import asyncio.constants
import logging
from datetime import datetime as dt
from datetime import timedelta
from itertools import chain
from typing import Literal

from sounds import VERBOSE_LOG_LEVEL
from sounds.endpoints import URLs
from sounds.exceptions import APIResponseError, NotFoundError
from sounds.models import LiveStation, MenuItem, Network
from sounds.parser import Parser
from sounds.playback import PlaybackService
from sounds.requests import RequestManager
from sounds.schedule import ScheduleService
from sounds.utils import _date_with_ordinal

logger = logging.getLogger(__name__)


class StationService:
    def __init__(
        self,
        playback: PlaybackService,
        schedules: ScheduleService,
        requests: RequestManager,
    ):
        self.playback = playback
        self.schedules = schedules
        self.requests = requests
        self.parser = Parser()

    async def get_networks(self) -> list[Network] | None:
        json_resp = await self.requests.get_json_response(url=URLs.NETWORKS_LIST)
        stations = self.parser.parse_container(json_resp)
        if isinstance(stations, list):
            station_list: list[Network] = [
                station for station in stations if isinstance(station, Network)
            ]
            return station_list
        return []

    async def get_stations(
        self,
        include_local: bool = False,
        include_streams: bool = False,
        include_schedules: bool = False,
    ) -> list[LiveStation]:
        """
        Gets the list of all stations

        :return: A list of Station objects
        :rtype: list[Station]
        """
        json_resp = await self.requests.get_json_response(url=URLs.STATIONS)
        logger.log(VERBOSE_LOG_LEVEL, "Getting station list...")
        logger.log(VERBOSE_LOG_LEVEL, json_resp)

        try:
            national_stations = json_resp["data"][0]["data"]
            local_stations = json_resp["data"][1]["data"]
        except KeyError, IndexError:
            raise APIResponseError("Station list response not as expected.")

        if include_local:
            requested_stations = list(chain([national_stations, local_stations]))
        else:
            requested_stations = national_stations

        stations_list = self.parser.parse_node(requested_stations)

        if isinstance(stations_list, list):
            all_stations: list[LiveStation] = [
                station for station in stations_list if type(station) is LiveStation
            ]

            if include_streams and isinstance(stations_list, list):
                # Parallelise the requests to improve speed, one to watch for API rates in future
                needs_stream = [s for s in all_stations if not s.stream]
                streams = await asyncio.gather(
                    *(self.playback.get_live_stream(s.id) for s in needs_stream)
                )
                for station, stream in zip(needs_stream, streams):
                    station.stream = stream

            if include_schedules and isinstance(stations_list, list):
                needs_schedule = [s for s in all_stations if not s.schedule]
                schedules = await asyncio.gather(
                    *(self.schedules.get_schedule(s.id) for s in needs_schedule)
                )
                for station, schedule in zip(needs_schedule, schedules):
                    station.schedule = schedule
            return all_stations
        return []

    async def get_local_stations(self) -> list[LiveStation]:
        json_resp = await self.requests.get_json_response(url=URLs.STATIONS)
        logger.log(VERBOSE_LOG_LEVEL, "Getting local station list...")
        logger.log(VERBOSE_LOG_LEVEL, json_resp)
        station_data = json_resp["data"][1]["data"]
        station_list = [self.parser.parse_node(s) for s in station_data]
        local_stations: list[LiveStation] = [
            station for station in station_list if type(station) is LiveStation
        ]
        return local_stations

    async def get_station_schedule(
        self,
        station_id: str,
        include_stream: bool = False,
        include_schedule: bool = False,
        date: str | None = None,
    ) -> LiveStation | None:
        """
        Gets a station's details

        :return: A Station object
        :rtype: Station
        """
        stations = await self.get_stations(
            include_local=True,
        )
        station = next(
            (station for station in stations if station.id == station_id),
            None,
        )
        if not station:
            return None

        if include_stream:
            station.stream = await self.playback.get_live_stream(station.id)
        if include_schedule:
            station.schedule = await self.schedules.get_schedule(station.id, date=date)
        return station

    async def get_station(
        self,
        station_id: str,
        include_stream: bool = False,
        stream_format: Literal["hls", "dash"] = "hls",
        include_schedule: bool = False,
        date: str | None = None,
    ) -> LiveStation | None:
        """Get a live radio station

        Args:
            station_id (str): ID of the station, e.g. bbc_radio_four
            include_stream (bool, optional): Set LiveStation.stream to the stream URL. Defaults to False.
            stream_format (Literal["hls"] | Literal["dash"], optional): Stream format preference. Defaults to "hls".
            include_schedule (bool, optional): Set LiveStation.schedule to the station schedule. Defaults to False.
            date (str | None, optional): The date of the schedule, if `include_schedule` is True. Defaults to None.

        Returns:
            LiveStation | None: A LiveStation object if station_id is found
        """
        json_response = await self.requests.get_json_response(
            url=URLs.STATION_PLAYABLE_DETAILS,
            url_args={"station_id": station_id},
        )
        station = self.parser.parse_node(json_response)

        # station id is almost always the same as pid but not quite, e.g. bbc_radio_fourfm and bbc_radio_four
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

    async def get_broadcast(self, pid: str):
        json_resp = await self.requests.get_json_response(
            url=URLs.BROADCAST, url_args={"pid": pid}
        )
        broadcast = self.parser.parse_node(json_resp)
        return broadcast

    async def get_schedule_menu(self, include_local: bool = False):

        return MenuItem(
            id="stations",
            title="Station & Schedules",
            sub_items=[
                await self.get_station_menu(station.id)
                for station in await self.get_stations(include_local=include_local)
            ],
        )

    async def get_station_menu(self, station_id: str) -> MenuItem:
        station = await self.get_station(station_id)
        if not station or not isinstance(station, LiveStation):
            raise NotFoundError(f"Couldn't get station with id {station_id}")

        schedule = [
            MenuItem(
                id=dt.now(tz=self.schedules.timezone).strftime("%Y-%m-%d"),
                title="Today",
                sub_items=[],
            ),
            MenuItem(
                id=(dt.now(tz=self.schedules.timezone) - timedelta(days=1)).strftime(
                    "%Y-%m-%d"
                ),
                title="Yesterday",
                sub_items=[],
            ),
        ]
        # Maximum is 30 days prior
        for diff in range(28):
            this_date = dt.now(tz=self.schedules.timezone) - timedelta(days=2 + diff)
            schedule.extend(
                [
                    MenuItem(
                        id=this_date.strftime("%Y-%m-%d"),
                        title=_date_with_ordinal(this_date),
                        sub_items=[],
                    )
                ]
            )
        return MenuItem(
            id=station_id,
            title=station.network.short_title if station.network else "Unknown Station",
            image_url=station.network.logo_url if station.network else None,
            sub_items=schedule,
        )
