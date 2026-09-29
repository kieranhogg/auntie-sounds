import logging
from http.cookiejar import FileCookieJar
from pathlib import Path
from typing import cast

import aiohttp

logger = logging.getLogger(__name__)

# This is the ID of the cookie we use to check we have a valid session
COOKIE_ID = "ckns_id"

# Special value for cookie owner when initial per-account cookie store
_ANONYMOUS_OWNER = "\0anonymous"


class CookieStore:
    _COOKIE_CLEAR_DOMAINS = ("bbc.co.uk", "bbc.com")

    def __init__(
        self,
        session: aiohttp.ClientSession,
        mock_session: bool = False,
        cookie_file_location: str | Path | None = None,
        account_id: str | None = None,
    ):
        self.path: Path | None
        if isinstance(cookie_file_location, str):
            self.path = Path(cookie_file_location)
        else:
            self.path = cookie_file_location

        self.mock_session = mock_session
        self.session = session
        self.account_id = account_id

    @property
    def _owner_path(self) -> Path | None:
        if self.path is None:
            return None
        return self.path.with_name(self.path.name + ".owner")

    def _read_owner(self) -> str | None:
        """Return the account_id recorded for the on-disk cookie file.

        Returns None if there is no marker file at all (a cookie file
        saved before this tracking existed, or not created by us).
        """
        owner_path = self._owner_path
        if owner_path is None or not owner_path.exists():
            return None
        try:
            return owner_path.read_text(encoding="utf-8").strip()
        except OSError:
            logger.warning(
                "Could not read cookie owner marker, so treating as untracked."
            )
            return None

    def _write_owner(self) -> None:
        owner_path = self._owner_path
        if owner_path is None:
            return
        owner_path.write_text(
            self.account_id if self.account_id is not None else _ANONYMOUS_OWNER,
            encoding="utf-8",
        )

    def load(self) -> None:
        logger.debug("Loading cookies from disk...")
        if self.path is None:
            logger.warning("No cookie file location configured.")
            return
        if self.path.exists():
            if len(self.session.cookie_jar) > 0:
                logger.info("Skipping loading into existing cookie jar.")
                return

            recorded_owner = self._read_owner()
            this_owner = (
                self.account_id if self.account_id is not None else _ANONYMOUS_OWNER
            )
            if recorded_owner is not None and recorded_owner != this_owner:
                logger.warning(
                    "Cookie file at %s belongs to a different account; "
                    "refusing to load a foreign session.",
                    self.path,
                )
                return

            cast(
                aiohttp.CookieJar,
                self.session.cookie_jar,
            ).load(str(self.path))

            if recorded_owner is None:
                # Legacy cookie file with no owner marker <v2.1.0
                self._write_owner()
        logger.warning("Cookie location does not exist.")

    def save(self) -> None:
        if self.path is None:
            logger.warning("No cookie file location configured.")
            return
        logger.debug("Saving cookies to disk...")
        cast(FileCookieJar, self.session.cookie_jar).save(str(self.path))
        self._write_owner()

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
            cookie
            for cookie in cast(aiohttp.CookieJar, self.session.cookie_jar)
            if cookie.key == COOKIE_ID
        ]
        logger.debug([m.key for m in filtered_cookies])
        return filtered_cookies

    def clear(self) -> None:
        logger.debug("Clearing cookies...")

        logger.debug(self._get_filtered_cookies())
        for base in self._COOKIE_CLEAR_DOMAINS:
            self.session.cookie_jar.clear_domain(base)
        logger.debug([m.key for m in self._get_filtered_cookies() if m])
