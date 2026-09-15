import logging
from functools import partial
from typing import TYPE_CHECKING, Literal, cast

from sounds import endpoints
from sounds.endpoints import URLs
from sounds.exceptions import APIResponseError, InvalidFormatError, NotFoundError
from sounds.models import (
    Category,
    Collection,
    Container,
    Menu,
    PlayableItem,
    Podcast,
    PodcastEpisode,
    RadioClip,
    RadioSeries,
    RadioShow,
    SearchResults,
    Segment,
)
from sounds.parser import Parser
from sounds.playback import PlaybackService
from sounds.requests import RequestManager
from sounds.user import UserService
from sounds.utils import image_from_spotify

if TYPE_CHECKING:
    from sounds.models import SoundsTypes

logger = logging.getLogger(__name__)


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

    async def get_podcasts(self) -> Menu:
        podcasts = self.parser.parse_menu(
            await self.requests.get_json_response(url=endpoints.URLs.PODCASTS)
        )
        return podcasts

    async def get_podcast(
        self, urn=None, pid=None, include_episodes=True
    ) -> Podcast | RadioSeries:
        podcast = None
        if not urn and not pid:
            raise InvalidFormatError("Must be called with one of: urn, pid")
        if urn:
            # If we have the URN we can look up the podcast container
            podcast_container = await self.get_container(urn=urn)
            if podcast_container and type(podcast_container) is list:
                podcast = next(
                    (
                        podcast
                        for podcast in podcast_container
                        if isinstance(podcast, (Podcast, RadioSeries))
                    ),
                    None,
                )
            else:
                podcast = (
                    podcast_container
                    if isinstance(podcast_container, (Podcast, RadioSeries))
                    else None
                )
            if podcast and not include_episodes and getattr(podcast, "sub_items", None):
                podcast.sub_items = []
        elif pid:
            # If we only have the PID, we can grab the episodes and parse out the podcast or radio series
            podcast_episodes = await self.get_pid_container(pid=pid)
            length = len(podcast_episodes) if podcast_episodes else 0
            logger.debug("Received %s episodes for podcast", length)
            if (
                podcast_episodes
                and len(podcast_episodes) > 1
                and podcast_episodes[0].container
            ):
                inferred_type = type(podcast_episodes[0].container)
                logger.debug(f"Inferred type of podcast is {inferred_type}")
                if inferred_type is Podcast:
                    return await self.get_podcast(urn=podcast_episodes[0].container.urn)
                elif inferred_type is RadioSeries:
                    return await self.get_radio_series(
                        urn=podcast_episodes[0].container.urn
                    )
                raise NotFoundError(
                    "Incorrect type found for podcast - urn: {urn}, pid: {pid}"
                )

        if not podcast or not isinstance(podcast, (Podcast, RadioSeries)):
            raise NotFoundError(f"Couldn't get podcast - urn: {urn}, pid: {pid}")
        return podcast

    async def get_podcast_episodes(
        self, pid
    ) -> list[PodcastEpisode | RadioShow | RadioClip] | None:
        podcast_container = await self.get_pid_container(pid)
        if podcast_container and type(podcast_container) is list:
            return [
                episode
                for episode in podcast_container
                if isinstance(episode, (PodcastEpisode, RadioShow, RadioClip))
            ]
        return []

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
        logger.debug(f"Getting playable item with PID {pid}")

        if (
            await self.user.is_uk_account_and_location()
            and self.user.login_details_provided
        ):
            json_resp = await self.requests.run(
                partial(
                    self.requests.get_json_response,
                    url=URLs.PID_PLAYABLE,
                    url_args={"pid": pid},
                )
            )
        else:
            json_resp = await self.requests.get_json_response(
                url=URLs.PROGRAMME_FROM_PID_PLAYABLE, url_args={"pid": pid}
            )

        logger.debug(json_resp)
        if not json_resp or "id" not in json_resp:
            logger.debug(json_resp)
            raise APIResponseError(f"Couldn't get playable item with PID {pid}")
        playable_item = self.parser.parse_node(json_resp)
        if not isinstance(playable_item, PlayableItem):
            raise APIResponseError(f"Couldn't get playable item with PID {pid}")

        if include_stream:
            playable_item.stream = await self.playback.get_episode_stream(
                episode_id=playable_item.id, stream_format=stream_format
            )
        return playable_item

    async def get_pid_container(self, pid) -> list[PlayableItem] | None:
        json_resp = await self.requests.get_json_response(
            url=URLs.PLAYABLE_ITEMS_CONTAINER, url_args={"pid": pid}
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
            url=URLs.CONTAINER_URL, url_args={"urn": urn}
        )
        container = self.parser.parse_container(json_resp)
        if type(container) is list and len(container) == 1:
            return container[0]
        if not container:
            return []
        return container

    async def get_category(self, category) -> Category:
        json_resp = await self.requests.get_json_response(
            url=URLs.CATEGORY_LATEST, url_args={"category": category}
        )
        return cast("Category", self.parser.parse_node(json_resp))

    async def get_collection(self, pid) -> Collection:
        json_resp = await self.requests.get_json_response(
            url=URLs.COLLECTIONS, url_args={"pid": pid}
        )
        return cast("Collection", self.parser.parse_node(json_resp))

    async def get_playlist_contents(self, pid) -> list[SoundsTypes]:
        """Gets a curation/playlist."""
        json_resp = await self.requests.get_json_response(
            url=URLs.CURATIONS, url_args={"pid": pid}
        )
        if not json_resp:
            return []
        if not json_resp:
            return []
        container = self.parser.parse_container(json_resp)
        if isinstance(container, list):
            return container
        return [container] if container else []

    async def search(self, query) -> SearchResults:
        json_resp = await self.requests.get_json_response(
            url=URLs.SEARCH_URL, url_args={"search": query}
        )
        return self.parser.parse_search(json_resp)

    async def get_show_segments(
        self, vpid, fetch_missing_images: bool = False
    ) -> list[Segment]:
        json_resp = await self.requests.get_json_response(
            url=URLs.SEGMENTS, url_args={"vpid": vpid}
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
                    segment.image_url = await image_from_spotify(segment.spotify_url)
            return segments
        return []
