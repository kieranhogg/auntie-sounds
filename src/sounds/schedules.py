from datetime import datetime as dt

from . import constants
from .base import Base
from .constants import URLs
from .exceptions import InvalidFormatException
from .models import ScheduleItem, Segment, Station
from .utils import image_from_recipe


class ScheduleService(Base):

    async def get_schedule(
        self, station_id: str, date: str | None = None, image_size=320
    ) -> list[ScheduleItem]:
        url = URLs.SCHEDULE_URL.format(station_id=station_id)
        if date:
            try:
                _ = dt.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise InvalidFormatException(
                    "Invalid date specified, must be in the format YYYY-MM-DD"
                )
            url = f"{url}/{date}"
        json_resp = await self._get_json(url)
        schedule = json_resp["data"][0]["data"]
        self.logger.log(constants.VERBOSE_LOG_LEVEL, "Getting schedule for list...")
        self.logger.log(constants.VERBOSE_LOG_LEVEL, json_resp)
        return [
            ScheduleItem(
                id=item["id"],
                urn=item["urn"],
                start=item["start"],
                end=item["end"],
                duration=item["duration"],
                short_synopsis=item["synopses"]["short"],
                medium_synopsis=item["synopses"]["medium"],
                long_synopsis=item["synopses"]["long"],
                image_url=image_from_recipe(
                    image_recipe=item["image_url"], size=image_size
                ),
                primary_title=item["titles"]["primary"],
                secondary_title=item["titles"]["secondary"],
                tertiary_title=item["titles"]["tertiary"],
            )
            for item in schedule
        ]

    async def now_playing(
        self, station: Station, logo_size=450, results=10
    ) -> list[Segment]:
        """Gets the recent playing segements on this station"""
        url = URLs.NOW_PLAYING_URL.format(station_id=station.id, limit=results)
        json = await self._get_json(url)

        return [
            Segment(
                id=segment["id"],
                primary_title=segment["titles"]["primary"],
                secondary_title=segment["titles"]["secondary"],
                tertiary_title=segment["titles"]["tertiary"],
                entity_title=segment["titles"]["entity_title"],
                image_url=image_from_recipe(
                    segment["image_url"], f"{logo_size}x{logo_size}"
                ),
                start_seconds=segment["offset"]["start"],
                end_seconds=segment["offset"]["start"],
                label=segment["offset"]["label"],
                now_playing=segment["offset"]["now_playing"],
            )
            for segment in json["data"]
        ]

    async def song_playing(self, station_id) -> list[Segment] | list[None]:
        """Gets the currently playing song, if one is playing."""
        return list(filter(lambda x: x.now_playing, await self.now_playing(station_id)))
