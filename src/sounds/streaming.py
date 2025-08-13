import json
import logging
import re
from datetime import datetime as dt
from typing import Optional

from . import constants
from .utils import network_logo
from .base import Base
from .constants import ContainerType, URLs
from .exceptions import APIResponseError
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

    async def get_live_stream(
        self,
        station: Station,
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
        url = URLs.LIVE_STATION_URL.format(station_id=station.id)
        html_resp = await self._get_html(url)
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
        jwt_token = await self.get_jwt_token(station.id)

        async with self._session.get(
            URLs.MEDIASET_URL.format(
                station_id=station.id,
                jwt_auth_token=jwt_token,
            )
        ) as resp:
            if resp.status != 200:
                raise RuntimeError("Failed to receive stream")
            data = await resp.json()

            try:
                stream = self._get_best_stream(
                    data["media"][0]["connection"], prefer_type=stream_format
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
            image_url=image_from_recipe(
                programme_details["image_url"], size=f"{logo_size}x{logo_size}"
            ),
            show_title=programme_details["titles"]["primary"],
            show_description=programme_details["titles"]["secondary"],
            station=station,
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
        url = URLs.EPISODE_MEDIASET.format(episode_id=episode_id)
        json_resp = await self._get_json(url)

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

    async def get_by_pid(self, pid):
        json_resp = await self._get_json(URLs.PID_PLAYABLE.format(pid=pid))
        return PlayableItem(
            id=json_resp["id"],
            urn=json_resp["urn"],
            network=(
                Network(
                    id=json_resp["network"]["id"],
                    key=json_resp["network"]["key"],
                    short_title=json_resp["network"]["short_title"],
                    logo_url=json_resp["network"]["logo_url"],
                )
                if json_resp.get("network") is not None
                else None
            ),
            duration=(
                json_resp["duration"]["value"]
                if json_resp.get("duration") is not None
                else None
            ),
            progress=(
                json_resp["progress"]["value"]
                if json_resp.get("progress") is not None
                else None
            ),
            synopses=(
                json_resp["synopses"] if json_resp.get("synopses") is not None else {}
            ),
            _image_url=json_resp["image_url"],
            titles=(json_resp["titles"] if json_resp.get("titles") is not None else {}),
            container=(
                Container(
                    type=ContainerType(json_resp["container"]["type"]),
                    id=json_resp["container"]["id"],
                    urn=json_resp["container"]["urn"],
                    title=json_resp["container"]["title"],
                    synopses=json_resp["container"]["synopses"],
                )
                if json_resp.get("container")
                else None
            ),
        )

    async def get_container(self, urn):
        json_resp = await self._get_json(URLs.CONTAINER_URL.format(urn=urn))
        container_data = json_resp["data"][0]["data"]
        episode_data = json_resp["data"][1]["data"]

        container = Container(
            type=ContainerType(container_data["type"]),
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
                    episode["synopses"] if episode.get("synopses") is not None else {}
                ),
                _image_url=episode["image_url"],
                titles=(episode["titles"] if episode.get("titles") is not None else {}),
            )
            for episode in episode_data
        ]
        return container, episodes
