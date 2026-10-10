import asyncio.constants
import logging
from itertools import chain
from typing import TYPE_CHECKING

from auntie_sounds.constants import VERBOSE_LOG_LEVEL
from auntie_sounds.endpoints import Endpoints
from auntie_sounds.exceptions import (
    APIResponseError,
    InvalidArgumentsError,
    NotFoundError,
)
from auntie_sounds.models import (
    LiveStation,
    Network,
    PlayableNetwork,
    Station,
)
from auntie_sounds.parser import Parser
from auntie_sounds.playback import StreamPreference
from auntie_sounds.utils import service_id_to_station_id

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from auntie_sounds.playback import PlaybackService
    from auntie_sounds.requests import RequestManager
    from auntie_sounds.schedule import ScheduleService


class StationService:
    """StationService is the main way to interact with the radio stations.

    It also provides some wrapping up of station elements into menus for client
    consumption, as well as pulling schedule data from ScheduleService.
    """

    def __init__(
        self,
        playback: PlaybackService,
        schedules: ScheduleService,
        requests: RequestManager,
    ):
        self.playback: PlaybackService = playback
        self.schedules: ScheduleService = schedules
        self.requests: RequestManager = requests
        # Broadcasts are slots on a station and are typed as such, so unlike
        # ContentService and PersonalService this doesn't look up brand owners
        self.parser: Parser = Parser()
        self.international_networks: list[str] = [
            "bbc_afrique_radio",
            "bbc_arabic_radio",
            "bbc_burmese_radio",  # "p0gwwsz2"
            "bbc_dari_radio",
            "bbc_hindi_radio",
            "bbc_gahuza_radio",
            "bbc_hausa_radio",
            "bbc_nepali_radio",
            "bbc_pashto_radio",
            "bbc_uzbek_radio",
            "bbc_somali_radio",
            "bbc_swahili_radio",
        ]

    def _is_international_network(self, network_id):
        """Check if the network is classed as an international network.

        There is a group of radio networks that aren't present in most of the API endpoints,
        but are nevertheless available to request a stream via an international endpoint."""
        return network_id in self.international_networks

    async def get_networks(
        self,
        international_only: bool = False,
    ) -> list[Network | PlayableNetwork]:
        json_resp = await self.requests.get_json_response(
            url=Endpoints.NETWORKS_DETAILED
        )
        networks = self.parser.parse_container(json_resp)
        if type(networks) is not list:
            return []
        for network in networks:
            if not network or type(network) is not Network:
                continue
            if network.id in self.international_networks:
                network.international = True
                if network.service:
                    network.service.international = True
        return [
            network
            for network in networks
            if type(network) is Network
            and (
                not international_only
                or international_only
                and self._is_international_network(network.id)
            )
        ]

    async def get_stations(
        self,
        include_national_stations: bool = True,
        include_local_stations: bool = False,
        include_international_stations: bool = False,
        include_streams: bool = False,
        include_schedules: bool = False,
    ) -> list[LiveStation | Station]:
        """
        Gets the list of all radio stations.

        Parameters:
            include_national_stations: whether to include national radio stations in the returned list
            include_local_stations: whether to include local radio stations in the returned list
            include_international_stations: whether to include international stations in the returned list
            include_streams: whether to append a `.stream` to each object set to the URL of a playable station stream
            include_schedules: whether to append a Schedule object containing the station schedule to`.schedule`
        """
        if not (
            include_national_stations
            or include_local_stations
            or include_international_stations
        ):
            raise InvalidArgumentsError(
                "One of include_national_stations, include_local_stations or include_international_stations must be set to True"
            )
        requested_stations: list[dict] = []
        if include_national_stations or include_local_stations:
            json_resp = await self.requests.get_json_response(url=Endpoints.STATIONS)
            logger.log(VERBOSE_LOG_LEVEL, "Getting station list...")
            logger.log(VERBOSE_LOG_LEVEL, json_resp)

            try:
                national_stations = json_resp["data"][0]["data"]
                local_stations = json_resp["data"][1]["data"]
                local_station_ids = [s["id"] for s in local_stations]
            except (KeyError, IndexError) as e:
                raise APIResponseError("Station list response not as expected.") from e

            if include_local_stations and include_national_stations:
                requested_stations = list(chain(national_stations, local_stations))
            elif include_national_stations:
                requested_stations = national_stations
            elif include_local_stations:
                requested_stations = local_stations
        stations_list = []

        parsed_stations = self.parser.parse_node(requested_stations)
        if isinstance(parsed_stations, list):
            stations_list.extend(
                [s for s in parsed_stations if isinstance(s, (Station, LiveStation))]
            )

        if include_local_stations:
            for station in stations_list:
                if station.id in local_station_ids:
                    station.local = True
        if include_international_stations:
            i18n_stations = await self.get_networks(international_only=True)
            stations_list.extend(
                [
                    network.service
                    for network in i18n_stations
                    if network.service is not None
                ]
            )

        if include_streams and isinstance(stations_list, list):
            # Parallelise the requests to improve speed, one to watch for API rates in future
            needs_stream = [
                s
                for s in stations_list
                if not s.stream and isinstance(s, (Station, LiveStation))
            ]
            streams = await asyncio.gather(
                *(self.playback.get_live_stream(s.id) for s in needs_stream)
            )
            for station, stream in zip(needs_stream, streams, strict=True):
                station.stream = stream

        if include_schedules and isinstance(stations_list, list):
            needs_schedule = [s for s in stations_list if not s.schedule]
            schedules = await asyncio.gather(
                *(self.schedules.get_schedule(s.id) for s in needs_schedule)
            )
            for station, schedule in zip(needs_schedule, schedules):
                station.schedule = schedule
        return stations_list

    async def get_station(
        self,
        station_id: str,
        include_stream: bool = False,
        stream_preferences: StreamPreference | None = None,
        include_schedule: bool = False,
        date: str | None = None,
    ) -> LiveStation | Station | None:
        """Get a live radio station.

        Parameters:
            station_id: ID of the station, e.g. bbc_radio_four
            include_stream (optional): Set LiveStation.stream to the stream URL. Defaults to False.
            stream_format: Stream format preference. Defaults to "hls".
            include_schedule (optional): Set LiveStation.schedule to the station schedule. Defaults to False.
            date (optional): The date of the schedule, if `include_schedule` is True. Defaults to None.
        """
        if not stream_preferences:
            stream_preferences = StreamPreference()

        if station_id in self.international_networks:
            station = await self._get_international_station(
                station_id,
                include_stream=include_stream,
                stream_preferences=stream_preferences,
            )
            if not station:
                return None

            station.international = True
            return station

        station_id = service_id_to_station_id(station_id)

        try:
            json_response = await self.requests.get_json_response(
                url=Endpoints.STATION_PLAYABLE_DETAILS,
                url_args={"station_id": station_id},
            )
            station = self.parser.parse_node(json_response)
        except NotFoundError:
            # Service-only IDs (e.g. bbc_radio_orkney, bbc_radio_scotland_mw) have
            # no network endpoint, but are listed in the stations list and stream.
            stations = await self.get_stations(
                include_national_stations=True, include_local_stations=True
            )
            station = next((s for s in stations if s.id == station_id), None)

        if not isinstance(station, LiveStation):
            return None
        if include_stream:
            stream = await self.playback.get_live_stream(
                station_id=station_id, preferences=stream_preferences
            )
            if stream:
                station.stream = stream

        if include_schedule:
            station.schedule = await self.schedules.get_schedule(
                station_id=station_id, date=date
            )
        return station

    async def _get_international_station(
        self,
        station_id,
        stream_preferences: StreamPreference,
        include_stream: bool = False,
    ):
        networks = await self.get_networks()
        network = next((n for n in networks if n.id == station_id), None)
        station = network.service if network is not None else None

        if not isinstance(station, Station):
            return None
        if include_stream:
            stream = await self.playback.get_live_stream(
                station_id=station_id,
                preferences=stream_preferences,
                international=True,
            )
            if stream:
                station.stream = stream

        return station

    async def get_broadcast(self, pid: str):
        json_resp = await self.requests.get_json_response(
            url=Endpoints.BROADCAST, url_args={"pid": pid}
        )
        broadcast = self.parser.parse_node(json_resp)
        return broadcast
