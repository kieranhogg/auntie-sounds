import logging
from datetime import datetime as dt
from datetime import tzinfo

import aiohttp

from sounds import endpoints
from sounds.endpoints import URLs
from sounds.exceptions import APIResponseError, InvalidFormatError
from sounds.models import LiveProgramme, Schedule, Segment
from sounds.parser import Parser
from sounds.requests import RequestManager

logger = logging.getLogger(__name__)


class ScheduleService:
    def __init__(self, requests: RequestManager, timezone: tzinfo):
        self.requests = requests
        self.timezone = timezone
        self.parser = Parser()

    async def get_schedule(
        self, station_id: str, date: str | None = None
    ) -> Schedule | None:
        url_template = URLs.SCHEDULE
        if date:
            url_template = URLs.SCHEDULE_DATE
            try:
                _ = dt.strptime(date, "%Y-%m-%d").replace(tzinfo=self.timezone)
            except ValueError:
                raise InvalidFormatError(
                    "Invalid date specified, must be in the format YYYY-MM-DD"
                )
        json_resp = await self.requests.get_json_response(
            url=url_template, url_args={"station_id": station_id, "date": date}
        )
        schedule = self.parser.parse_schedule(json_resp)
        return schedule if isinstance(schedule, Schedule) else None

    async def current_programme(self, station_id: str) -> LiveProgramme | None:
        json_resp = await self.requests.get_json_response(url=endpoints.URLs.STATIONS)
        try:
            stations_data = json_resp["data"][0]["data"]
        except IndexError, KeyError:
            raise APIResponseError("Station listing data not in expected format.")

        listing = next(
            (
                self.parser.parse_node(station)
                for station in stations_data
                if station.get("id") == station_id
            ),
            None,
        )
        return listing if type(listing) is LiveProgramme else None

    async def recently_played_items(self, station_id: str, results=10) -> list[Segment]:
        """Gets the recent playing items on this station"""
        json_resp = await self.requests.get_json_response(
            url=URLs.NOW_PLAYING,
            url_args={"station_id": station_id, "limit": results},
        )
        segments = self.parser.parse_container(json_resp)
        if isinstance(segments, list):
            return [segment for segment in segments if isinstance(segment, Segment)]
        return []

    async def currently_playing_song(self, station_id) -> Segment | None:
        """Gets the currently playing song, if one is playing."""
        recently_played = await self.recently_played_items(station_id)
        if recently_played:
            try:
                if recently_played[0].offset["now_playing"]:
                    return recently_played[0]
            except IndexError, KeyError:
                pass
        return None
