import copy
import json
from pathlib import Path

import pytest

from auntie_sounds.endpoints import Endpoints
from auntie_sounds.exceptions import APIResponseError
from auntie_sounds.models import Podcast, PodcastEpisode, RadioSeries, RadioShow
from auntie_sounds.owners import OwnerAwareParser, OwnerService

pytestmark = pytest.mark.anyio

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "api"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _container_items(owners: dict[str, str]) -> dict:
    """A CONTAINER_FROM_PIDS response for these pids and owning networks."""
    template = _load("CONTAINER_FROM_PIDS.json")
    items = []
    for pid, network_id in owners.items():
        item = copy.deepcopy(template["data"][0])
        item["id"] = pid
        item["urn"] = f"urn:bbc:radio:brand:{pid}"
        item["network"] = {**item["network"], "id": network_id}
        items.append(item)
    return {**template, "total": len(items), "data": items}


class FakeRequests:
    """Answers CONTAINER_FROM_PIDS from a fixed pid -> network map."""

    def __init__(
        self, owners: dict[str, str], fail: bool = False, stations_fail: bool = False
    ):
        self.owners = owners
        self.fail = fail
        self.stations_fail = stations_fail
        self.calls: list[list[str]] = []
        self.station_calls = 0

    async def get_json_response(self, url, url_args=None, **kwargs):
        if url == Endpoints.NETWORKS:
            self.station_calls += 1
            if self.stations_fail:
                raise APIResponseError("down")
            return _load("NETWORKS.json")
        assert url == Endpoints.CONTAINER_FROM_PIDS
        pids = url_args["pids"].split(",")
        self.calls.append(pids)
        if self.fail:
            raise APIResponseError("down")
        return _container_items({p: self.owners[p] for p in pids if p in self.owners})


def _episode(pid: str, brand: str, network_id: str) -> dict:
    episode = copy.deepcopy(_load("PROGRAMME_FROM_PID_PLAYABLE.json"))
    episode["urn"] = f"urn:bbc:radio:episode:{pid}"
    episode["network"] = {**episode["network"], "id": network_id}
    episode["container"] = {
        **episode["container"],
        "id": brand,
        "urn": f"urn:bbc:radio:brand:{brand}",
    }
    return episode


class TestOwnerService:
    async def test_marks_the_container_by_its_owner(self):
        requests = FakeRequests({"p08yblkf": "bbc_sounds_podcasts"})
        listing = _load("PLAYABLE_ITEMS_CONTAINER.json")

        await OwnerService(requests).annotate(listing)

        assert requests.calls == [["p08yblkf"]]
        # Every container is marked as not station-owned, even under the
        # episodes that went out on Radio 4
        assert {item["container"]["station_owned"] for item in listing["data"]} == {
            False
        }
        # Only the mark is added
        assert all("network" not in item["container"] for item in listing["data"])
        assert {item["network"]["id"] for item in listing["data"]} == {
            "bbc_sounds_podcasts",
            "bbc_radio_four",
        }

    async def test_one_request_for_a_mixed_listing(self):
        requests = FakeRequests({"b1": "bbc_sounds_podcasts", "b2": "bbc_radio_four"})
        listing = {
            "data": [
                _episode("e1", "b1", "bbc_radio_four"),
                _episode("e2", "b2", "bbc_radio_four"),
                _episode("e3", "b1", "bbc_sounds_podcasts"),
            ]
        }

        await OwnerService(requests).annotate(listing)

        assert requests.calls == [["b1", "b2"]]

    async def test_each_owner_is_looked_up_once(self):
        requests = FakeRequests({"b1": "bbc_sounds_podcasts"})
        owners = OwnerService(requests)

        await owners.annotate(_episode("e1", "b1", "bbc_radio_four"))
        await owners.annotate(_episode("e2", "b1", "bbc_radio_four"))

        assert requests.calls == [["b1"]]

    async def test_unknown_pids_are_not_looked_up_again(self):
        requests = FakeRequests({})
        owners = OwnerService(requests)

        await owners.annotate(_episode("e1", "gone", "bbc_radio_four"))
        await owners.annotate(_episode("e2", "gone", "bbc_radio_four"))

        assert requests.calls == [["gone"]]

    async def test_listed_containers_are_remembered(self):
        """A podcast's own page already says who owns it."""
        requests = FakeRequests({})
        owners = OwnerService(requests)

        await owners.annotate(_load("CONTAINER_FROM_PIDS.json"))
        episode = _episode("e1", "p08yblkf", "bbc_radio_four")
        await owners.annotate(episode)

        assert requests.calls == []
        assert episode["container"]["station_owned"] is False

    async def test_lookups_are_batched_by_page(self):
        brands = {f"b{n:02}": "bbc_radio_four" for n in range(45)}
        requests = FakeRequests(brands)

        await OwnerService(requests).lookup(brands)

        assert [len(batch) for batch in requests.calls] == [30, 15]

    async def test_failed_lookup_falls_back_and_is_retried_later(self):
        requests = FakeRequests({"b1": "bbc_sounds_podcasts"}, fail=True)
        owners = OwnerService(requests)

        # The episode went out on Radio 4, so until the owner is known it's
        # treated as station-owned
        episode = _episode("e1", "b1", "bbc_radio_four")
        await owners.annotate(episode)
        assert episode["container"]["station_owned"] is True

        requests.fail = False
        episode = _episode("e1", "b1", "bbc_radio_four")
        await owners.annotate(episode)
        assert episode["container"]["station_owned"] is False

    async def test_unknown_owner_falls_back_to_the_episode_network(self):
        """bbc_local_radio isn't a station, so this isn't station-owned."""
        requests = FakeRequests({})
        episode = _episode("e1", "gone", "bbc_local_radio")

        await OwnerService(requests).annotate(episode)

        assert episode["container"]["station_owned"] is False


