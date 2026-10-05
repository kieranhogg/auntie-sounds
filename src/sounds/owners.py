"""Work out whether a station owns each brand, so episodes are typed consistently.

A brand or top-level series owned by a radio station is a RadioSeries and its
episodes are RadioShows. Anything else is treated as a Podcast of PodcastEpisodes.
A station is a network with a live service of its own.

Depending on endpoints, requesting a particular episode does not contain enough data to
be able to determine what type of episode it is. Rather than adding an extra request
each time, OwnerService keeps track of that pid->series/brand->network conversion.

Notes:
    * this depends on who owns the brand, not on the network an episode went out
on. E.g. some BBC Podcast-owned episodes are broadcast on radio, but are presented as a
podcast within Sounds itself.
    * there are some programmes that have both a radio version and a podcast version
"""

import asyncio
import logging
import time
from collections.abc import Iterable, Iterator
from itertools import batched
from typing import Any

from sounds.endpoints import Endpoints
from sounds.exceptions import SoundsException
from sounds.model_factory import STATION_OWNED
from sounds.models import Menu, SearchResults, Season, SoundsTypes
from sounds.parser import Parser
from sounds.requests import RequestManager

logger = logging.getLogger(__name__)

# Brand and series entries, either listed in their own right or found under an
# episode's container or ancestors
_PROGRAMME_TYPES = frozenset({"brand", "series"})

# The API's own page size, so each batch lookup is a single page
_BATCH_SIZE = 30

# How long to wait before asking again about a pid the API didn't return
_RETRY_MISSES_AFTER = 60 * 60


def _walk(node: Any, parent: dict | None = None) -> Iterator[tuple[dict, dict | None]]:
    """Every dict in a JSON response, depth first, with the dict it sits in."""
    if isinstance(node, dict):
        yield node, parent
        for value in node.values():
            yield from _walk(value, node)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value, parent)


def _pid(entry: dict) -> str | None:
    if urn := entry.get("urn"):
        return urn.rsplit(":", 1)[-1]
    return entry.get("id")


def _network_id(entry: dict) -> str | None:
    network = entry.get("network")
    return network.get("id") if isinstance(network, dict) else None


def _is_programme(entry: dict) -> bool:
    """A brand or series, either listed in its own right with a urn such as
    urn:bbc:radio:brand:p08yblkf, or as an episode's container or ancestor."""
    parts = (entry.get("urn") or "").split(":")
    return entry.get("type") in _PROGRAMME_TYPES or (
        len(parts) == 5 and parts[3] in _PROGRAMME_TYPES
    )


class OwnerService:
    """Works out whether a radio station owns each brand or series."""

    def __init__(self, requests: RequestManager):
        self.requests = requests
        # pid -> id of the owning network. Ownership never changes, so this lasts
        # the client's lifetime. Given the small size of entries, this shouldn't need
        # truncating.
        self._owners: dict[str, str | None] = {}
        # pid -> time.monotonic() of the last lookup that didn't find it
        self._misses: dict[str, float] = {}
        # Ids of networks with a live service. None until fetched.
        self._stations: frozenset[str] | None = None

    async def lookup(self, pids: Iterable[str]) -> None:
        """Fetch the owners of any of these pids not already known."""
        now = time.monotonic()
        missing = sorted(
            {
                pid
                for pid in pids
                if pid not in self._owners
                and now - self._misses.get(pid, -_RETRY_MISSES_AFTER)
                >= _RETRY_MISSES_AFTER
            }
        )
        if missing:
            await asyncio.gather(
                *(self._fetch(list(batch)) for batch in batched(missing, _BATCH_SIZE))
            )

    async def annotate(self, json_data: Any) -> None:
        """Mark each brand and series entry with whether a station owns it."""
        programmes = [
            (entry, parent)
            for entry, parent in _walk(json_data)
            if _is_programme(entry)
        ]
        if not programmes:
            return

        # Containers listed in their own right, e.g. a podcast's page or search
        # results, already say who owns them
        for entry, _ in programmes:
            if (pid := _pid(entry)) and (network_id := _network_id(entry)):
                self._owners[pid] = network_id
                self._misses.pop(pid, None)

        _, stations = await asyncio.gather(
            self.lookup(pid for entry, _ in programmes if (pid := _pid(entry))),
            self._station_networks(),
        )
        # Without the station list, entries are left unmarked and the parser
        # falls back to its fixed set of podcast networks
        if stations is None:
            return

        for entry, parent in programmes:
            owner = self._owners.get(_pid(entry) or "")
            # If the owner couldn't be found, the network the episode went out
            # on is the best guess
            if owner is None and parent is not None:
                owner = _network_id(parent)
            if owner is not None:
                entry[STATION_OWNED] = owner in stations

    async def _station_networks(self) -> frozenset[str] | None:
        """The networks that are radio stations, fetched once per client."""
        if self._stations is None:
            try:
                json_resp = await self.requests.get_json_response(
                    url=Endpoints.NETWORKS, fetch_all_items=True
                )
            except SoundsException as e:
                logger.warning("Couldn't get the station list: %s", e)
                return None
            self._stations = frozenset(
                network["id"]
                for network in json_resp.get("data") or []
                if network.get("services")
            )
        return self._stations

    async def _fetch(self, pids: list[str]) -> None:
        try:
            json_resp = await self.requests.get_json_response(
                url=Endpoints.CONTAINER_FROM_PIDS, url_args={"pids": ",".join(pids)}
            )
        except SoundsException as e:
            # Leave these unknown so a later call can try again. Until then
            # annotate marks entries from each episode's own network instead.
            logger.warning("Couldn't look up the owners of %s: %s", pids, e)
            return
        found = {
            pid: _network_id(item)
            for item in json_resp.get("data") or []
            if (pid := _pid(item))
        }
        now = time.monotonic()
        for pid in pids:
            if network_id := found.get(pid):
                self._owners[pid] = network_id
                self._misses.pop(pid, None)
            else:
                self._misses[pid] = now


class OwnerAwareParser:
    """The Parser, with station ownership marked first.

    ContentService and PersonalService parse through this, so every episode
    they return is typed by its brand's owner, whichever endpoint it came
    from. Its methods are async, so a parse that skips the lookup can't be
    written by accident.
    """

    def __init__(self, owners: OwnerService):
        self.owners = owners
        self._parser = Parser()

    async def parse_node(
        self,
        node: dict | list,
        parent_network: dict | None = None,
        type_hint: type[SoundsTypes] | None = None,
    ) -> SoundsTypes | list[SoundsTypes] | None:
        await self.owners.annotate(node)
        return self._parser.parse_node(
            node, parent_network=parent_network, type_hint=type_hint
        )

    async def parse_container(
        self, json_data: dict, type_hint: type[SoundsTypes] | None = None
    ) -> SoundsTypes | list[SoundsTypes] | None:
        await self.owners.annotate(json_data)
        return self._parser.parse_container(json_data, type_hint=type_hint)

    async def parse_menu(self, json_data: dict) -> Menu:
        await self.owners.annotate(json_data)
        return self._parser.parse_menu(json_data)

    async def parse_schedule(self, json_data: dict) -> Any:
        await self.owners.annotate(json_data)
        return self._parser.parse_schedule(json_data)

    async def parse_search(self, json_data: dict) -> SearchResults:
        await self.owners.annotate(json_data)
        return self._parser.parse_search(json_data)

    async def parse_seasons(self, json_data: dict) -> list[Season]:
        await self.owners.annotate(json_data)
        return self._parser.parse_seasons(json_data)
