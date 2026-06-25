import logging
import os
from datetime import tzinfo
from pathlib import Path

import aiohttp
import pytz
from colorlog import ColoredFormatter

from sounds import constants
from sounds.auth import AuthService
from sounds.exceptions import InvalidArgumentsError
from sounds.models import Menu, MenuItem, Segment, Station, Stream
from sounds.personal import MenuRecommendationOptions, PersonalService
from sounds.requests import RequestManager
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
        self.state = Session(
            cookie_file=cookie_file, logger=self.logger, mock_session=mock_session
        )
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

        self.auth = AuthService(
            state=self.state, on_login_success=self.save_cookies, **service_kwargs
        )
        self.schedules = ScheduleService(state=self.state, **service_kwargs)
        self.user = UserService(
            state=self.state,
            login_details_provided=(
                self.username is not None and self.password is not None
            ),
            **service_kwargs,
        )

        self.requests = RequestManager(
            auth=self.auth,
            state=self.state,
            logger=self.logger,
            username=self.username,
            password=self.password,
        )
        self.streaming = StreamingService(
            auth=self.auth,
            requests=self.requests,
            schedules=self.schedules,
            user=self.user,
            **service_kwargs,
        )
        self.stations = StationService(
            streaming=self.streaming,
            schedules=self.schedules,
            **service_kwargs,
        )
        self.personal = PersonalService(
            auth=self.auth, requests=self.requests, **service_kwargs
        )

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

    async def login(self) -> bool:
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

        if self.has_session_cookie:
            self.logger.info("Existing session found, reusing")
            ok = await self.auth.renew_session()
            return ok

        ok = await self.auth.login(self.username, self.password)

        if ok:
            self.state.save()
            await self.user.refresh()

        return ok

    def save_cookies(self):
        self.state.save()

    def load_cookies(self):
        self.state.load()

    @property
    def has_session_cookie(self) -> bool:
        """Check if we have a cookie present."""
        return self.state.has_session_cookie

    async def get_menu(
        self,
        include_local_stations: bool = False,
        recommendations: MenuRecommendationOptions = MenuRecommendationOptions.INCLUDE,
    ):
        """Get the main Sounds menu."""
        explore_all = await self.personal.get_explore_all()
        stations = await self.stations.get_stations(
            include_local=include_local_stations
        )
        listen_live = MenuItem(
            title="Listen Live", id="listen_live", sub_items=stations
        )
        schedule = await self.stations.get_station_schedule_menu()
        if await self.user.is_uk_listener() and self.username and self.password:
            # UK listener, logged in, get menu from Sounds API
            menu = await self.personal.get_uk_menu(recommendations=recommendations)
            menu.sub_items.pop(0)
            menu.sub_items.insert(0, listen_live)
            menu.sub_items.insert(1, schedule)
            menu.sub_items.insert(len(menu.sub_items), explore_all)
        elif await self.user.is_uk_listener():
            # UK listener, not logged in, construct UK menu
            menu = Menu(sub_items=[listen_live, schedule, explore_all])
        else:
            # Construct internaional menu
            menu = Menu(sub_items=[listen_live, explore_all])
        return menu

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
