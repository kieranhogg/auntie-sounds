import json
import logging
import re
from datetime import datetime as dt
from typing import Optional

from . import constants
from .utils import network_logo
from .base import Base
from .constants import URLs
from .exceptions import APIResponseException
from .models import Station, Stream
from .utils import image_from_recipe


class StreamingService(Base):

    async def get_stream_info(
        self,
        station: Station,
        stream_format="hls",
        logo_size=800,
    ) -> Stream:
        """
        Gets the stream and details of the currently playing show on a given station.

        :param station: A Station object
        :type station_id: str
        :returns: Stream object of stream information
        :rtype: Stream
        """
        url = URLs.LIVE_STATION_URL.format(station_id=station.id)
        html_resp = await self._get_html(url)
        match = re.search(
            r"window\.__PRELOADED_STATE__\s*=\s*(.*?);\s*</script>",
            html_resp,
            re.DOTALL,
        )
        if not match:
            raise APIResponseException("Could not find embedded player JSON")

        json_response = json.loads(match.group(1))
        self.logger.log(constants.VERBOSE_LOG_LEVEL, "Getting stream details...")
        self.logger.log(constants.VERBOSE_LOG_LEVEL, json_response)

        programme_details = json_response["programmes"]["current"]
        jwt_token = await self.get_jwt_token(station.id)

        async with self._session.get(
            URLs.MEDIASET_URL.format(
                station_id=station.id,
                jwt_auth_token=jwt_token,
            )
        ) as resp:
            if resp.status != 200:
                raise RuntimeError("Failed to receive stream")
            data = await resp.json()

            try:
                stream = self.get_best_stream(
                    data["media"][0]["connection"], prefer_type=stream_format
                )
                self.logger.debug(f"Found stream: {stream}")
            except (StopIteration, KeyError):
                raise RuntimeError("No valid stream found")

        self.current_stream = Stream(
            id=programme_details["id"],
            start=dt.fromisoformat(programme_details["start"]),
            end=dt.fromisoformat(programme_details["end"]),
            uri=stream,
            image_url=image_from_recipe(
                programme_details["image_url"], size=f"{logo_size}x{logo_size}"
            ),
            show_title=programme_details["titles"]["primary"],
            show_description=programme_details["titles"]["secondary"],
            station=station,
        )
        return self.current_stream

    def get_best_stream(self, streams: dict, prefer_type="hls") -> Optional[str]:
        """Looks for the first valid stream with the requested format."""
        self.logger.log(constants.VERBOSE_LOG_LEVEL, "Looking for best stream in:")
        self.logger.log(constants.VERBOSE_LOG_LEVEL, streams)

        return next(
            (
                conn["href"]
                for conn in streams
                if conn.get("transferFormat", "") == prefer_type
            ),
            None,
        )
