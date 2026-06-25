from logging import Logger
from pathlib import Path

from aiohttp import CookieJar
from aiohttp.abc import AbstractCookieJar
from yarl import URL

from sounds import constants


class Session:
    def __init__(
        self,
        cookie_file: str | Path,
        logger: Logger,
        mock_session: bool = False,
        jar: CookieJar | None = None,
        unsafe: bool = True,
        *args,
        **kwargs,
    ):
        if isinstance(cookie_file, str):
            self.path = Path(cookie_file)
        else:
            self.path = cookie_file
        self.logger = logger
        self._jar = jar if jar is not None else CookieJar(unsafe=unsafe)
        self.jar: AbstractCookieJar = self._jar
        self.mock_session = mock_session

    def load(self) -> None:
        if self.path.exists():
            self._jar.load(self.path)

    def save(self) -> None:
        self._jar.save(self.path)

    @property
    def has_session_cookie(self) -> bool:
        """Check if we have a cookie present."""
        self.logger.debug("Checking if we are logged in...")
        if self.mock_session:
            self.logger.debug("mock_session=True")

            return True

        jar = self._jar
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

    def clear(self) -> None:
        self._jar.clear()
