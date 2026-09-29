import asyncio.constants
import hashlib
import logging
from collections.abc import Sequence
from datetime import tzinfo
from http.cookiejar import CookieJar as HttpCookieJar
from pathlib import Path

import aiohttp
import pytz

from sounds.auth import AuthService
from sounds.content import ContentService
from sounds.cookies import CookieStore
from sounds.exceptions import InvalidArgumentsError
from sounds.models import Menu, MenuItem
from sounds.personal import PersonalService
from sounds.playback import PlaybackService
from sounds.requests import RequestManager
from sounds.schedule import ScheduleService
from sounds.stations import StationService
from sounds.user import UserService
from sounds.utils import _get_data_dir

# Not-signed-in cookie location
COOKIE_FILE = Path(_get_data_dir(), "sounds_jar")

logger = logging.getLogger(__name__)


def _default_cookie_file(username: str | None) -> Path:
    """Return the default cookie file path for a given account.

    We use a cookie jar location per-username to avoid clashes. Anonymous sessions still
    use COOKIE_FILE.
    """
    if not username:
        return COOKIE_FILE
    digest = hashlib.sha256(username.encode("utf-8")).hexdigest()[:16]
    return Path(_get_data_dir(), f"sounds_jar_{digest}")


class SoundsClient:
    """A client to interact with the Sounds API."""

    def __init__(
        self,
        username=None,
        password=None,
        session=None,
        cookie_file_location=None,
        timezone=None,
        log_level=None,
        debug_login=False,
    ) -> None:
        if log_level:
            logger.setLevel(log_level)
        logger.debug("Creating new SoundsClient...")

        self.username = username
        self.password = password
        self.debug_login = debug_login
        self.cookie_store: CookieStore
        self._external_session: aiohttp.ClientSession | None = session
        self._session: aiohttp.ClientSession
        self._started = False
        self._cookie_path = cookie_file_location or _default_cookie_file(self.username)

        if timezone:
            self.timezone: tzinfo = timezone
        else:
            logger.warning(
                "No timezone provided, assuming UTC so any time calculations for the schedules may be incorrect"
            )
            self.timezone = pytz.timezone("UTC")

    @classmethod
    async def create(cls, *args, **kwargs) -> SoundsClient:
        client = cls(*args, **kwargs)
        await client.start()
        return client

    async def start(self) -> None:
        if self._started:
            logger.info("Client already started.")
            return

        self._session = (
            self._external_session
            if self._external_session is not None
            else aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar())
        )
        if not isinstance(self._session.cookie_jar, aiohttp.CookieJar):
            raise TypeError(
                "SoundsClient requires an aiohttp.CookieJar for persistence"
            )
        if len(self._session.cookie_jar) > 0:
            raise InvalidArgumentsError(
                "This session's cookie jar already contains cookies, so it may be shared "
                "with another account. Pass each account its own session"
            )

        self.cookie_store = CookieStore(
            session=self._session,
            cookie_file_location=self._cookie_path,
            account_id=self.username,
        )
        await asyncio.to_thread(self.cookie_store.load)
        self._create_services()
        self._started = True

    def _create_services(self) -> None:
        login_details_provided: bool = bool(self.username and self.password)

        if not isinstance(self._session.cookie_jar, (HttpCookieJar, aiohttp.CookieJar)):
            raise TypeError(
                "SoundsClient requires aiohttp.CookieJar for cookie persistence"
            )

        self.requests: RequestManager = RequestManager(
            session=self._session,
            login_details_provided=login_details_provided,
        )

        self.auth = AuthService(
            requests=self.requests,
            cookie_store=self.cookie_store,
            username=self.username,
            password=self.password,
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

        Renews an existing session if possible, otherwise logs in.

        :return: True on success
        :raises LoginFailedError: If the login fails for any reason
        :raises UnauthorisedError: If the login is not authorised
        :raises InvalidArgumentsError: If either a username or password isn't set
        """

        if not self.username or not self.password:
            raise InvalidArgumentsError(
                "Can't authenticate without username and password set"
            )

        await self.auth.authenticate()
        await self.save_cookies()
        await self.user.refresh()
        return True

    async def save_cookies(self):
        await asyncio.to_thread(self.cookie_store.save)

    async def load_cookies(self):
        await asyncio.to_thread(self.cookie_store.load)

    async def clear_cookies(self):
        await asyncio.to_thread(self.cookie_store.clear)
        await asyncio.to_thread(self.cookie_store.save)

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
        radio, schedule, catch_up = await asyncio.gather(
            self.stations.get_radio_menu(include_local_stations=include_local_stations),
            self.stations.get_schedule_menu(
                include_local_stations=include_local_stations, depth=2
            ),
            self.stations.get_catch_up_menu(
                include_local_stations=include_local_stations
            ),
        )
        if (
            self.user.login_details_provided
            and await self.user.is_uk_account_and_location()
        ):
            return await self.personal.construct_uk_menu(
                radio=radio,
                catch_up=catch_up,
                schedule=schedule,
                include_recommendations=include_recommendations,
            )
        else:
            return await self.personal.construct_international_menu(
                radio=radio,
                catch_up=catch_up,
                schedule=schedule,
            )

    async def logout(self):
        logger.debug("Logging out...")
        await self.clear_cookies()
        await self.save_cookies()
        logger.debug("Logged out.")

    async def close(self):
        if not self._started:
            return
        logger.debug("Closing session...")
        await self.save_cookies()
        if self._external_session is None:
            await self._session.close()
        self._started = False
        logger.debug("Session closed.")

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.close()
