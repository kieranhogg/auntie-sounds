from . import constants
from .base import Base
from .constants import URLs
from .models import Station
from .utils import network_logo


class StationsService(Base):

    async def get_stations(self) -> list[Station]:
        """
        Gets the list of all stations

        :return: A list of Station objects
        :rtype: list[Station]
        """
        json_resp = await self._get_json(URLs.STATIONS_URL)
        self.logger.log(constants.VERBOSE_LOG_LEVEL, "Getting station list...")
        self.logger.log(constants.VERBOSE_LOG_LEVEL, json_resp)
        return [
            Station(
                id=s["id"],
                name=s["network"]["short_title"],
                description=f"{s['titles']['secondary']} • {s['titles']['primary']}: {s['synopses']['short']}",
                logo_url=network_logo(s["network"]["logo_url"]),
            )
            for s in json_resp["data"][0]["data"]
        ]

    async def get_station(self, station_id: str) -> Station:
        """
        Gets a station's details

        :return: A Station object
        :rtype: Station
        """
        # TODO: include listings here?
        json_resp = await self._get_json(URLs.STATIONS_URL)
        self.logger.log(constants.VERBOSE_LOG_LEVEL, "Getting station list...")
        self.logger.log(constants.VERBOSE_LOG_LEVEL, json_resp)
        station_data = [
            station for station in json_resp if station["id"] == station_id
        ][0]
        return Station(
            id=station_data["id"],
            name=station_data["network"]["short_title"],
            description=f"{station_data['titles']['secondary']} • {station_data['titles']['primary']}: {station_data['synopses']['short']}",
            logo_url=network_logo(station_data["network"]["logo_url"]),
        )
