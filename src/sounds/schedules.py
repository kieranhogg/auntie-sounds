from datetime import datetime as dt

from . import constants
from .base import Base
from .constants import URLs
from .exceptions import InvalidFormatError
from .json import parse_menu
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
                raise InvalidFormatError(
                    "Invalid date specified, must be in the format YYYY-MM-DD"
                )
            url = f"{url}/{date}"
        json_resp = await self._get_json(url)
        schedule = json_resp["data"][0]["data"]
        print(parse_menu(json_resp))
        exit(0)
        self.logger.log(constants.VERBOSE_LOG_LEVEL, "Getting schedule for list...")
        self.logger.log(constants.VERBOSE_LOG_LEVEL, json_resp)
        return [
            ScheduleItem(
                id=item["id"],
                urn=item["urn"],
                start=dt.fromisoformat(item["start"]),
                end=dt.fromisoformat(item["end"]),
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
                episode_id=(
                    item["playable_item"]["id"] if item["playable_item"] else None
                ),
            )
            for item in schedule
        ]

    async def recently_played_items(
        self, station: Station, image_size=450, results=10
    ) -> list[Segment]:
        """Gets the recent playing items on this station"""
        url = URLs.NOW_PLAYING_URL.format(station_id=station.id, limit=results)
        json = await self._get_json(url)

        return [
            Segment(
                id=segment["id"],
                primary_title=segment["titles"]["primary"],
                secondary_title=segment["titles"]["secondary"],
                tertiary_title=segment["titles"]["tertiary"],
                entity_title=segment["titles"]["entity_title"],
                image_url=image_from_recipe(segment["image_url"], image_size),
                start_seconds=segment["offset"]["start"],
                end_seconds=segment["offset"]["start"],
                label=segment["offset"]["label"],
                now_playing=segment["offset"]["now_playing"],
            )
            for segment in json["data"]
        ]

    async def currently_playing_song(
        self, station_id, image_size=450
    ) -> Segment | None:
        """Gets the currently playing song, if one is playing."""
        recently_played = await self.recently_played_items(station_id, image_size)
        try:
            if recently_played[0].now_playing:
                return recently_played[0]
        except KeyError:
            pass
        return None
