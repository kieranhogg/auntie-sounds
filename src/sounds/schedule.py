import asyncio
import datetime
import logging
from datetime import datetime as dt
from datetime import timedelta, tzinfo

from sounds import endpoints
from sounds.endpoints import Endpoints
from sounds.exceptions import APIResponseError, InvalidFormatError
from sounds.models import LiveStation, Schedule, Segment
from sounds.parser import Parser
from sounds.requests import RequestManager
from sounds.stations import StationService

logger = logging.getLogger(__name__)


def _get_date_range(start_date: datetime.date, end_date: datetime.date):
    # Future schedule requested
    if end_date > start_date:
        if (end_date - start_date).days > 7:
            logger.warning(
                "More than 7 days of schedule requested, which is not supported."
            )
            return range(7)
        return range((end_date - start_date).days + 1)
    # Catch-up schedule requested
    if (start_date - end_date).days > 30:
        logger.warning(
            "More than 30 days of catch-up requested, which is not supported."
        )
        return range(0, -30, -1)
    return range(0, -(start_date - end_date).days - 1, -1)


class ScheduleService:
    def __init__(self, requests: RequestManager, timezone: tzinfo):
        self.requests = requests
        self.timezone = timezone
        self.parser = Parser()

    async def get_schedule(
        self, station_id: str, date: str | None = None
    ) -> Schedule | None:
        """Get a Schedule item for a given station_id."""
        url = Endpoints.SCHEDULE
        url_args = {"service_id": station_id}

        if date:
            url = Endpoints.SCHEDULE_DATE
            url_args.update({"date": date})
            try:
                _ = dt.strptime(date, "%Y-%m-%d").replace(tzinfo=self.timezone)
            except ValueError:
                raise InvalidFormatError(
                    "Invalid date specified, must be in the format YYYY-MM-DD"
                )
        json_resp = await self.requests.get_json_response(url=url, url_args=url_args)
        schedule = self.parser.parse_schedule(json_resp)
        return schedule if isinstance(schedule, Schedule) else None

    async def get_schedules(
        self, station_ids: list[str], date: str | None = None
    ) -> list[Schedule]:
        """Get the schedules for multiple stations for a given day."""
        schedules = await asyncio.gather(
            *(self.get_schedule(id, date=date) for id in station_ids)
        )
        return [schedule for schedule in schedules if isinstance(schedule, Schedule)]

    async def get_station_schedules(
        self,
        station_id: str,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> list[Schedule]:
        """Get the schedules for a station for a date range.

        Supports end_date being earlier than start date, i.e. a catch-up range.
        Note: the API"""
        date_range = _get_date_range(start_date, end_date)
        schedules = await asyncio.gather(
            *(
                self.get_schedule(
                    station_id,
                    date=(start_date + timedelta(days=diff)).strftime("%Y-%m-%d"),
                )
                for diff in date_range
            )
        )
        return [schedule for schedule in schedules if isinstance(schedule, Schedule)]

    async def get_stations_schedules(
        self, station_ids: list[str], start_date: datetime.date, end_date: datetime.date
    ) -> list[Schedule]:
        """Get the schedules for multiple stations for a date range."""
        schedules = await asyncio.gather(
            *(
                self.get_station_schedules(id, start_date=start_date, end_date=end_date)
                for id in station_ids
            )
        )
        return [schedule for schedule in schedules if isinstance(schedule, Schedule)]

    async def current_programme(self, station_id: str) -> LiveStation | None:
        json_resp = await self.requests.get_json_response(
            url=endpoints.Endpoints.STATIONS
        )
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
        return listing if type(listing) is LiveStation else None

    async def recently_played_items(self, station_id: str, results=10) -> list[Segment]:
        """Gets the recent playing items on this station"""
        json_resp = await self.requests.get_json_response(
            url=Endpoints.NOW_PLAYING,
            url_args={
                "service_id": StationService.station_id_to_service_id(station_id),
                "limit": results,
            },
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
