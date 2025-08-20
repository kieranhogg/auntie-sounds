from http import cookiejar
import logging

import aiohttp
import pytz
from colorlog import ColoredFormatter

from . import constants
from .auth import AuthService
from .models import Segment, Station, Stream
from .personal import PersonalService
from .schedules import ScheduleService
from .stations import StationService
from .streaming import StreamingService


class SoundsClient:
    """A client to interact with the Sounds API"""

    def __init__(
        self,
        session: aiohttp.ClientSession | None = None,
        timezone: pytz.BaseTzInfo | None = None,
        logger: logging.Logger | None = None,
        log_level: str | None = None,
        mock_session: bool = False,
        **kwargs,
    ) -> None:
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger()
            self.setLogger(log_level)
            self.logger.log(constants.VERBOSE_LOG_LEVEL, "SoundsClient.__init__()")
        if timezone:
            self.timezone = timezone
        else:
            self.logger.warning(
                "No timezone provided, assuming UTC so any time calculations for the schedules may be incorrect"
            )
            self.timezone = pytz.timezone("UTC")
        self.current_station: Station | None = None
        self.current_stream: Stream | None = None
        self.current_segment: Segment | None = None
        self.timeout = aiohttp.ClientTimeout(total=10)
        self.mock_session = mock_session
        self._cookie_jar = aiohttp.CookieJar(unsafe=True)
        # self.cookie_jar = cookiejar.FileCookieJar("cookies.txt")
        if not session:
            self._session = aiohttp.ClientSession(cookie_jar=self._cookie_jar)
            self.managing_session = True
        else:
            self._session = session
            self._session._cookie_jar = self._cookie_jar
            self.managing_session = False

        service_kwargs = {
            "session": self._session,
            "timeout": self.timeout,
            "logger": self.logger,
            "mock_session": self.mock_session,
            **kwargs,
        }

        self.auth = AuthService(**service_kwargs)
        self.streaming = StreamingService(auth_service=self.auth, **service_kwargs)
        self.schedules = ScheduleService(**service_kwargs)
        self.stations = StationService(
            streaming_service=self.streaming,
            schedule_service=self.schedules,
            **service_kwargs,
        )
        self.personal = PersonalService(auth_service=self.auth, **service_kwargs)

    def setLogger(self, log_level=None):
        logging.addLevelName(constants.VERBOSE_LOG_LEVEL, "VERBOSE")
        if not log_level:
            log_level = logging.WARN
        logging.basicConfig(
            level=log_level,
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
            self.logger.setLevel(log_level)
        else:
            self.logger.setLevel(constants.VERBOSE_LOG_LEVEL)

    async def close(self):
        if self._session and self.managing_session:
            await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        if self.managing_session:
            self.logger.debug("Closed session")
            await self.close()
        self.auth.save_cookies_to_disk()
