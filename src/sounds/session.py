from pathlib import Path

from aiohttp import CookieJar
from aiohttp.abc import AbstractCookieJar
from yarl import URL

from sounds.constants import COOKIE_ID, URLs


class Session:
    def __init__(self, cookie_file: str | Path, *, unsafe: bool = True):
        if isinstance(cookie_file, str):
            self.path = Path(cookie_file)
        else:
            self.path = cookie_file

        self._jar: CookieJar = CookieJar(unsafe=unsafe)
        self.jar: AbstractCookieJar = self._jar

    def load(self) -> None:
        if self.path.exists():
            self._jar.load(self.path)

    def save(self) -> None:
        self._jar.save(self.path)

    @property
    def is_logged_in(self) -> bool:
        return (COOKIE_ID in self._jar.filter_cookies(URL(URLs.COOKIE_BASE.value))) or (
            COOKIE_ID in self._jar.filter_cookies(URL(URLs.COOKIE_BASE_I18N.value))
        )

    def clear(self) -> None:
        self._jar.clear()
