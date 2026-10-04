import logging
from enum import StrEnum
from typing import Literal

from sounds import VERBOSE_LOG_LEVEL
from sounds.endpoints import Endpoints, URLs
from sounds.exceptions import APIResponseError, InvalidArgumentsError
from sounds.requests import RequestManager
from sounds.stations import StationService

logger = logging.getLogger(__name__)


def _extract_stream(json_resp: dict, prefer_type) -> str | None:
    try:
        streams = json_resp["media"][0]["connection"]
    except (KeyError, IndexError, TypeError) as e:
        raise APIResponseError("No valid stream found") from e
    return get_best_stream(streams, prefer_type=prefer_type)


def get_best_stream(
    streams: list[dict], prefer_type: Literal["hls", "dash"] = "hls"
) -> str | None:
    """Looks for the first valid stream with the requested format."""
    logger.log(VERBOSE_LOG_LEVEL, "Looking for best stream in:")
    logger.log(VERBOSE_LOG_LEVEL, streams)

    return next(
        (
            conn["href"]
            for conn in streams
            if conn.get("transferFormat", "") == prefer_type
        ),
        None,
    )


class PlaybackService:
    """Actions to do with turning an ID into audio, or reporting playback progress.

    ContentService deals with resolving items, this service deals with just playing items.
    """

    def __init__(self, requests: RequestManager, **kwargs):
        self.requests = requests

    async def get_stream_token(self, station_id, international: bool = False):
        """Requests a JWT token for a given station.

        For now, this also works for non-UK listeners, returning a non-UK stream when used.
        """
        if international:
            id_type = "serviceId"
            id = station_id
            params = {id_type: id}
            json = await self.requests.get_json_response(
                url=URLs.INTL_JWT, params=params
            )
        else:
            url_args = {"id": StationService.station_id_to_service_id(station_id)}
            json = await self.requests.get_json_response(
                url=URLs.JWT, url_args=url_args
            )
        if "token" not in json:
            raise APIResponseError(f"Couldn't get JWT token: {json}")
        return json.get("token")

    async def get_live_stream(
        self,
        station_id: str,
        prefer_type: Literal["hls", "dash"] = "hls",
        international: bool = False,
    ) -> str | None:
        if not station_id:
            raise InvalidArgumentsError("station_id is required.")
        station_id = StationService.service_id_to_station_id(station_id)

        jwt_token = await self.get_stream_token(station_id, international=international)
        if not jwt_token:
            raise APIResponseError("No JWT token received.")

        if international:
            json_resp = await self.requests.get_json_response(
                url=URLs.I18N_MEDIASET,
                url_args={"id": station_id},
                headers={"Bearer": jwt_token},
            )
        else:
            params = {
                "jwt_auth": jwt_token,
            }
            url_args = {"id": StationService.station_id_to_service_id(station_id)}

            json_resp = await self.requests.get_json_response(
                url=URLs.MEDIASET,
                url_args=url_args,
                params=params,
                headers={"Bearer": jwt_token},
            )
        return _extract_stream(json_resp, prefer_type=prefer_type)

    async def get_episode_stream(
        self,
        episode_id: str,
        prefer_type: Literal["hls", "dash"] = "hls",
    ) -> str | None:
        """
        Gets the stream for a specified episode.
        """
        json_resp = await self.requests.get_json_response(
            url=URLs.EPISODE_MEDIASET, url_args={"episode_id": episode_id}
        )
        return _extract_stream(json_resp, prefer_type=prefer_type)

    async def update_play_status(
        self,
        pid: str,
        elapsed_time: int,
        action: PlayStatus,
        vpid: str,
        resource_type: str,
    ):
        data = {
            "action": action,
            "elapsed_time": elapsed_time,
            "pid": pid,
            "play_mode": "ondemand",
            "version_pid": vpid,
            "resource_type": resource_type,
        }
        resp = await self.requests.make_request(
            method="POST", url=Endpoints.PLAYS, json=data
        )
        if resp.status != 202:
            raise APIResponseError(await resp.json(), resp.status)
        return True


class PlayStatus(StrEnum):
    STARTED = "started"
    PAUSED = "paused"
    ENDED = "ended"
    HEARTBEAT = "heartbeat"
