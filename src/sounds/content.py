import asyncio
import logging
from collections import defaultdict
from collections.abc import Sequence
from itertools import chain
from typing import TYPE_CHECKING, Literal, cast

from sounds import endpoints
from sounds.endpoints import Endpoints
from sounds.exceptions import APIResponseError, InvalidFormatError, NotFoundError
from sounds.models import (
    Audiobook,
    Collection,
    Container,
    EpisodeTypes,
    ItemCategory,
    Menu,
    PlayableItem,
    Podcast,
    PodcastEpisode,
    RadioSeries,
    RadioShow,
    SearchResults,
    Season,
    Segment,
)
from sounds.parser import Parser
from sounds.playback import PlaybackService
from sounds.requests import RequestManager
from sounds.user import UserService

if TYPE_CHECKING:
    from sounds.models import SoundsTypes

logger = logging.getLogger(__name__)


def assign_seasons(
    podcast: Podcast | RadioSeries, episodes: Sequence[EpisodeTypes]
) -> None:
    if not podcast.seasons:
        return
    by_series: defaultdict[str | None, list[EpisodeTypes]] = defaultdict(list)
    for episode in episodes:
        by_series[episode.series_pid].append(episode)

    def first_release(season: Season) -> str:
        return min(
            (e.release["date"] for e in by_series.get(season.item_id, ()) if e.release),
            default="9999",
        )

    podcast.seasons.sort(key=first_release)
    for season in podcast.seasons:
        # Container.pid isn't populated from the urn, so use item_id
        season.sub_items = (
            by_series.pop(season.item_id, None) if season.item_id else None
        )

    # anything left matched no season (including series_pid=None)
    podcast.sub_items = list(chain.from_iterable(by_series.values())) or None


