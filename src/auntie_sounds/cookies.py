import logging
from pathlib import Path
from typing import cast

import aiohttp

logger = logging.getLogger(__name__)

# This is the ID of the cookie we use to check we have a valid session
ID_COOKIE = "ckns_id"
ACCESS_TOKEN_COOKIE = "ckns_atkn"

# Special value for cookie owner when initial per-account cookie store
_ANONYMOUS_OWNER = "\0anonymous"


def _owner_path(path: Path) -> Path:
    """Helper for typing, as owner path depends on path."""
    return path.with_name(f"{path.name}.owner")


class CookieStore:
    _COOKIE_CLEAR_DOMAINS = ("bbc.co.uk", "bbc.com")

    def __init__(
        self,
        session: aiohttp.ClientSession,
        cookie_file_location: str | Path | None = None,
        account_id: str | None = None,
    ):
        self.path: Path | None
        if isinstance(cookie_file_location, str):
            self.path = Path(cookie_file_location)
        else:
            self.path = cookie_file_location
        logger.debug("Cookie jar location: %s", self.path)
        self.session = session
        self.account_id = account_id

    @property
    def is_signed_in(self) -> bool:
        return self._has_cookie(ID_COOKIE)

    @property
    def has_access_token(self) -> bool:
        return self._has_cookie(ACCESS_TOKEN_COOKIE)

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

            try:
                cast(aiohttp.CookieJar, self.session.cookie_jar).load(str(self.path))
            except Exception:
                # If we run into any issues loading the cookie jar, restarting the
                # session is the best option here
                logger.warning(
                    "Couldn't read the cookie file at %s, starting without a session",
                    self.path,
                    exc_info=True,
                )
                return

            if recorded_owner is None:
                # Legacy cookie file with no owner marker <v3.0.0
                self._write_owner()
        else:
            logger.warning("Cookie location does not exist.")

    def save(self) -> None:
        if self.path is None:
            logger.warning("No cookie file location configured.")
            return
        logger.debug("Saving cookies to disk...")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        cast(aiohttp.CookieJar, self.session.cookie_jar).save(str(self.path))
        self._write_owner()

    def clear(self) -> None:
        """Clear the cookies with domains matching `self._COOKIE_CLEAR_DOMAINS`."""
        logger.debug("Clearing cookies, signed in before: %s", self.is_signed_in)
        for base in self._COOKIE_CLEAR_DOMAINS:
            self.session.cookie_jar.clear_domain(base)

    def delete(self) -> None:
        """Remove the persisted jar and its owner file, if present."""
        if self.path is None:
            logger.warning("No cookie file location configured.")
            return
        logger.debug("Deleting cookie jar at %s...", self.path)
        for path in (self.path, _owner_path(self.path)):
            path.unlink(missing_ok=True)
            logger.debug("Deleted")

    def _has_cookie(self, name: str) -> bool:
        # aiohttp drops expired cookies before we check
        return any(
            c.key == name and c["domain"].endswith("bbc.co.uk")
            for c in self.session.cookie_jar
        )

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
        if self.path is None:
            return None
        owner_path = _owner_path(self.path)
        if not owner_path.exists():
            return None
        try:
            return owner_path.read_text(encoding="utf-8").strip()
        except OSError:
            logger.warning(
                "Could not read cookie owner marker, so treating as untracked."
            )
            return None

    def _write_owner(self) -> None:
        if self.path is None:
            return
        _owner_path(self.path).write_text(
            self.account_id if self.account_id is not None else _ANONYMOUS_OWNER,
            encoding="utf-8",
        )
