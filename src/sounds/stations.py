import itertools
from . import constants
from .base import Base
from .constants import URLs
from .models import Station
from .utils import network_logo


class StationsService(Base):

    async def get_stations(self, include_local=False) -> list[Station]:
        """
        Gets the list of all stations

        :return: A list of Station objects
        :rtype: list[Station]
        """
        json_resp = await self._get_json(URLs.STATIONS_URL)
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
        return [
            Station(
                id=s["id"],
                name=s["network"]["short_title"],
                description=f"{s['titles']['secondary']} • {s['titles']['primary']}: {s['synopses']['short']}",
                logo_url=network_logo(s["network"]["logo_url"]),
                local=s["local"],
            )
            for s in stations
        ]

    async def get_station(self, station_id: str) -> Station | None:
        """
        Gets a station's details

        :return: A Station object
        :rtype: Station
        """
        # TODO: include listings here?
        stations = await self.get_stations(include_local=True)
        try:
            return [station for station in stations if station.id == station_id][0]
        except KeyError:
            return None