class TestOwnerAwareParser:
    @pytest.mark.parametrize(
        ("owner", "episode_type", "container_type"),
        [
            ("bbc_sounds_podcasts", PodcastEpisode, Podcast),
            ("bbc_radio_four", RadioShow, RadioSeries),
        ],
    )
    async def test_mixed_brands_are_each_typed_by_their_owner(
        self, owner, episode_type, container_type
    ):
        """Both episodes went out on Radio 4. Only the owner differs."""
        requests = FakeRequests({"b1": owner, "b2": "bbc_sounds_podcasts"})
        listing = {
            "data": [
                _episode("e1", "b1", "bbc_radio_four"),
                _episode("e2", "b2", "bbc_radio_four"),
            ]
        }

        first, second = await OwnerAwareParser(OwnerService(requests)).parse_container(
            listing
        )

        assert type(first) is episode_type
        assert type(first.container) is container_type
        assert type(second) is PodcastEpisode
        assert type(second.container) is Podcast


class TestStationOwnership:
    @pytest.mark.parametrize(
        ("owner", "station_owned"),
        [
            ("bbc_radio_four", True),
            ("bbc_world_service", True),
            # Online-only streams have a live service, so they count
            ("bbc_radio_six_indie_forever", True),
            ("bbc_sounds_podcasts", False),
            ("bbc_news", False),
            # Not stations themselves, though the fixed set treated them as radio
            ("bbc_local_radio", False),
            ("bbc_webonly", False),
        ],
    )
    async def test_marks_whether_the_owner_is_a_station(self, owner, station_owned):
        episode = _episode("e1", "b1", "bbc_radio_four")

        await OwnerService(FakeRequests({"b1": owner})).annotate(episode)

        assert episode["container"]["station_owned"] is station_owned

    async def test_station_list_is_fetched_once(self):
        requests = FakeRequests({"b1": "bbc_radio_four", "b2": "bbc_local_radio"})
        owners = OwnerService(requests)

        await owners.annotate(_episode("e1", "b1", "bbc_radio_four"))
        await owners.annotate(_episode("e2", "b2", "bbc_radio_four"))

        assert requests.station_calls == 1

    async def test_no_request_without_programmes(self):
        requests = FakeRequests({})

        await OwnerService(requests).annotate({"data": [{"type": "segment_item"}]})

        assert requests.station_calls == 0
        assert requests.calls == []

    async def test_without_the_station_list_entries_are_unmarked(self):
        requests = FakeRequests({"b1": "bbc_local_radio"}, stations_fail=True)
        episode = _episode("e1", "b1", "bbc_radio_four")

        await OwnerService(requests).annotate(episode)

        assert "station_owned" not in episode["container"]

    async def test_local_radio_podcast_is_a_podcast(self):
        """Undercover is owned by bbc_local_radio, which has no live service."""
        requests = FakeRequests({"b1": "bbc_local_radio"})

        item = await OwnerAwareParser(OwnerService(requests)).parse_node(
            _episode("e1", "b1", "bbc_local_radio")
        )

        assert type(item) is PodcastEpisode
        assert type(item.container) is Podcast
