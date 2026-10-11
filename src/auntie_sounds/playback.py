import logging
from dataclasses import dataclass
from enum import StrEnum, auto, unique
from typing import Literal

from auntie_sounds.constants import VERBOSE_LOG_LEVEL
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


def _best_media_connections(json_resp: dict) -> list[dict]:
    """Return the connections of the highest bitrate media variant.

    Mediaselector doesn't promise an order for `media`, so the first entry
    can be a lower bitrate variant.
    """
    try:
        media = max(json_resp["media"], key=lambda item: int(item.get("bitrate", 0)))
        return media["connection"]
    except (KeyError, TypeError, ValueError) as e:
        raise APIResponseError("No valid stream found") from e


def _extract_streams(json_resp: dict, preferences: StreamPreference) -> list[str]:
    """Return the ranked stream URLs from a mediaselector response, best first."""
    connections = _best_media_connections(json_resp)
    variants = get_stream_variants(connections=connections, preferences=preferences)
    logger.debug("Stream variants: %s", variants)
    return [href for variant in variants if (href := variant.get("href"))]


def get_stream_variants(
    connections: list[dict], preferences: StreamPreference
) -> list[dict]:
    """Rank the mediaselector connections, best first, keeping one per supplier.

    StreamPreference.stream_type is treated as a requirement, the rest as preferences.
    Each entry after the first is from a different CDN supplier, so a caller
    whose first stream fails to connect can fall back to another CDN.
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
        return []

    def rank(connection: dict) -> tuple[bool, bool, int]:
        """Rank a connection, where the lowest tuple is the best.

        Each preference is scored as a boolean check, inverted so a match sorts
        first, followed by mediaselector's own priority. The protocol comes
        before the supplier, so an HTTPS stream is picked over an HTTP one
        whenever both exist, whatever the supplier preference.

        The ideal rank is e.g. (False, False, 10) for protocol yes, supplier yes, priority 10.
        """
        protocol_matches = connection.get("protocol") == preferences.protocol
        supplier_matches = (
            preferences.supplier is None
            or preferences.supplier in connection.get("supplier", "")
        )

        return (
            not protocol_matches,
            not supplier_matches,
            int(connection.get("priority", 0)),
        )

    best_per_supplier: dict[str, dict] = {}
    for connection in sorted(candidates, key=rank):
        best_per_supplier.setdefault(connection.get("supplier", ""), connection)
    return list(best_per_supplier.values())


def get_stream_variant(
    connections: list[dict], preferences: StreamPreference
) -> dict | None:
    """Pick the best mediaselector connection, see get_stream_variants."""
    variants = get_stream_variants(connections=connections, preferences=preferences)
    return variants[0] if variants else None


class PlaybackService:
    """Actions to do with turning an ID into audio, or reporting playback progress.

    ContentService finds items, PlaybackService focuses on playing-type actions.
    """

    def __init__(self, requests: RequestManager) -> None:
        self.requests = requests

    async def get_stream_token(self, station_id) -> str:
        """Requests a stream JWT for a station from rms.

        International stations do not need a token.
        """
        url_args = {"id": station_id_to_service_id(station_id)}
        json = await self.requests.get_json_response(url=URLs.JWT, url_args=url_args)
        if not json.get("token"):
            raise APIResponseError(f"Couldn't get JWT token: {json}")
        return str(json["token"])

    async def get_live_streams(
        self,
        station_id: str,
        preferences: StreamPreference | None = None,
        international: bool = False,
    ) -> list[str]:
        """
        Get the stream URLs for a live radio station, best first.

        Each URL after the first is from a different CDN supplier, to try if
        the first fails to connect.

        :param station_id: the ID of the station (also known as the service ID)
        :param preferences: an optional StreamPreferences object to state the requested stream's preferred options
        :param international: set to True if this is an international stream, False if not
        :return: the stream URLs, which is empty if none match the preferences
        """
        if not station_id:
            raise InvalidArgumentsError("station_id is required.")
        if not preferences:
            preferences = StreamPreference()

        station_id = service_id_to_station_id(station_id)
        url_args = {"id": station_id_to_service_id(station_id)}

        if international:
            headers = None
        else:
            jwt_token = await self.get_stream_token(station_id)
            headers = {"Authorization": f"Bearer {jwt_token}"}

        json_resp = await self.requests.get_json_response(
            url=URLs.MEDIASET, url_args=url_args, headers=headers
        )
        logger.log(VERBOSE_LOG_LEVEL, json_resp)
        return _extract_streams(json_resp, preferences=preferences)

    async def get_live_stream(
        self,
        station_id: str,
        preferences: StreamPreference | None = None,
        international: bool = False,
    ) -> str | None:
        """
        Get the best stream URL for a live radio station, see get_live_streams.

        :return: the stream URL, or None if none match the preferences
        """
        streams = await self.get_live_streams(
            station_id, preferences=preferences, international=international
        )
        return streams[0] if streams else None

    async def get_episode_streams(
        self, vpid: str, preferences: StreamPreference | None = None
    ) -> list[str]:
        """
        Get the stream URLs for an episode, best first.

        Each URL after the first is from a different CDN supplier, to try if
        the first fails to connect.

        :param vpid: the version PID of the episode
        :param preferences: an optional StreamPreferences object to state the requested stream's preferred options
        :return: the stream URLs, which is empty if none match the preferences
        """
        return await self._get_streams(vpid, preferences)

    async def get_episode_stream(
        self, vpid: str, preferences: StreamPreference | None = None
    ) -> str | None:
        """
        Gets the best stream URL for an episode, see get_episode_streams.

        :param vpid: the version PID of the episode
        :param preferences: an optional StreamPreferences object to state the requested stream's preferred options
        :return: the string containing the stream URL, or None
        """
        streams = await self.get_episode_streams(vpid, preferences=preferences)
        return streams[0] if streams else None

    async def _get_streams(
        self,
        media_id: str,
        preferences: StreamPreference | None,
        jwt_token: str | None = None,
    ) -> list[str]:
        """Ask mediaselector for an id's streams and rank them.

        Episodes don't need a token. Live stations need the JWT as a Bearer header.
        """
        headers = {"Authorization": f"Bearer {jwt_token}"} if jwt_token else None
        json_resp = await self.requests.get_json_response(
            url=URLs.MEDIASET, url_args={"id": media_id}, headers=headers
        )
        logger.log(VERBOSE_LOG_LEVEL, json_resp)
        return _extract_streams(
            json_resp, preferences=preferences or StreamPreference()
        )

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
