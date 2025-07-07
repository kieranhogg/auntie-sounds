import aiohttp
import logging
from abc import ABC
from typing import Optional

from .constants import URLs
from .exceptions import SoundsAPIException


class Base(ABC):
    """Base class for other classes to inherit shared session and state"""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        logger: Optional[logging.Logger] = None,
        timeout: Optional[aiohttp.ClientTimeout] = None,
    ):
        self._session = session
        self._timeout = timeout or aiohttp.ClientTimeout(total=10)

    async def _make_request(
        self, method: str, url: str, **kwargs
    ) -> aiohttp.ClientResponse:
        """Makes a HTTP request using the shared session and state"""
        try:
            kwargs.setdefault("timeout", self._timeout)
            kwargs.setdefault("ssl", True)
            kwargs.setdefault("allow_redirects", True)
            async with self._session.request(method, url, **kwargs) as resp:
                resp.raise_for_status()
                return resp
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP request failed: {method} {url} - {e}")
            raise SoundsAPIException(f"Request failed: {e}")

    async def _get_json(self, url: str, **kwargs) -> dict:
        """Gets JSON response"""
        kwargs.setdefault("timeout", self._timeout)
        kwargs.setdefault("ssl", True)
        kwargs.setdefault("allow_redirects", True)
        try:
            async with self._session.request("GET", url, **kwargs) as resp:
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP request failed: {url} - {e}")
            raise SoundsAPIException(f"Request failed: {e}")

    async def _get_html(self, url: str, method: str = "GET", **kwargs) -> str:
        kwargs.setdefault("timeout", self._timeout)
        kwargs.setdefault("ssl", True)
        kwargs.setdefault("allow_redirects", True)
        try:
            async with self._session.request(method, url, **kwargs) as resp:
                resp.raise_for_status()
                return await resp.text()
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP request failed: {method} {url} - {e}")
            raise SoundsAPIException(f"Request failed: {e}")

    async def get_jwt_token(self, station_id):
        async with self._session.get(
            URLs.JWT_URL.format(station_id=station_id)
        ) as resp:
            json = await resp.json()
            return json.get("token")
