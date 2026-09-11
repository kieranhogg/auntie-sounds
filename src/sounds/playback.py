import logging
from typing import Literal

from sounds import constants
from sounds.base import Base
from sounds.constants import PlayStatus, SignedInURLs, URLs
from sounds.exceptions import APIResponseError

logger = logging.getLogger(__name__)


def get_best_stream(
        streams: dict, prefer_type: Literal["hls", "dash"] = "hls"
) -> str | None:
    """Looks for the first valid stream with the requested format."""
    logger.log(constants.VERBOSE_LOG_LEVEL, "Looking for best stream in:")
    logger.log(constants.VERBOSE_LOG_LEVEL, streams)

    return next(
        (
            conn["href"]
            for conn in streams
            if conn.get("transferFormat", "") == prefer_type
        ),
        None,
    )


class PlaybackService(Base):
    """Actions to do with turning an ID into audio, or reporting playback progress.

    ContentService deals with resolving items, this service deals with just playing items.
    """

    async def get_stream_jwt_token(self, station_id):
        """Requests a JWT token for a given station.

        For now, this also works for non-UK listeners, returning a non-UK stream when used.
        """
        json = await self._get_json(
            url_template=URLs.JWT, url_args={"station_id": station_id}
        )
        if "token" not in json:
            raise APIResponseError(f"Couldn't get JWT token: {json}")
        return json.get("token")

    async def get_live_stream(
        self, station_id: str, stream_format: Literal["hls", "dash"] = "hls"
    ) -> str | None:
        jwt_token = await self.get_stream_jwt_token(station_id)

        json_resp = await self._get_json(
            url_template=URLs.MEDIASET,
            url_args={"station_id": station_id, "jwt_auth_token": jwt_token},
            headers={"Bearer": jwt_token},
        )
        stream = None
        try:
            streams = json_resp["media"][0]["connection"]
            logger.debug("Found streams:")
            logger.debug(str(streams))
            stream = get_best_stream(streams, prefer_type=stream_format)
            logger.debug(f"Found stream: {stream}")
        except StopIteration, KeyError:
            logger.error("No valid stream found")
            logger.debug(json_resp)
            raise RuntimeError("No valid stream found")

        return stream

    async def get_episode_stream(
        self,
        episode_id: str,
        stream_format: Literal["hls", "dash"] = "hls",
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

        streams = None
        try:
            streams = json_resp["media"][0]["connection"]
            logger.debug("Found streams:")
            logger.debug(str(streams))
            stream = get_best_stream(streams, prefer_type=stream_format)
            logger.debug(f"Found stream: {stream}")
        except StopIteration, KeyError:
            raise RuntimeError("No valid stream found")
        return stream

    async def get_heartbeat_details(self, pid):
        json_resp = await self._get_json(
            url_template=URLs.PID_DETAILS, url_args={"pid": pid}
        )
        logger.debug(f"Heartbeat details response: {json_resp}")
        try:
            vpid = json_resp["defaultAvailableVersion"]["smpConfig"]["items"][0]["vpid"]
            item_type = json_resp["statsObject"]["parentPIDType"]
        except APIResponseError, KeyError, TypeError:
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
