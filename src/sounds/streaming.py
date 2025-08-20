import json
import logging
import re
from datetime import datetime as dt
from typing import Literal, Optional

from .auth import AuthService


from . import constants
from .utils import network_logo
from .base import Base
from .constants import ContainerType, PlayStatus, SignedInURLs, URLs
from .exceptions import APIResponseError
from .json import parse_container, parse_node, parse_search
from .models import (
    Container,
    Network,
    PlayableItem,
    ScheduleItem,
    Station,
    Stream,
)
from .utils import image_from_recipe


class StreamingService(Base):

    def __init__(
        self,
        auth_service: AuthService,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.auth_service = auth_service

    async def get_live_stream(
        self,
        station_id: str,
        stream_format="hls",
        logo_size=800,
    ) -> Stream | None:
        """
        Gets the stream and details of the currently playing show on a given station.

        :param station: A Station object
        :type station_id: str
        :returns: Stream object of stream information
        :rtype: Stream | None
        """
        html_resp = await self._get_html(
            url_template=URLs.LIVE_STATION, url_args={"station_id": station_id}
        )
        match = re.search(
            r"window\.__PRELOADED_STATE__\s*=\s*(.*?);\s*</script>",
            html_resp,
            re.DOTALL,
        )
        if not match:
            raise APIResponseError("Could not find embedded player JSON")

        json_response = json.loads(match.group(1))
        self.logger.log(constants.VERBOSE_LOG_LEVEL, "Getting stream details...")
        self.logger.log(constants.VERBOSE_LOG_LEVEL, json_response)

        programme_details = json_response["programmes"]["current"]
        jwt_token = await self.get_jwt_token(station_id)

        json_resp = await self._get_json(
            url_template=URLs.MEDIASET,
            url_args={"station_id": station_id, "jwt_auth_token": jwt_token},
        )

        try:
            stream = self._get_best_stream(
                json_resp["media"][0]["connection"], prefer_type=stream_format
            )
            self.logger.debug(f"Found stream: {stream}")
        except (StopIteration, KeyError):
            raise RuntimeError("No valid stream found")
        if not stream:
            return None

        self.current_stream = Stream(
            id=programme_details["id"],
            start=dt.fromisoformat(programme_details["start"]),
            end=dt.fromisoformat(programme_details["end"]),
            uri=stream,
            image_url=image_from_recipe(programme_details["image_url"], size=logo_size),
            show_title=programme_details["titles"]["primary"],
            show_description=programme_details["titles"]["secondary"],
        )
        return self.current_stream

    def _get_best_stream(self, streams: dict, prefer_type="hls") -> Optional[str]:
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
        stream_format="hls",
        logo_size=800,
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

        # jwt_token = await self.get_jwt_token(station.id)
        stream = None
        try:
            stream = self._get_best_stream(
                json_resp["media"][0]["connection"], prefer_type=stream_format
            )
            self.logger.debug(f"Found stream: {stream}")
        except (StopIteration, KeyError):
            raise RuntimeError("No valid stream found")
        return stream

    async def get_by_pid(self, pid, include_stream=False):
        self.logger.debug(f"Getting playable item with PID {pid}")
        if self.auth_service.is_logged_in:
            url_template = SignedInURLs.PID_PLAYABLE
        else:
            url_template = URLs.PID_PLAYABLE
        json_resp = await self._get_json(
            url_template=url_template, url_args={"pid": pid}
        )
        self.logger.debug(json_resp)
        if not json_resp or "id" not in json_resp:
            self.logger.debug(json_resp)
            raise APIResponseError(f"Couldn't get playable item with PID {pid}")
        playable_item = parse_node(json_resp)
        if include_stream:
            playable_item.stream = await self.get_episode_stream(playable_item.id)
        return playable_item

    async def get_pid_container(self, pid):
        json_resp = await self._get_json(
            url_template=URLs.PID_CONTAINER, url_args={"pid": pid}
        )
        container = parse_container(json_resp)
        return container

    async def get_container(self, urn):
        json_resp = await self._get_json(
            url_template=URLs.CONTAINER_URL, url_args={"urn": urn}
        )
        container = parse_container(json_resp)
        return container
        try:
            container_data = json_resp["data"][0]["data"]
            episode_data = json_resp["data"][1]["data"]

            container = Container(
                type=ContainerType(container_data["type"]).value,
                id=container_data["id"],
                urn=container_data["urn"],
                title=container_data["titles"]["primary"],
                synopses=container_data["synopses"],
                network=(
                    Network(
                        id=container_data["network"]["id"],
                        key=container_data["network"]["key"],
                        short_title=container_data["network"]["short_title"],
                        logo_url=container_data["network"]["logo_url"],
                    )
                    if container_data.get("network") is not None
                    else None
                ),
            )
            episodes = [
                PlayableItem(
                    id=episode["id"],
                    urn=episode["urn"],
                    container=container,
                    network=(
                        Network(
                            id=episode["network"]["id"],
                            key=episode["network"]["key"],
                            short_title=episode["network"]["short_title"],
                            logo_url=episode["network"]["logo_url"],
                        )
                        if episode.get("network") is not None
                        else None
                    ),
                    duration=(
                        episode["duration"]["value"]
                        if episode.get("duration") is not None
                        else None
                    ),
                    progress=(
                        episode["progress"]["value"]
                        if episode.get("progress") is not None
                        else None
                    ),
                    synopses=(
                        episode["synopses"]
                        if episode.get("synopses") is not None
                        else {}
                    ),
                    image_url=episode["image_url"],
                    titles=(
                        episode["titles"] if episode.get("titles") is not None else {}
                    ),
                )
                for episode in episode_data
            ]
        except KeyError as e:
            self.logger.error(f"Error parsing container data: {e}")
            self.logger.error(json_resp)
            raise APIResponseError(f"Invalid container data received: {e}")
        return container, episodes

    async def get_heartbeat_details(self, pid):
        json_resp = await self._get_json(
            url_template=URLs.PLAYLIST, url_args={"pid": pid}
        )
        try:
            vpid = json_resp["defaultAvailableVersion"]["smpConfig"]["items"][0]["vpid"]
            item_type = json_resp["statsObject"]["parentPIDType"]
        except (APIResponseError, KeyError):
            vpid = None
            item_type = None
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

    async def get_category(self, category):
        json_resp = await self._get_json(
            url_template=URLs.CATEGORY_LATEST, url_args={"category": category}
        )
        return parse_node(json_resp)

    async def get_collection(self, pid):
        json_resp = await self._get_json(
            url_template=URLs.COLLECTIONS, url_args={"pid": pid}
        )
        return parse_node(json_resp)

    async def search(self, query):
        json_resp = await self._get_json(
            url_template=URLs.SEARCH_URL, url_args={"search": query}
        )
        return parse_search(json_resp)

    async def get_show_segments(self, vpid):
        json_resp = await self._get_json(
            url_template=URLs.SEGMENTS, url_args={"vpid": vpid}
        )
        return parse_container(json_resp)
