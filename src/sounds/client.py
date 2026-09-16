import asyncio.constants
import logging
from collections.abc import Sequence
from datetime import tzinfo
from http.cookiejar import CookieJar as HttpCookieJar
from pathlib import Path

import aiohttp
import pytz
from colorlog import ColoredFormatter

from sounds import VERBOSE_LOG_LEVEL
from sounds.auth import AuthService
from sounds.content import ContentService
from sounds.cookies import CookieStore
from sounds.exceptions import InvalidArgumentsError
from sounds.models import Menu, MenuItem, Segment, Station, Stream
from sounds.personal import PersonalService
from sounds.playback import PlaybackService
from sounds.requests import RequestManager
from sounds.schedule import ScheduleService
from sounds.stations import StationService
from sounds.user import UserService
from sounds.utils import _get_data_dir

COOKIE_FILE = Path(_get_data_dir(), "sounds_jar")

logger = logging.getLogger(__name__)


def setLogger(log_level=None):
    logging.addLevelName(VERBOSE_LOG_LEVEL, "VERBOSE")
    if not log_level:
        log_level = logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s -%(levelname)s -on line: %(lineno)d -%(message)s",
    )
    log_fmt = (
        "%(asctime)s.%(msecs)03d %(levelname)s (%(threadName)s) [%(name)s] %(message)s"
    )
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
        logger.setLevel(VERBOSE_LOG_LEVEL)


class SoundsClient:
    """A client to interact with the Sounds API."""

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        session: aiohttp.ClientSession | None = None,
        cookie_file_location: str | Path = COOKIE_FILE,
        timezone: tzinfo | None = None,
        log_level: int | None = None,
        mock_data: bool = False,
        debug_login: bool = False,
        **kwargs,
    ) -> None:
        setLogger(log_level)

        logger.debug("Creating new SoundsClient")

        self.username = username
        self.password = password

        self.current_station: Station | None = None
        self.current_stream: Stream | None = None
        self.current_segment: Segment | None = None
        self.mock_data = mock_data
        self.debug_login = debug_login
        if timezone:
            self.timezone = timezone
        else:
            logger.warning(
                "No timezone provided, assuming UTC so any time calculations for the schedules may be incorrect"
            )
            self.timezone = pytz.timezone("UTC")

        if session:
            logger.debug("Reusing provided aiohttp session.")
            self._session = session
        else:
            logger.debug("No provided aiohttp session, creating a new one.")
            self._session = aiohttp.ClientSession()
        self.managing_session = session is None
        login_details_provided = bool(self.username and self.password)

        if not isinstance(self._session.cookie_jar, (HttpCookieJar, aiohttp.CookieJar)):
            raise TypeError(
                "SoundsClient requires aiohttp.CookieJar for cookie persistence"
            )

        self.cookie_store = CookieStore(
            session=self._session, cookie_file_location=cookie_file_location
        )

        self.cookie_store.load()
        if self.cookie_store.has_session_cookie and not login_details_provided:
            # Handle the edge case of a session going from logged in to anonymous
            logger.info(
                "Login credentials not provided, so clearing persisted session."
            )
            self.cookie_store.clear()
            self.cookie_store.save()

        self.requests = RequestManager(
            session=self._session,
            mock_data=self.mock_data,
            login_details_provided=login_details_provided,
        )
        self.auth = AuthService(
            requests=self.requests,
            cookie_store=self.cookie_store,
            username=self.username,
            password=self.password,
            mock_data=self.mock_data,
            debug_login=self.debug_login,
            on_login_success=self.save_cookies,
        )
        self.requests.set_reauth_handler(self.auth.retry_with_reauth)
        self.schedules = ScheduleService(
            requests=self.requests,
            timezone=self.timezone,
        )
        self.user = UserService(
            cookie_store=self.cookie_store,
            login_details_provided=login_details_provided,
            requests=self.requests,
        )

        self.schedules = ScheduleService(requests=self.requests, timezone=self.timezone)
        self.playback = PlaybackService(
            requests=self.requests,
        )
        self.content = ContentService(
            requests=self.requests,
            user=self.user,
            playback=self.playback,
        )
        self.stations = StationService(
            playback=self.playback,
            schedules=self.schedules,
            requests=self.requests,
        )
        self.personal = PersonalService(auth=self.auth, requests=self.requests)

    async def login(self) -> bool:
        """Signs into BBC Sounds.

        :return: True if successfully logged in, False otherwise
        :raises LoginFailedError: If the login fails for any reason
        :raises UnauthorisedError: If the login is not authorised
        :raises InvalidArgumentsError: If either a username or password isn't set
        """

        if self.mock_data:
            return True

        if not self.username or not self.password:
            raise InvalidArgumentsError(
                "Can't authenticate without username and password set"
            )

        if self.has_session_cookie:
            logger.info("Existing session cookie found, reusing")
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

    def clear_cookies(self):
        self.cookie_store.clear()
        self.cookie_store.save()

    @property
    def has_session_cookie(self) -> bool:
        """Check if we have a cookie present."""
        return self.cookie_store.has_session_cookie

    async def get_recommendation_folders(self) -> Sequence[MenuItem]:
        return await self.personal.get_recommendations()

    async def get_menu(
        self,
        include_local_stations: bool = False,
        include_recommendations: bool = True,
    ) -> Menu:
        """Get the main Sounds menu."""
        listen_live, schedule, catch_up = await asyncio.gather(
            self.stations.get_listen_live_menu(include_local=include_local_stations),
            self.stations.get_schedule_menu(include_local=include_local_stations),
            self.stations.get_catch_up_menu(include_local=include_local_stations),
        )
        if (
            self.user.login_details_provided
            and await self.user.is_uk_account_and_location()
        ):
            return await self.personal.construct_uk_menu(
                listen_live=listen_live,
                catch_up=catch_up,
                schedule=schedule,
                include_recommendations=include_recommendations,
            )
        else:
            return await self.personal.construct_international_menu(
                listen_live=listen_live,
                catch_up=catch_up,
                schedule=schedule,
            )

    async def logout(self):
        logger.debug("Logging out...")
        self.cookie_store.clear()
        self.cookie_store.save()
        logger.debug("Logged out.")

    async def close(self):
        logger.debug("Session close explicitly requested.")
        if self._session and self.managing_session:
            await self._session.close()
        self.cookie_store.save()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        if self.managing_session:
            logger.debug("Closed session")
            await self.close()
        self.cookie_store.save()
