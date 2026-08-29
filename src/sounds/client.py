import logging
from datetime import tzinfo
from http.cookiejar import CookieJar as HttpCookieJar
from pathlib import Path

import aiohttp
import pytz
from colorlog import ColoredFormatter

from sounds import constants
from sounds.auth import AuthService
from sounds.cookies import CookieStore
from sounds.exceptions import InvalidArgumentsError
from sounds.models import Menu, MenuItem, Segment, Station, Stream
from sounds.personal import MenuRecommendationOptions, PersonalService
from sounds.requests import RequestManager
from sounds.schedule import ScheduleService
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
        cookie_file_location: str | Path = COOKIE_FILE,
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
        self.login_details_provided = bool(self.username and self.password)
        self.current_station: Station | None = None
        self.current_stream: Stream | None = None
        self.current_segment: Segment | None = None
        self.timeout = aiohttp.ClientTimeout(total=10)
        self.mock_session = mock_session
        if timezone:
            self.timezone = timezone
        else:
            self.logger.warning(
                "No timezone provided, assuming UTC so any time calculations for the schedules may be incorrect"
            )
            self.timezone = pytz.timezone("UTC")

        if session:
            self.logger.debug("Reusing provided aiohttp session.")
            self._session = session
        else:
            self.logger.debug("No provided aiohttp session, creating a new one.")
            self._session = aiohttp.ClientSession()
        self.managing_session = session is None

        if not isinstance(self._session.cookie_jar, (HttpCookieJar, aiohttp.CookieJar)):
            raise TypeError(
                "SoundsClient requires aiohttp.CookieJar for cookie persistence"
            )

        service_kwargs = {
            "session": self._session,
            "timeout": self.timeout,
            "logger": self.logger,
            "timezone": self.timezone,
            "mock_session": self.mock_session,
            **kwargs,
        }
        self.cookie_store = CookieStore(
            **service_kwargs, cookie_file_location=cookie_file_location
        )

        self.cookie_store.load()
        if self.cookie_store.has_session_cookie and not self.login_details_provided:
            # Handle the edge case of a session going from logged in to anonymous
            self.logger.info(
                "Login credentials not provided, so clearing persisted session."
            )
            self.cookie_store.clear()
            self.cookie_store.save()

        self.auth = AuthService(
            cookie_store=self.cookie_store,
            on_login_success=self.save_cookies,
            **service_kwargs,
        )
        self.schedules = ScheduleService(
            cookie_store=self.cookie_store, **service_kwargs
        )
        self.user = UserService(
            cookie_store=self.cookie_store,
            login_details_provided=self.login_details_provided,
            **service_kwargs,
        )

        self.requests = RequestManager(
            auth=self.auth,
            cookie_store=self.cookie_store,
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
            log_level = logging.WARNING
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
            self.logger.info("Existing session cookie found, reusing")
            ok = await self.auth.renew_session()
            return ok

        ok = await self.auth.login(self.username, self.password)

        if ok:
            self.cookie_store.save()
            await self.user.refresh()

        return ok

    def save_cookies(self):
        self.cookie_store.save()

    def load_cookies(self):
        self.cookie_store.load()

    @property
    def has_session_cookie(self) -> bool:
        """Check if we have a cookie present."""
        return self.cookie_store.has_session_cookie

    async def get_menu(
        self,
        include_local_stations: bool = False,
        recommendations: MenuRecommendationOptions = MenuRecommendationOptions.INCLUDE,
    ) -> Menu:
        """Get the main Sounds menu."""
        menu = Menu(sub_items=[])
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
            if recommendations != MenuRecommendationOptions.ONLY:
                menu.sub_items.pop(0)
                menu.sub_items.insert(0, listen_live)
                menu.sub_items.insert(1, schedule)
                menu.sub_items.insert(len(menu.sub_items), explore_all)
        elif recommendations != MenuRecommendationOptions.ONLY:
            # Treat i18n and UK logged out the same
            menu = Menu(sub_items=[listen_live, schedule, explore_all])
        return menu

    async def logout(self):
        self.logger.debug("Logging out...")
        self.cookie_store.clear()
        self.cookie_store.save()
        self.logger.debug("Logged out.")

    async def close(self):
        self.logger.debug("Session close explicitly requested.")
        if self._session and self.managing_session:
            await self._session.close()
        self.cookie_store.save()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        if self.managing_session:
            self.logger.debug("Closed session")
            await self.close()
        self.cookie_store.save()
