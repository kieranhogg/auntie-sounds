import logging
from collections.abc import Callable
from colorlog import ColoredFormatter


import aiohttp

import constants
from .auth import AuthService
from .segments import SegmentsService
from .stations import StationsService
from .streaming import StreamingService
from .models import Segment, Station, Stream

logger = logging.getLogger(__name__)


class SoundsClient:
    """A client to interact with the Sounds API"""

    def __init__(
        self,
        session: aiohttp.ClientSession | None = None,
        update_handler: Callable | None = None,
        log_level: str | None = None,
    ) -> None:
        self.setLogger(log_level)
        logger.log(constants.VERBOSE_LOG_LEVEL, "SoundsClient.__init__()")
        self._update_handler = update_handler
        self.current_station: Station | None = None
        self.current_stream: Stream | None = None
        self.current_segment: Segment | None = None
        self.timeout = aiohttp.ClientTimeout(total=10)

        if not session:
            self._session = aiohttp.ClientSession()
            self.managing_session = True
        else:
            self._session = session
            self.managing_session = False

        service_kwargs = {
            "session": self._session,
            "timeout": self.timeout,
        }

        self.auth = AuthService(**service_kwargs)
        self.stations = StationsService(**service_kwargs)
        self.streaming = StreamingService(**service_kwargs)
        self.segments = SegmentsService(**service_kwargs)

    def setLogger(self, log_level=None):
        logging.addLevelName(constants.VERBOSE_LOG_LEVEL, "VERBOSE")
        logging.basicConfig(
            level=constants.VERBOSE_LOG_LEVEL,
            format="%(asctime)s -%(levelname)s -on line: %(lineno)d -%(message)s",
        )
        log_fmt = "%(asctime)s.%(msecs)03d %(levelname)s (%(threadName)s) [%(name)s] %(message)s"
        colorfmt = f"%(log_color)s{log_fmt}%(reset)s"
        logging.getLogger().handlers[0].setFormatter(
            ColoredFormatter(
                colorfmt,
                reset=True,
                log_colors={
                    "VERBOSE": "light_black",
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "red",
                },
            )
        )
        if log_level:
            logger.setLevel(log_level)
        else:
            logger.setLevel(constants.VERBOSE_LOG_LEVEL)

    async def close(self):
        if self._session and self.managing_session:
            await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        if self._session:
            logger.debug("Closed session")
        await self.close()
