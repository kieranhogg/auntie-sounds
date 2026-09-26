import asyncio.constants
import logging
from datetime import datetime as dt
from datetime import timedelta
from itertools import chain
from typing import TYPE_CHECKING, Literal

from anyio.functools import lru_cache

from sounds import VERBOSE_LOG_LEVEL
from sounds.endpoints import Endpoints
from sounds.exceptions import (
    APIResponseError,
    InvalidArgumentsError,
    NotFoundError,
)
from sounds.models import (
    LiveStation,
    MenuItem,
    Network,
    PlayableNetwork,
    Schedule,
    Station,
)
from sounds.parser import Parser

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from sounds.playback import PlaybackService
    from sounds.requests import RequestManager
    from sounds.schedule import ScheduleService


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
        self.parser: Parser = Parser()
        self.local_networks: list[str] = []
        self.national_networks: list[str] = []
        self.international_networks: list[str] = [
            "bbc_afrique_radio",
            "bbc_arabic_radio",
            "bbc_burmese_radio", #"p0gwwsz2"
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

    @lru_cache(maxsize=1)
    def _is_local_network(self, network_id):
        if not self.local_networks:
            raise AttributeError("No local_networks.")
        return network_id in self.local_networks

    @lru_cache(maxsize=1)
    def _is_national_network(self, network_id):
        if not self.national_networks:
            raise AttributeError("No national_networks.")
        return network_id in self.national_networks

    @lru_cache(maxsize=19)
    def _is_international_network(self, network_id):
        """Check if the network is classed as an international network.

        There is a group of radio networks that aren't present in most of the API endpoints,
        but are nevertheless available to request a stream via an international endpoint."""
        return network_id in self.international_networks

    @lru_cache(maxsize=1)
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
            except KeyError, IndexError:
                raise APIResponseError("Station list response not as expected.")

            if include_local_stations and include_national_stations:
                requested_stations = list(chain([national_stations, local_stations]))
            elif include_national_stations:
                requested_stations = national_stations
            elif include_local_stations:
                requested_stations = local_stations
        stations_list = []

        parsed_stations = self.parser.parse_node(requested_stations)
        if isinstance(parsed_stations, list):
            stations_list.extend([
                s for s in parsed_stations if isinstance(s, (Station, LiveStation))
            ])
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
            for station, stream in zip(needs_stream, streams):
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
        stream_format: Literal["hls", "dash"] = "hls",
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
        if station_id in self.international_networks:
            station = await self._get_international_station(
                station_id, include_stream=include_stream, stream_format=stream_format
            )
            station.international = True
            return station

        json_response = await self.requests.get_json_response(
            url=Endpoints.STATION_PLAYABLE_DETAILS,
            url_args={"station_id": station_id},
        )
        station = self.parser.parse_node(json_response)

        if not isinstance(station, LiveStation):
            return None
        if include_stream:
            stream = await self.playback.get_live_stream(
                station_id=station_id, stream_format=stream_format
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
        include_stream: bool = False,
        stream_format: Literal["hls", "dash"] = "hls",
    ):
        networks = await self.get_networks()
        network = next(n for n in networks if n.id == station_id)
        station = network.service

        if not isinstance(station, Station):
            return None
        if include_stream:
            stream = await self.playback.get_live_stream(
                station_id=station_id, stream_format=stream_format, international=True
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

    async def get_radio_menu(
        self,
        include_national_stations: bool = True,
        include_local_stations: bool = False,
        include_international_stations: bool = False,
    ):
        return MenuItem(
            id="radio",
            title="Live Radio",
            sub_items=await self.get_stations(
                include_local_stations=include_local_stations,
                include_national_stations=include_national_stations,
                include_international_stations=include_international_stations,
            ),
        )

    async def get_schedule_menu(
        self,
        include_national_stations: bool = True,
        include_local_stations: bool = False,
        include_international_stations: bool = False,
        depth=2,
    ):
        """Get station schedules converted into a `MenuItem`.

        Parameters:
            depth: truncate the menu for later data retrieval. As follows: **Station Schedules > Radio One** *(depth = 2)* **> Today** *(depth = 3)* **> Programme Listing** *(depth = 4)*

        """

        def _station_to_schedule(station: LiveStation | Station) -> Schedule | None:
            return (
                Schedule(id=station.id, image_url=station.network.logo_url)
                if station and station.network
                else None
            )

        menu_item = MenuItem(
            id="schedule",
            title="Station Schedules",
        )
        if depth == 2:
            menu_item.sub_items = [
                result
                for result in (
                    _station_to_schedule(station)
                    for station in await self.get_stations()
                )
                if result is not None
            ]
            return menu_item

        menu_item.sub_items = [
            await self.get_network_schedule_or_catch_up_menu(
                station_id=station.id, catch_up=False, include_listings=(depth == 4)
            )
            for station in await self.get_stations(
                include_national_stations=include_national_stations,
                include_local_stations=include_local_stations,
                include_international_stations=include_international_stations,
            )
        ]
        return menu_item

    async def get_catch_up_menu(self, include_local_stations: bool = False):
        return MenuItem(
            id="catch_up",
            title="Catch-up Radio",
            sub_items=[],
            # await self.get_station_schedule_or_catch_up_menu(
            #     station.id, catch_up=True
            # )
            # for station in await self.get_networks(
            #     include_local_networks=include_local
            # )
            # ],
        )

    async def get_network_schedule_or_catch_up_menu(
        self, station_id: str, catch_up: bool = True, include_listings: bool = True
    ) -> MenuItem:
        station = await self.get_station(station_id)
        if not station:  # or not isinstance(station, LiveStation):
            raise NotFoundError(f"Couldn't get station with id {station_id}")

        menu_item = MenuItem(
            id=station_id,
            title=station.network.short_title
            if station and station.network
            else "Unknown Station",
            image_url=station.network.logo_url if station and station.network else None,
        )
        if include_listings:
            start_date = dt.now(tz=self.schedules.timezone).date()
            if catch_up:
                end_date = start_date - timedelta(days=30)
            else:
                end_date = start_date + timedelta(days=7)
            date_data = await self.schedules.get_station_schedules(
                station_id, start_date, end_date
            )
            menu_item.sub_items = date_data
        return menu_item

    @staticmethod
    def station_id_to_service_id(station_id):
        """
        'bbc_radio_wales_fm', 'bbc_radio_wales_am',
         'bbc_radio_scotland_fm', 'bbc_radio_scotland_mw',
        # [
        #     (URLs.STATIONS, ("bbc_radio_fourfm"),
        #     (URLs.LIVE_STATION_DETAILS, ("bbc_radio_fourfm"),
        #     (URLs.NETWORK_DETAILS, ("bbc_radio_four"),
        #     (URLs.NETWORK_PLAYABLE_DETAILS, ("bbc_radio_four"),
        #     (URLs.NOW_PLAYING, ("bbc_radio_fourfm"),
        #     (URLs.SCHEDULE, ("bbc_radio_fourfm"),
        #     (URLs.SCHEDULE_DATE, ("bbc_radio_fourfm"),
        # ]
        """
        return "bbc_radio_fourfm" if station_id == "bbc_radio_four" else station_id

    @staticmethod
    def service_id_to_station_id(service_id):
        return "bbc_radio_four" if service_id == "bbc_radio_fourfm" else service_id
