import logging
import os
from datetime import tzinfo
from pathlib import Path

import aiohttp
import pytz
from colorlog import ColoredFormatter
from yarl import URL

from sounds import constants
from sounds.auth import AuthService
from sounds.exceptions import InvalidArgumentsError
from sounds.models import Segment, Station, Stream
from sounds.personal import PersonalService
from sounds.schedule import ScheduleService
from sounds.session import Session
from sounds.stations import StationService
from sounds.streaming import StreamingService
from sounds.user import UserService
from sounds.utils import _get_data_dir

COOKIE_FILE = Path(_get_data_dir(), "sounds_jar")


class SoundsClient:
    """A client to interact with the Sounds API"""

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        session: aiohttp.ClientSession | None = None,
        cookie_file: str | Path = COOKIE_FILE,
        timezone: tzinfo | None = None,
        logger: logging.Logger | None = None,
        log_level: int | None = None,
        mock_session: bool = False,
        **kwargs,
    ) -> None:
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger()
            self.setLogger(log_level)
            self.logger.log(constants.VERBOSE_LOG_LEVEL, "SoundsClient.__init__()")

        self.logger.debug("Creating new SoundsClient")

        self.username = username
        self.password = password
        self.current_station: Station | None = None
        self.current_stream: Stream | None = None
        self.current_segment: Segment | None = None
        self.timeout = aiohttp.ClientTimeout(total=10)
        self.mock_session = mock_session
        self.state = Session(cookie_file)

        if timezone:
            self.timezone = timezone
        else:
            self.logger.warning(
                "No timezone provided, assuming UTC so any time calculations for the schedules may be incorrect"
            )
            self.timezone = pytz.timezone("UTC")

        if not session:
            self.logger.debug("No provided session, creating a new one.")
            self._session = aiohttp.ClientSession(cookie_jar=self.state.jar)
            self.managing_session = True
        else:
            self.logger.debug("Reusing provided session.")
            self._session = session
            self.managing_session = False
        self.state.load()

        service_kwargs = {
            "session": self._session,
            "timeout": self.timeout,
            "logger": self.logger,
            "mock_session": self.mock_session,
            **kwargs,
        }

        self.auth = AuthService(on_login_success=self.save_cookies, **service_kwargs)
        self.schedules = ScheduleService(**service_kwargs)
        self.user = UserService()

        self.streaming = StreamingService(
            auth=self.auth, schedules=self.schedules, **service_kwargs
        )
        self.stations = StationService(
            streaming=self.streaming,
            schedules=self.schedules,
            **service_kwargs,
        )
        self.personal = PersonalService(auth=self.auth, **service_kwargs)

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

    async def authenticate(self) -> bool:
        """Signs into BBC Sounds.

        :param username: The username or email address to sign in with
        :param password: The password to sign in with
        :return: True if successfully logged in, False otherwise
        :rtype: bool
        :raises LoginFailedError: If the login fails for any reason
        :raises UnauthorisedError: If the login is not authorised
        """
        if self.mock_session:
            return True

        if not self.username or not self.password:
            raise InvalidArgumentsError(
                "Can't authenticate without username and password set"
            )

        if self.state.is_logged_in:
            self.logger.info("Existing session found, reusing")
            ok = await self.auth.renew_session()
            return ok

        ok = await self.auth.login(self.username, self.password)

        if ok:
            self.state.save()

        return ok

    def save_cookies(self):
        self.state.save()

    def load_cookies(self):
        self.state.load()

    @property
    def has_session_cookie(self) -> bool:
        """Check if we have a valid session."""
        self.logger.debug("Checking if we are logged in...")
        if self.mock_session:
            self.logger.debug("mock_session=True")

            return True

        jar = self._session.cookie_jar
        existing_cookie = (
            constants.COOKIE_ID
            in jar.filter_cookies(URL(constants.URLs.COOKIE_BASE.value))
        ) or (
            constants.COOKIE_ID
            in jar.filter_cookies(URL(constants.URLs.COOKIE_BASE_I18N.value))
        )
        if existing_cookie:
            self.logger.debug("Existing cookie found.")
        else:
            self.logger.debug("No cookies found.")
        return existing_cookie

    async def logout(self):
        self.logger.debug("Logging out...")
        try:
            os.remove(COOKIE_FILE)
            self.logger.debug("Cookie file deleted.")
        except FileNotFoundError:
            pass
        self.state.clear()
        self.logger.debug("Logged out.")

    async def close(self):
        if self._session and self.managing_session:
            await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        if self.managing_session:
            self.logger.debug("Closed session")
            await self.close()
        self.state.save()
