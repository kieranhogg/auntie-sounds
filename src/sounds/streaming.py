from typing import TYPE_CHECKING, List, Literal, Optional, cast

from . import constants
from .auth import AuthService
from .base import Base
from .constants import PlayStatus, SignedInURLs, URLs
from .exceptions import APIResponseError, InvalidFormatError, NotFoundError
from .models import (
    Category,
    Collection,
    PlayableItem,
    Podcast,
    PodcastEpisode,
    RadioClip,
    RadioSeries,
    RadioShow,
    SearchResults,
    Segment,
)
from .parser import parse_container, parse_menu, parse_node, parse_search
from .schedules import ScheduleService

if TYPE_CHECKING:
    from .models import SoundsTypes


class StreamingService(Base):
    def __init__(
        self,
        auth_service: AuthService,
        schedule_service: ScheduleService,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.auth_service = auth_service
        self.schedule_service = schedule_service

    async def get_postcasts(self):
        podcasts = parse_menu(
            await self._get_json(url_template=constants.URLs.PODCASTS)
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
            podcast_container = await self.get_container(urn)
            if podcast_container and type(podcast_container) is list:
                podcast = next(
                    (
                        podcast
                        for podcast in podcast_container
                        if type(podcast) is Podcast
                    ),
                    None,
                )
            else:
                podcast = podcast_container

            if podcast:
                podcast = cast(Podcast, podcast)
                if not include_episodes and getattr(podcast, "sub_items", None):
                    podcast.sub_items = []
        elif pid:
            # If we only have the PID, we can grab the episodes and parse out the podcast or radio series
            podcast_episodes = await self.get_pid_container(pid)
            if podcast_episodes and len(podcast_episodes) > 1:
                if podcast_episodes[0].container:
                    if type(podcast_episodes[0].container) is Podcast:
                        return await self.get_podcast(
                            urn=podcast_episodes[0].container.urn
                        )
                    elif type(podcast_episodes[0].container) is RadioSeries:
                        return await self.get_radio_series(
                            urn=podcast_episodes[0].container.urn
                        )

        if not podcast or not isinstance(podcast, Podcast):
            raise NotFoundError(f"Couldn't get podcast - urn: {urn}, pid: {pid}")
        return podcast

    async def get_podcast_episodes(
        self, pid
    ) -> Optional[List[PodcastEpisode | RadioShow | RadioClip]]:
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
            raise APIResponseError(f"Item requested not a radio show! {str(show)}")
        return show

    async def get_live_stream(
        self, station_id: str, stream_format: Literal["hls"] | Literal["dash"] = "hls"
    ) -> Optional[str]:
        jwt_token = await self.get_jwt_token(station_id)

        json_resp = await self._get_json(
            url_template=URLs.MEDIASET,
            url_args={"station_id": station_id, "jwt_auth_token": jwt_token},
        )
        stream = None
        try:
            streams = json_resp["media"][0]["connection"]
            self.logger.debug("Found streams:")
            self.logger.debug(str(streams))
            stream = self.get_best_stream(streams, prefer_type=stream_format)
            self.logger.debug(f"Found stream: {stream}")
        except (StopIteration, KeyError):
            raise RuntimeError("No valid stream found")
        if not stream:
            return None

        return stream

    def get_best_stream(
        self, streams: dict, prefer_type: Literal["hls"] | Literal["dash"] = "hls"
    ) -> Optional[str]:
        """Looks for the first valid stream with the requested format."""
        self.logger.log(constants.VERBOSE_LOG_LEVEL, "Looking for best stream in:")
        self.logger.log(constants.VERBOSE_LOG_LEVEL, streams)

        return next(
            (
                conn["href"]
                for conn in streams
                if conn.get("transferFormat", "") == prefer_type
            ),
            None,
        )

    async def get_episode_stream(
        self,
        episode_id: str,
        stream_format: Literal["hls"] | Literal["dash"] = "hls",
    ) -> str | None:
        """
        Gets the stream for a specified episode.

        :param episode_id: str
        :returns: Stream object of stream information
        :rtype: str | None
        """
        json_resp = await self._get_json(
            url_template=URLs.EPISODE_MEDIASET, url_args={"episode_id": episode_id}
        )

        stream = None
        try:
            streams = json_resp["media"][0]["connection"]
            self.logger.debug("Found streams:")
            self.logger.debug(str(streams))
            stream = self.get_best_stream(streams, prefer_type=stream_format)
            self.logger.debug(f"Found stream: {stream}")
        except (StopIteration, KeyError):
            raise RuntimeError("No valid stream found")
        return stream

    async def get_by_pid(
        self,
        pid,
        include_stream=False,
        stream_format: Literal["hls"] | Literal["dash"] = "hls",
    ) -> "SoundsTypes":
        self.logger.debug(f"Getting playable item with PID {pid}")
        if self.auth_service.is_logged_in:
            json_resp = await self._get_json(
                url_template=SignedInURLs.PID_PLAYABLE, url_args={"pid": pid}
            )
        else:
            json_resp = await self._get_json(
                url_template=URLs.PID_PLAYABLE, url_args={"pid": pid}
            )

        self.logger.debug(json_resp)
        if not json_resp or "id" not in json_resp:
            self.logger.debug(json_resp)
            raise APIResponseError(f"Couldn't get playable item with PID {pid}")
        playable_item = parse_node(json_resp)
        if not isinstance(playable_item, PlayableItem):
            raise APIResponseError(f"Couldn't get playable item with PID {pid}")

        if include_stream:
            playable_item.stream = await self.get_episode_stream(
                episode_id=playable_item.id, stream_format=stream_format
            )
        return playable_item

    async def get_pid_container(self, pid) -> List[PlayableItem] | None:
        json_resp = await self._get_json(
            url_template=URLs.PLAYABLE_ITEMS_CONTAINER, url_args={"pid": pid}
        )
        container = parse_container(json_resp)
        if isinstance(container, list):
            playable_container: List[PlayableItem] = [
                item for item in container if isinstance(item, PlayableItem)
            ]
            return playable_container
        return None

    async def get_container(self, urn):
        json_resp = await self._get_json(
            url_template=URLs.CONTAINER_URL, url_args={"urn": urn}
        )
        container = parse_container(json_resp)
        if type(container) is list and len(container) == 1:
            container = container[0]
        return container

    async def get_heartbeat_details(self, pid):
        json_resp = await self._get_json(
            url_template=URLs.PLAYLIST, url_args={"pid": pid}
        )
        self.logger.debug(f"Heartbeat details response: {json_resp}")
        try:
            vpid = json_resp["defaultAvailableVersion"]["smpConfig"]["items"][0]["vpid"]
            item_type = json_resp["statsObject"]["parentPIDType"]
        except (APIResponseError, KeyError, TypeError):
            raise APIResponseError(f"Couldn't get heartbeat details for PID {pid}")
        return vpid, item_type

    async def update_play_status(
        self,
        pid: str,
        elapsed_time: int,
        action: PlayStatus,
    ):
        vpid, resource_type = await self.get_heartbeat_details(pid)
        data = {
            "action": action,
            "elapsed_time": elapsed_time,
            "pid": pid,
            "play_mode": "ondemand",
            "resource_type": resource_type,
            "version_pid": vpid,
        }
        resp = await self._make_request(
            method="POST", url=SignedInURLs.PLAYS.value, json=data
        )
        if resp.status != 202:
            raise APIResponseError(resp)
        return True

    async def get_category(self, category) -> Category:
        json_resp = await self._get_json(
            url_template=URLs.CATEGORY_LATEST, url_args={"category": category}
        )
        return cast("Category", parse_node(json_resp))

    async def get_collection(self, pid) -> Collection:
        json_resp = await self._get_json(
            url_template=URLs.COLLECTIONS, url_args={"pid": pid}
        )
        return cast("Collection", parse_node(json_resp))

    async def search(self, query) -> SearchResults:
        json_resp = await self._get_json(
            url_template=URLs.SEARCH_URL, url_args={"search": query}
        )
        return parse_search(json_resp)

    async def get_show_segments(self, vpid) -> List[Segment]:
        json_resp = await self._get_json(
            url_template=URLs.SEGMENTS, url_args={"vpid": vpid}
        )
        return cast("List[Segment]", parse_container(json_resp))
