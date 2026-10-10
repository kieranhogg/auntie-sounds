import logging
from dataclasses import dataclass
from enum import StrEnum, auto, unique
from typing import Literal

from auntie_sounds import VERBOSE_LOG_LEVEL
from auntie_sounds.endpoints import Endpoints, URLs
from auntie_sounds.exceptions import APIResponseError, InvalidArgumentsError
from auntie_sounds.requests import RequestManager
from auntie_sounds.utils import service_id_to_station_id, station_id_to_service_id

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


@unique
class PlayMode(StrEnum):
    """The play modes that can be sent to the heartbeat API."""

    ONDEMAND = auto()
    LIVE = auto()


@unique
class ResourceType(StrEnum):
    """The resources types that can be sent to the heartbeat API."""

    EPISODE = auto()


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

    def __init__(self, requests: RequestManager, **kwargs) -> None:
        self.requests = requests

    async def get_stream_token(self, station_id, international: bool = False) -> str:
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
        if "token" not in json or not json.get("token"):
            raise APIResponseError(f"Couldn't get JWT token: {json}")
        return str(json.get("token"))

    async def get_live_stream(
        self,
        station_id: str,
        preferences: StreamPreference | None = None,
        international: bool = False,
    ) -> str | None:
        """
        Get a stream for a live radio station.

        :param station_id: the ID of the station (also known as the service ID)
        :param preferences: an optional StreamPreferences object to state the requested stream's preferred options
        :param international: set to True if this is an international stream, False if not
        :return:
        """
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
                headers={"Authorization: Bearer": jwt_token},
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
                # headers={"Bearer": jwt_token},
            )
            logger.log(VERBOSE_LOG_LEVEL, json_resp)
        return _extract_stream(json_resp, preferences=preferences)

    async def get_episode_stream(
        self, vpid: str, preferences: StreamPreference | None = None
    ) -> str | None:
        """
        Gets the stream for a specified episode.

        :param vpid: the version PID of the episode
        :param preferences: an optional StreamPreferences object to state the requested stream's preferred options
        :return: the string containing the stream URL, or None
        """
        if not preferences:
            preferences = StreamPreference()

        json_resp = await self.requests.get_json_response(
            url=URLs.EPISODE_MEDIASET, url_args={"episode_id": vpid}
        )
        logger.log(VERBOSE_LOG_LEVEL, json_resp)
        return _extract_stream(json_resp, preferences=preferences)

    async def update_episode_play_status(
        self,
        pid: str,
        vpid: str,
        action: PlayStatus,
        elapsed_time: int,
    ) -> bool:
        """Update the API's play status endpoint with the latest episode progress/action.

        :param pid: the episode, or current station programme's pid
        :param action: a `PlayStatus` value for the current action
        :param elapsed_time: the time listened so far, only applicable to
        :param vpid: version pid of the episode
        :return: True if the update suceeded, raises APIResponseError if not

        :raises APIResponseError(msg, status) if HTTP 202 not returned
        """
        data = {
            "action": action,
            "elapsed_time": elapsed_time,
            "pid": pid,
            "version_pid": vpid,
            "play_mode": PlayMode.ONDEMAND,
            "resource_type": ResourceType.EPISODE,
        }
        return await self._update_play_status(data)

    async def update_live_play_status(
        self,
        pid: str,
        action: PlayStatus,
        service_id: str | None = None,
    ) -> bool:
        """Update the API's play status endpoint with the latest live stream action.

        :param pid: the episode, or current station programme's pid
        :param action: a `PlayStatus` value for the current action
        :param service_id: service ID of the radio station
        :return: True if the update suceeded, raises APIResponseError if not

        :raises APIResponseError(msg, status) if HTTP 202 not returned
        """
        data = {
            "action": action,
            "pid": pid,
            "play_mode": PlayMode.LIVE,
            "resource_type": ResourceType.EPISODE,
            "metadata": {"service_id": service_id, "platform": "web"},
        }
        return await self._update_play_status(data)

    async def _update_play_status(
        self,
        data: dict,
    ) -> bool:
        """Update the API's play status endpoint with the latest progress/action.

        :param data: the dictionary parameters to send to the endpoint
        :return: True if the update suceeded, raises APIResponseError if not

        :raises APIResponseError(msg, status) if HTTP 202 not returned
        """
        async with await self.requests.make_request(
            method="POST", url=Endpoints.PLAYS, json=data
        ) as resp:
            # We're expected a 202 here
            if not resp.ok:
                json_resp = await resp.json()
                logger.debug(json_resp)
                raise APIResponseError(resp.reason, resp.status)
        return True
