import logging

from src.sounds.base import Base
from src.sounds.constants import URLs
from src.sounds.models import Segment
from src.sounds.utils import image_from_recipe

logger = logging.getLogger(__name__)


class SegmentsService(Base):

    async def now_playing(
        self, station_id: str, logo_size=450, results=10
    ) -> list[Segment]:
        """Gets the recent playing segements on this station"""
        url = URLs.NOW_PLAYING_URL.format(station_id=station_id, limit=results)
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
