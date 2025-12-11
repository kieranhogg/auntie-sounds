import itertools
from typing import List, Literal, Optional

from . import constants
from .base import Base
from .constants import URLs
from .models import LiveStation, Network
from .parser import parse_container, parse_node
from .schedules import ScheduleService
from .streaming import StreamingService


class StationService(Base):
    def __init__(
        self,
        streaming_service: StreamingService,
        schedule_service: ScheduleService,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.streams = streaming_service
        self.schedules = schedule_service

    async def get_stations_detailed(self) -> Optional[List[Network]]:
        json_resp = await self._get_json(url_template=URLs.NETWORKS_LIST)
        stations = parse_container(json_resp)
        if isinstance(stations, list):
            station_list: List[Network] = [
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
        json_resp = await self._get_json(url_template=URLs.STATIONS)
        self.logger.log(constants.VERBOSE_LOG_LEVEL, "Getting station list...")
        self.logger.log(constants.VERBOSE_LOG_LEVEL, json_resp)

        # Append a key to assign if they are local stations or not
        for station in json_resp["data"][0]["data"]:
            station["local"] = False

        for station in json_resp["data"][1]["data"]:
            station["local"] = True

        if include_local:
            # Flatten the national and local stations sublists
            stations = list(
                itertools.chain(
                    json_resp["data"][0]["data"], json_resp["data"][1]["data"]
                )
            )

        else:
            # Just get the national data list
            stations = json_resp["data"][0]["data"]
        stations_list = parse_node(stations)

        if isinstance(stations_list, list):
            all_stations: List[LiveStation] = [
                station for station in stations_list if isinstance(station, LiveStation)
            ]

            if include_streams and isinstance(stations_list, list):
                for station in all_stations:
                    station.stream = await self.streams.get_live_stream(station.id)

            if include_schedules and isinstance(stations_list, list):
                for station in all_stations:
                    station.schedule = await self.schedules.get_schedule(station.id)
            return all_stations
        return []

    async def get_local_stations(self) -> List[LiveStation]:
        json_resp = await self._get_json(url_template=URLs.STATIONS)
        self.logger.log(constants.VERBOSE_LOG_LEVEL, "Getting local station list...")
        self.logger.log(constants.VERBOSE_LOG_LEVEL, json_resp)
        station_data = json_resp["data"][1]["data"]
        station_list = [parse_node(s) for s in station_data]
        local_stations: List[LiveStation] = [
            station
            for station in station_list
            if station is not None and isinstance(station, LiveStation)
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
            station.stream = await self.streams.get_live_stream(station.id)
        if include_schedule:
            station.schedule = await self.schedules.get_schedule(station.id, date=date)
        return station

    async def get_station(
        self,
        station_id: str,
        include_stream: bool = False,
        stream_format: Literal["hls"] | Literal["dash"] = "hls",
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
        stations = await self.get_stations()
        # station id is almost always the same as pid but not quite, e.g. bbc_radio_fourfm and bbc_radio_four
        station = next(
            (s for s in stations if s.id == station_id),
            None,
        )

        if station:
            if include_stream:
                stream = await self.streams.get_live_stream(
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
        json_resp = await self._get_json(
            url_template=URLs.BROADCAST, url_args={"pid": pid}
        )
        broadcast = parse_node(json_resp)
        return broadcast
