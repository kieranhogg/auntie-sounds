import logging
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)

# This is the ID of the cookie we use to check we have a valid session
COOKIE_ID = "ckns_id"


class CookieStore:
    _COOKIE_CLEAR_DOMAINS = ("bbc.co.uk", "bbc.com")

    def __init__(
        self,
        session: aiohttp.ClientSession,
        mock_session: bool = False,
        cookie_file_location: str | Path | None = None,
    ):
        if isinstance(cookie_file_location, str):
            self.path = Path(cookie_file_location)
        else:
            self.path = cookie_file_location
        self.mock_session = mock_session
        self.session = session

    def load(self) -> None:
        logger.debug("Loading cookies from disk...")
        if self.path.exists():
            if len(self.session.cookie_jar) > 0:
                logger.info("Skipping loading into existing cookie jar.")
            else:
                self.session.cookie_jar.load(self.path)  # ty:ignore[unresolved-attribute]
            return
        logger.warning("Cookie location does not exist.")

    def save(self) -> None:
        logger.debug("Saving cookies to disk...")
        self.session.cookie_jar.save(self.path)  # ty:ignore[unresolved-attribute]

    @property
    def has_session_cookie(self) -> bool:
        """Check if we have a cookie present."""
        logger.debug("Checking if we are logged in...")
        if self.mock_session:
            logger.debug("mock_session=True")
        existing_cookies = self._get_filtered_cookies()
        if len(existing_cookies) > 0:
            logger.debug("Existing cookie found.")
            return True
        logger.debug("No cookies found.")
        return False

    def _get_filtered_cookies(self) -> list:
        filtered_cookies = [
            cookie for cookie in self.session.cookie_jar if cookie.key == COOKIE_ID
        ]
        logger.debug(filtered_cookies)
        return filtered_cookies

    def clear(self) -> None:
        logger.debug("Clearing cookies...")

        logger.debug(self._get_filtered_cookies())
        for base in self._COOKIE_CLEAR_DOMAINS:
            self.session.cookie_jar.clear_domain(base)
        logger.debug(self._get_filtered_cookies())
