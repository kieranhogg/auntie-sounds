import logging
from dataclasses import dataclass
from enum import StrEnum, auto, unique
from typing import Literal

from sounds import VERBOSE_LOG_LEVEL
from sounds.endpoints import Endpoints, URLs
from sounds.exceptions import APIResponseError, InvalidArgumentsError
from sounds.requests import RequestManager
from sounds.utils import service_id_to_station_id, station_id_to_service_id

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class StreamPreference:
    """A representation of a set of preferences for a stream request."""

    stream_type: Literal["hls", "dash"] = "hls"
    protocol: Literal["http", "https"] = "https"
    supplier: Literal["akamai", "cloudfront"] | None = None


@unique
class PlayStatus(StrEnum):
    """The statuses types that can be sent to the heartbeat API."""

    STARTED = auto()
    PAUSED = auto()
    ENDED = auto()
    HEARTBEAT = auto()


def _extract_stream(json_resp: dict, preferences: StreamPreference) -> str | None:
    """Helper to prevent to grab the connection data from the json response."""
    try:
        connections = json_resp["media"][0]["connection"]
    except (KeyError, IndexError, TypeError) as e:
        raise APIResponseError("No valid stream found") from e
    stream = get_stream_variant(connections=connections, preferences=preferences)
    if not stream:
        return None
    logger.debug("Stream details: %s", stream)
    return stream.get("href", None)


def get_stream_variant(
    connections: list[dict], preferences: StreamPreference
) -> dict | None:
    """Pick the best mediaselector connection.

    StreamPreference.stream_type is treated as a requirement, the rest as preferences.
    """

    candidates = [
        connection
        for connection in connections
        if connection.get("transferFormat") == preferences.stream_type
    ]

    if not candidates:
        logger.warning(
            "Requested stream_type %s is not available",
            preferences.stream_type,
        )
        return None

    def rank(connection: dict) -> tuple[int, int, int]:
        """Rank the remaining streams.

        We rank the connection by 'scoring' the supplier and protocol as a boolean
        check, then invert it, so lowest is better, to go with the existing priority.

        The ideal rank is e.g. 0, 0, 10 -> supplier yes, protocol yes, priority 10."""
        supplier_matches = (
            preferences.supplier is None
            or preferences.supplier in connection.get("supplier", "")
        )
        protocol_matches = connection.get("protocol") == preferences.protocol

        return (
            not supplier_matches,
            not protocol_matches,
            int(connection.get("priority", 0)),
        )

    return min(candidates, key=rank)


class PlaybackService:
    """Actions to do with turning an ID into audio, or reporting playback progress.

    ContentService finds items, PlaybackService focuses on playing-type actions.
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
            url_args = {"id": station_id_to_service_id(station_id)}
            json = await self.requests.get_json_response(
                url=URLs.JWT, url_args=url_args
            )
        if "token" not in json:
            raise APIResponseError(f"Couldn't get JWT token: {json}")
        return json.get("token")

    async def get_live_stream(
        self,
        station_id: str,
        preferences: StreamPreference | None = None,
        international: bool = False,
    ) -> str | None:
        if not station_id:
            raise InvalidArgumentsError("station_id is required.")
        if not preferences:
            preferences = StreamPreference()

        station_id = service_id_to_station_id(station_id)

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
            url_args = {"id": station_id_to_service_id(station_id)}

            json_resp = await self.requests.get_json_response(
                url=URLs.MEDIASET,
                url_args=url_args,
                params=params,
                headers={"Bearer": jwt_token},
            )
            logger.log(VERBOSE_LOG_LEVEL, json_resp)
        return _extract_stream(json_resp, preferences=preferences)

    async def get_episode_stream(
        self, episode_id: str, preferences: StreamPreference | None = None
    ) -> str | None:
        """
        Gets the stream for a specified episode.
        """
        if not preferences:
            preferences = StreamPreference()

        json_resp = await self.requests.get_json_response(
            url=URLs.EPISODE_MEDIASET, url_args={"episode_id": episode_id}
        )
        logger.log(VERBOSE_LOG_LEVEL, json_resp)
        return _extract_stream(json_resp, preferences=preferences)

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
