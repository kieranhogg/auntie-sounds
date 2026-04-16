from datetime import datetime as dt
from typing import Optional, cast

from . import constants
from .base import Base
from .constants import URLs
from .exceptions import InvalidFormatError
from .models import LiveProgramme, Schedule, Segment
from .parser import parse_container, parse_node, parse_schedule


class ScheduleService(Base):
    async def get_schedule(
        self, station_id: str, date: str | None = None
    ) -> Schedule | None:
        url_template = URLs.SCHEDULE
        if date:
            url_template = URLs.SCHEDULE_DATE
            try:
                _ = dt.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise InvalidFormatError(
                    "Invalid date specified, must be in the format YYYY-MM-DD"
                )
        json_resp = await self._get_json(
            url_template=url_template, url_args={"station_id": station_id, "date": date}
        )
        schedule = parse_schedule(json_resp)
        return schedule if isinstance(schedule, Schedule) else None

    async def current_programme(self, station_id: str) -> Optional[LiveProgramme]:
        json_resp = await self._get_json(url_template=constants.URLs.STATIONS)
        listing = next(
            (
                station
                for station in json_resp["data"][0]["data"]
                if station.get("id") == station_id
            ),
            None,
        )
        if listing:
            listing = cast(LiveProgramme, parse_node(listing))
        return listing

    async def recently_played_items(
        self, station_id: str, image_size=450, results=10
    ) -> list[Segment]:
        """Gets the recent playing items on this station"""
        json_resp = await self._get_json(
            url_template=URLs.NOW_PLAYING,
            url_args={"station_id": station_id, "limit": results},
        )
        segments = parse_container(json_resp)
        if isinstance(segments, list):
            return [segment for segment in segments if isinstance(segment, Segment)]
        return []

    async def currently_playing_song(
        self, station_id, image_size=450
    ) -> Segment | None:
        """Gets the currently playing song, if one is playing."""
        recently_played = await self.recently_played_items(station_id, image_size)
        try:
            if recently_played[0].offset["now_playing"]:
                return recently_played[0]
        except IndexError:
            pass
        return None
