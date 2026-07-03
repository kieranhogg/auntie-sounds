from logging import Logger
from pathlib import Path

import aiohttp
from yarl import URL

from sounds import constants
from sounds.constants import COOKIE_ID


class CookieStore:
    _COOKIE_CLEAR_DOMAINS = ("bbc.co.uk", "bbc.com")

    def __init__(
        self,
        session: aiohttp.ClientSession,
        logger: Logger,
        cookie_file_location: Path | str,
        mock_session: bool = False,
        *args,
        **kwargs,
    ):
        if isinstance(cookie_file_location, str):
            self.path = Path(cookie_file_location)
        else:
            self.path = cookie_file_location
        self.logger = logger
        self.mock_session = mock_session
        self.session = session

    def load(self) -> None:
        self.logger.debug("Loading cookies from disk...")
        if self.path.exists():
            if len(self.session.cookie_jar) > 0:
                self.logger.info("Skipping loading into existing cookie jar.")
            else:
                self.session.cookie_jar.load(self.path)  # ty:ignore[unresolved-attribute]
            return
        self.logger.warning("Cookie location does not exist.")

    def save(self) -> None:
        self.logger.debug("Saving cookies to disk...")
        self.session.cookie_jar.save(self.path)  # ty:ignore[unresolved-attribute]

    def get_filtered_cookies(self):
        return list(
            self.session.cookie_jar.filter_cookies(
                URL(constants.URLs.COOKIE_BASE.value)
            )
        ).extend(
            list(
                self.session.cookie_jar.filter_cookies(
                    URL(constants.URLs.COOKIE_BASE_I18N.value)
                )
            )
        )

    @property
    def has_session_cookie(self) -> bool:
        """Check if we have a cookie present."""
        self.logger.debug("Checking if we are logged in...")
        if self.mock_session:
            self.logger.debug("mock_session=True")
        existing_cookies = self._get_filtered_cookies()
        if len(existing_cookies) > 0:
            self.logger.debug("Existing cookie found.")
            return True
        self.logger.debug("No cookies found.")
        return False

    def _get_filtered_cookies(self) -> list:
        filtered_cookies = [
            cookie for cookie in self.session.cookie_jar if cookie.key == COOKIE_ID
        ]
        self.logger.debug(filtered_cookies)
        return filtered_cookies

    def clear(self) -> None:
        self.logger.debug("Clearing cookies...")

        self.logger.debug(self._get_filtered_cookies())
        for base in self._COOKIE_CLEAR_DOMAINS:
            self.session.cookie_jar.clear_domain(base)
        self.logger.debug(self._get_filtered_cookies())
