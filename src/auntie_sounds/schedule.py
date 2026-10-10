import asyncio
import datetime
import logging
import time
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, date, timedelta
from datetime import datetime as dt
from itertools import chain

from auntie_sounds import endpoints
from auntie_sounds.constants import SCHEDULE_TIMEZONE
from auntie_sounds.endpoints import Endpoints
from auntie_sounds.exceptions import (
    APIResponseError,
    DateOutOfRangeError,
    InvalidFormatError,
)
from auntie_sounds.history import SegmentHistory
from auntie_sounds.models import (
    LiveStation,
    MenuItem,
    Polling,
    RadioShow,
    Schedule,
    ScheduleItem,
    Segment,
    Station,
)
from auntie_sounds.parser import Parser
from auntie_sounds.requests import RequestManager, build_url
from auntie_sounds.utils import station_id_to_service_id

logger = logging.getLogger(__name__)

RECENT_TRACKS = "recent_tracks"
LIVE_PLAY_AREA = "live_play_area"
BROADCAST_TYPES = ("broadcast_summary", "broadcast")

# The API serves 30 days back and 7 ahead
CATCH_UP_DAYS = 30
UPCOMING_DAYS = 7

# How many programmes the on-air poll lists: the one on air and the next four
ON_AIR_LIMIT = 5

# The API rejects any other limit on the latest segments, whatever its spec says
SEGMENT_LIMIT_MAX = 10


def _covers(item: ScheduleItem | RadioShow, now: dt) -> bool:
    return (
        item.start is not None and item.end is not None and item.start <= now < item.end
    )


def _schedule_or_catch_up_dates(
    catch_up: bool, start_date: date | None = None
) -> list[date]:
    """The dates the API will return a schedule or catch-up for."""
    start_date = start_date or dt.now(SCHEDULE_TIMEZONE).date()
    if catch_up:
        return [start_date - timedelta(days=n) for n in range(CATCH_UP_DAYS + 1)]
    return [start_date + timedelta(days=n) for n in range(UPCOMING_DAYS + 1)]


def schedule_dates(start_date: date | None = None):
    """The dates the API will return a schedule for, soonest first.

    The API will accept today's date, and then 7 future days, for 8 total."""
    return _schedule_or_catch_up_dates(catch_up=False, start_date=start_date)


def catch_up_dates(start_date: date | None = None):
    """The dates the API will return a catch-up for, most recent first.

    The API will accept today's date, and then 30 previous days, for 31 total.
    """
    return _schedule_or_catch_up_dates(catch_up=True, start_date=start_date)


def unique_broadcasts(
    items: Iterable[ScheduleItem | RadioShow],
) -> list[ScheduleItem | RadioShow]:
    """
    Drop repeats of a broadcast, keeping the first of each and the order.

    A schedule day can run to 25 hours, so the same broadcast can be in two
    days' schedules. Episode pids can't be used, as one is repeated on purpose.

    :param items: Broadcasts from one or more schedules.
    """
    seen: dict[str, ScheduleItem | RadioShow] = {}
    for item in items:
        seen.setdefault(item.id, item)
    return list(seen.values())