class ContentService:
    """Resolving IDs (pids/urns) and browsing the catalog: podcasts, radio
    series, categories, collections, playlists, and search.

    This is deliberately the "what is this thing, and what's in it" service.
    Actually playing something lives in PlaybackService; get_by_pid() reaches
    into it only when a caller explicitly asks for the stream to be attached.
    """

    def __init__(
        self, user: UserService, requests: RequestManager, playback: PlaybackService
    ):
        self.user: UserService = user
        self.requests: RequestManager = requests
        self.playback: PlaybackService = playback
        self.parser = Parser()

    async def image_from_spotify(self, url: str) -> str | None:
        spotify_url = "https://open.spotify.com/oembed?url={url}"
        resp = await self.requests.make_request(
            method="GET", url=spotify_url.format(url=url)
        )
        json_resp = await resp.json()
        if json_resp.get("thumbnail_url"):
            return json_resp.get("thumbnail_url")
        return None

    async def get_podcasts(self) -> Menu:
        podcasts = self.parser.parse_menu(
            await self.requests.get_json_response(url=endpoints.Endpoints.PODCASTS)
        )
        return podcasts

    async def get_podcast(
        self, urn=None, pid=None, include_episodes=False
    ) -> Podcast | RadioSeries:
        if not urn and not pid:
            raise InvalidFormatError("Must be called with one of: urn, pid")
        if urn:
            pid = urn.rsplit(":", 1)[-1]

        # We get the seasons, if there are any, as well as the overall container
        series_json, brand_json = await asyncio.gather(
            self.requests.get_json_response(
                url=Endpoints.SERIES_CONTAINER,
                params={"parent": pid, "type": "series"},
            ),
            self.requests.get_json_response(
                url=Endpoints.CONTAINER_FROM_PIDS, url_args={"pids": pid}
            ),
        )
        brand = self.parser.parse_container(brand_json)
        podcast = brand[0] if isinstance(brand, list) and brand else None
        if not isinstance(podcast, (Podcast, RadioSeries)):
            raise NotFoundError(f"Couldn't get podcast - pid: {pid}")
        podcast.seasons = self.parser.parse_seasons(series_json) or None
        if include_episodes:
            episodes = await self.get_podcast_episodes(pid, fetch_all_items=True)
            if not podcast.seasons:
                podcast.sub_items = episodes
            else:
                assign_seasons(podcast, episodes)
        return podcast

    async def get_podcast_episodes(
        self,
        pid,
        fetch_all_items: bool = False,
        max_items: int | None = None,
    ) -> list[EpisodeTypes]:
        items = await self.get_pid_container(
            pid=pid, fetch_all_items=fetch_all_items, max_items=max_items
        )
        return [i for i in items or [] if isinstance(i, EpisodeTypes)]

    async def get_podcast_episode(self, pid, include_stream=False) -> PodcastEpisode:
        show = await self.get_by_pid(pid=pid, include_stream=include_stream)
        show = cast(PodcastEpisode, show)
        return show

    async def get_radio_series(self, urn, include_episodes=True) -> RadioSeries:
        series_container = await self.get_container(urn)

        if series_container:
            series = cast(RadioSeries, series_container)
            if not include_episodes and getattr(series, "sub_items", None):
                series.sub_items = []
        else:
            raise NotFoundError(f"No radio series with urn {urn}")
        return series

    async def get_radio_show(self, pid, include_stream=False) -> RadioShow:
        show = await self.get_by_pid(pid=pid, include_stream=include_stream)
        if not isinstance(show, RadioShow):
            raise APIResponseError(f"Item requested not a radio show! {show!s}")
        return show

    async def get_by_pid(
        self,
        pid,
        include_stream=False,
        stream_format: Literal["hls", "dash"] = "hls",
    ) -> SoundsTypes:
        logger.debug("Getting item with PID %s", pid)

        json_resp = await self.requests.get_json_response(
            url=Endpoints.PROGRAMME_FROM_PID, url_args={"pid": pid}
        )

        logger.debug(json_resp)

        if not json_resp or not json_resp.get("data"):
            raise NotFoundError(f"Couldn't get item with PID {pid}")
        playable_item = self.parser.parse_node(json_resp)

        if not isinstance(playable_item, PlayableItem):
            raise APIResponseError(f"Couldn't get item with PID {pid}")

        if include_stream:
            playable_item.stream = await self.playback.get_episode_stream(
                episode_id=playable_item.id, stream_format=stream_format
            )
        return playable_item

    async def get_pid_container(
        self,
        pid,
        sort: str = "sequential",
        fetch_all_items: bool = False,
        max_items: int | None = None,
    ) -> list[PlayableItem] | None:
        json_resp = await self.requests.get_json_response(
            url=Endpoints.PLAYABLE_ITEMS_CONTAINER,
            params={"container": pid, "sort": sort},
            fetch_all_items=fetch_all_items,
            max_items=max_items,
        )
        container = self.parser.parse_container(json_resp)
        if isinstance(container, list):
            playable_container: list[PlayableItem] = [
                item for item in container if isinstance(item, PlayableItem)
            ]
            return playable_container
        return None

    async def get_container(
        self, urn
    ) -> list[SoundsTypes] | SoundsTypes | Container | None:
        json_resp = await self.requests.get_json_response(
            url=Endpoints.URN_CONTAINER, url_args={"urn": urn}
        )
        container = self.parser.parse_container(json_resp)
        if isinstance(container, list) and len(container) == 1:
            return container[0]
        if not container:
            return []
        return container

    async def get_category(self, category) -> ItemCategory:
        json_resp = await self.requests.get_json_response(
            url=Endpoints.PLAYABLE_ITEMS_CONTAINER,
            params={"category": category, "sort": "-release_date"},
        )
        return cast("ItemCategory", self.parser.parse_node(json_resp))

    async def get_collection(self, pid) -> Collection:
        json_resp = await self.requests.get_json_response(
            url=Endpoints.COLLECTIONS, url_args={"pid": pid}
        )
        return cast("Collection", self.parser.parse_node(json_resp))

    async def get_audiobooks(self):
        json_resp = await self.requests.get_json_response(url=Endpoints.AUDIOBOOKS)
        return cast("Audiobook", self.parser.parse_node(json_resp))

    async def get_popular_audiobooks(self):
        json_resp = await self.requests.get_json_response(
            url=Endpoints.POPULAR_AUDIOBOOKS
        )
        container = self.parser.parse_container(json_resp)
        return container

    async def get_playlist_contents(self, pid) -> list[SoundsTypes]:
        """Gets a curation/playlist."""
        json_resp = await self.requests.get_json_response(
            url=Endpoints.CURATIONS, url_args={"pid": pid}
        )
        if not json_resp:
            return []
        container = self.parser.parse_container(json_resp)
        if isinstance(container, list):
            return container
        return [container] if container else []

    async def search(self, query) -> SearchResults:
        json_resp = await self.requests.get_json_response(
            url=Endpoints.SEARCH_URL, params={"q": query}
        )
        return self.parser.parse_search(json_resp)

    async def get_show_segments(
        self, vpid, fetch_missing_images: bool = False
    ) -> list[Segment]:
        json_resp = await self.requests.get_json_response(
            url=Endpoints.SEGMENTS, url_args={"vpid": vpid}
        )
        parsed_segments = self.parser.parse_container(json_resp)
        if isinstance(parsed_segments, list):
            segments = [item for item in parsed_segments if isinstance(item, Segment)]
            for segment in segments:
                if (
                    not segment.image_url
                    and fetch_missing_images
                    and segment.spotify_url
                ):
                    segment.image_url = await self.image_from_spotify(
                        segment.spotify_url
                    )
            return segments
        return []
