import logging
from . import constants
from .base import Base
from .constants import URLs
from .models import Station
from .utils import network_logo

logger = logging.getLogger(__name__)


class StationsService(Base):

    async def get_stations(self) -> list[Station]:
        """
        Gets the list of all stations

        :return: A list of Station objects
        :rtype: list[Station]
        """
        json_resp = await self._get_json(URLs.STATIONS_URL)
        logger.log(constants.VERBOSE_LOG_LEVEL, "Getting station list...")
        logger.log(constants.VERBOSE_LOG_LEVEL, json_resp)
        return [
            Station(
                id=s["id"],
                name=s["network"]["short_title"],
                description=f"{s['titles']['secondary']} • {s['titles']['primary']}: {s['synopses']['short']}",
                logo_url=network_logo(s["network"]["logo_url"]),
            )
            for s in json_resp["data"][0]["data"]
        ]