class ScheduleService:
    def __init__(
        self,
        requests: RequestManager,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.requests = requests
        # Broadcasts are slots on a station and are typed as such, so unlike
        # ContentService and PersonalService this doesn't look up brand owners
        self.parser = Parser()
        # Used to leave the wait the API asks for between polls
        self._clock = clock
        self._polling: dict[str, dict[str, Polling]] = {}
        self._on_air_items: dict[str, list[ScheduleItem | RadioShow]] = {}
        self._on_air_refresh_at: dict[str, float] = {}
        self._histories: dict[str, SegmentHistory] = {}
        self._segments_poll_at: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock(self, station_id: str) -> asyncio.Lock:
        return self._locks.setdefault(station_id, asyncio.Lock())

    def _parse_broadcasts(self, json_resp: dict) -> list[ScheduleItem | RadioShow]:
        """Get the broadcasts from an experience or poll response."""
        nodes = json_resp.get("data") or []
        # An experience wraps them in the live_play_area module
        play_area = next(
            (n for n in nodes if n.get("id") == LIVE_PLAY_AREA and "data" in n), None
        )
        if play_area is not None:
            nodes = play_area["data"] or []
        broadcasts = [n for n in nodes if n.get("type") in BROADCAST_TYPES]
        parsed = self.parser.parse_node(broadcasts) if broadcasts else None
        return unique_broadcasts(
            item
            for item in (parsed if isinstance(parsed, list) else [])
            if isinstance(item, (ScheduleItem, RadioShow))
        )

    async def _load_experience(self, station_id: str) -> None:
        """Fetch a station's play experience and keep its polling info and on-air list."""
        json_resp = await self.requests.get_json_response(
            url=Endpoints.PLAY_EXPERIENCE,
            url_args={"service_id": station_id_to_service_id(station_id)},
        )
        self._polling[station_id] = {
            module["id"]: Polling.from_dict(module["uris"]["polling"])
            for module in json_resp.get("data") or []
            if (module.get("uris") or {}).get("polling")
        }
        self._on_air_items[station_id] = self._parse_broadcasts(json_resp)
        wait = self._polling[station_id].get(LIVE_PLAY_AREA)
        self._on_air_refresh_at[station_id] = self._clock() + (
            wait.wait_before_poll_sec if wait else 0
        )

    async def polling(self, station_id: str) -> dict[str, Polling]:
        """
        Get how each of a station's experience modules asks to be refreshed.

        :param station_id: The station, e.g. bbc_6music.
        """
        if station_id not in self._polling:
            await self._load_experience(station_id)
        return self._polling[station_id]

    async def _refresh_on_air(self, station_id: str, needed: bool) -> None:
        """Poll for the on-air list, early if `needed` because it lists nothing current."""
        polling = (await self.polling(station_id)).get(LIVE_PLAY_AREA)
        if polling is None:
            return
        if not needed and self._clock() < self._on_air_refresh_at[station_id]:
            return
        json_resp = await self.requests.get_json_response(
            url=build_url(polling.render(offset=0, limit=ON_AIR_LIMIT))
        )
        if items := self._parse_broadcasts(json_resp):
            self._on_air_items[station_id] = items
            self._on_air_refresh_at[station_id] = (
                self._clock() + polling.wait_before_poll_sec
            )
        else:
            logger.debug(
                "No broadcasts in the poll for %s, using the experience", station_id
            )
            await self._load_experience(station_id)

    async def on_air(
        self, station_id: str, now: dt | None = None
    ) -> ScheduleItem | None:
        """
        Get the programme that is currently on air for a station.

        This is the first programme of the station's on-air poll. The poll also
        lists the next few, so it is only fetched again once the API's wait has
        passed or nothing it listed covers the time.

        :param station_id: The station, e.g. bbc_6music.
        :param now: The time to find the programme for, in UTC. Defaults to now.
        """
        at: dt = now or dt.now(UTC)

        def covering() -> ScheduleItem | None:
            return next(
                (
                    item
                    for item in self._on_air_items.get(station_id, ())
                    if isinstance(item, ScheduleItem) and _covers(item, at)
                ),
                None,
            )

        async with self._lock(station_id):
            # The first load already lists the on-air programme, so poll after it
            await self.polling(station_id)
            found = covering()
            await self._refresh_on_air(station_id, needed=found is None)
            found = covering()
        return found or await self._on_air_from_schedule(station_id, at)

    async def _on_air_from_schedule(
        self, station_id: str, now: dt
    ) -> ScheduleItem | None:
        """Find the programme on air in today's schedule, for stations without a poll."""
        schedule = await self.get_schedule(station_id)
        if not schedule or not schedule.sub_items:
            return None
        on_air_show = next(
            (s for s in unique_broadcasts(schedule.sub_items) if _covers(s, now)),
            None,
        )
        return on_air_show if isinstance(on_air_show, ScheduleItem) else None

    def history(self, station_id: str) -> SegmentHistory:
        """Get the tracks seen so far on a station, without any request."""
        return self._histories.setdefault(station_id, SegmentHistory())

    async def refresh_history(
        self, station_id: str, now: dt | None = None
    ) -> SegmentHistory:
        """
        Merge the station's latest tracks into its history, if the API's wait has passed.

        Stations whose experience has no recent tracks polling just keep an
        empty history. Calling this more often than the wait does no harm.

        :param station_id: The station, e.g. bbc_6music.
        :param now: The time of the poll, in UTC. Defaults to now.
        """
        history = self.history(station_id)
        polling = (await self.polling(station_id)).get(RECENT_TRACKS)
        if polling is None:
            return history
        async with self._lock(f"{station_id}/segments"):
            if self._clock() < self._segments_poll_at.get(station_id, 0):
                return history
            # Set first so a failed request isn't retried at once
            self._segments_poll_at[station_id] = (
                self._clock() + polling.wait_before_poll_sec
            )
            programme = await self.on_air(station_id, now)
            if programme is None or programme.start is None:
                return history
            json_resp = await self.requests.get_json_response(
                url=build_url(polling.render(offset=0, limit=SEGMENT_LIMIT_MAX))
            )
            parsed = self.parser.parse_container(json_resp)
            segments = (
                [s for s in parsed or [] if isinstance(s, Segment)]
                if isinstance(parsed, list)
                else []
            )
            history.merge(segments, programme.start, now)
        return history

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
                # Try to parse the date string as a valid date format
                dt.strptime(date, "%Y-%m-%d")  # ruff: ignore[DTZ007]
            except ValueError:
                raise InvalidFormatError(
                    "Invalid date specified, must be in the format YYYY-MM-DD"
                )
        try:
            json_resp = await self.requests.get_json_response(
                url=url, url_args=url_args
            )
        except APIResponseError as e:
            # e.g. "Acceptable date must be between 30 days in the past and 7 days in the future"
            if date and "acceptable date" in (e.message or "").lower():
                raise DateOutOfRangeError(
                    f"{e.message}. Date requested: {date}.", status_code=e.status_code
                ) from e
            raise
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
        """
        date_range = schedule_dates(start_date=dt.now(tz=SCHEDULE_TIMEZONE))
        schedules = await asyncio.gather(
            *(
                self.get_schedule(
                    station_id,
                    date=the_date.strftime("%Y-%m-%d"),
                )
                for the_date in date_range
            )
        )
        return [schedule for schedule in schedules if isinstance(schedule, Schedule)]

    async def get_stations_schedules(
        self, station_ids: list[str], start_date: datetime.date, end_date: datetime.date
    ) -> list[Schedule]:
        """Get the schedules for multiple stations for a date range."""
        per_station = await asyncio.gather(
            *(
                self.get_station_schedules(id, start_date=start_date, end_date=end_date)
                for id in station_ids
            )
        )
        return list(chain.from_iterable(per_station))

    async def current_programme(self, station_id: str) -> LiveStation | None:
        station_id = station_id_to_service_id(station_id)
        json_resp = await self.requests.get_json_response(
            url=endpoints.Endpoints.STATIONS
        )
        try:
            stations_data = json_resp["data"][0]["data"]
        except (TypeError, KeyError) as e:
            raise APIResponseError(
                "Station listing data not in expected format."
            ) from e

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
            url_args={"service_id": station_id_to_service_id(station_id)},
            params={"limit": min(max(results, 1), SEGMENT_LIMIT_MAX)},
        )
        segments = self.parser.parse_container(json_resp)
        if isinstance(segments, list):
            return [segment for segment in segments if isinstance(segment, Segment)]
        return []

    async def currently_playing_song(self, station_id) -> Segment | None:
        """Gets the currently playing song, if one is playing."""
        recently_played = await self.recently_played_items(station_id)
        if (
            recently_played
            and (offset := recently_played[0].offset)
            and offset.now_playing
        ):
            return recently_played[0]
        return None


def station_folders(
    id: str, title: str, stations: Sequence[LiveStation | Station]
) -> MenuItem:
    """A folder with one entry per station, e.g. for the schedule or catch-up menus."""
    return MenuItem(
        id=id,
        title=title,
        sub_items=[
            MenuItem(
                id=station.item_id,
                title=station.network.short_title,
                image_url=station.network.logo_url,
            )
            for station in stations
            if station.network
        ],
    )
