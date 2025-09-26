import itertools
from typing import List, Optional

from .json import parse_container, parse_node

from . import constants
from .base import Base
from .constants import URLs
from .models import Network, Station
from .schedules import ScheduleService
from .streaming import StreamingService
from .utils import network_logo


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
        return stations

    async def get_stations(
        self,
        include_local: bool = False,
        include_streams: bool = False,
        include_schedules: bool = False,
    ) -> list[Station]:
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
        stations = [
            Station(
                id=s["id"],
                title=s["network"]["short_title"],
                description=f"{s['titles']['secondary']} • {s['titles']['primary']}: {s['synopses']['short']}",
                image_url=network_logo(s["network"]["logo_url"]),
                local=s["local"],
            )
            for s in stations
        ]
        if include_streams:
            for station in stations:
                station.stream = await self.streams.get_live_stream(station)

        if include_schedules:
            for station in stations:
                station.schedule = await self.schedules.get_schedule(station.id)

        return stations

    async def get_local_stations(self):
        json_resp = await self._get_json(url_template=URLs.STATIONS)
        self.logger.log(constants.VERBOSE_LOG_LEVEL, "Getting local station list...")
        self.logger.log(constants.VERBOSE_LOG_LEVEL, json_resp)
        local_stations = json_resp["data"][1]["data"]
        stations = [parse_node(s) for s in local_stations]
        return stations

    async def get_station_schedule(
        self,
        station_id: str,
        include_stream: bool = False,
        include_schedule: bool = False,
        date: str | None = None,
    ) -> Station | None:
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
            station.stream = await self.streams.get_live_stream(station)
        if include_schedule:
            station.schedule = await self.schedules.get_schedule(station.id, date=date)
        return station

    async def get_station(
        self,
        station_id: str,
        include_stream: bool = False,
        include_schedule: bool = False,
        date: str | None = None,
    ) -> Station | None:
        if date:
            return await self.get_station_schedule(
                station_id, include_stream, include_schedule, date
            )
        station = next(
            (
                station
                for station in await self.get_stations()
                if station.id == station_id
            ),
            None,
        )
        if station and include_stream:
            station.stream = await self.streams.get_live_stream(station_id)
        return station

    async def get_broadcast(self, pid: str):
        json_resp = await self._get_json(
            url_template=URLs.BROADCAST, url_args={"pid": pid}
        )
        broadcast = parse_node(json_resp)
        return broadcast
