import aiohttp
import logging
from abc import ABC
from typing import Literal, Optional

from .constants import URLs
from .exceptions import SoundsException, UnauthorisedError, APIResponseError


class Base(ABC):
    """Base class for other classes to inherit shared session and state"""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        logger: logging.Logger | None = None,
        timeout: Optional[aiohttp.ClientTimeout] = None,
        **kwargs,
    ):
        self._session = session
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
        self._timeout = timeout or aiohttp.ClientTimeout(total=10)

    async def _make_request(
        self, method: Literal["GET"] | Literal["POST"], url: str, **kwargs
    ) -> aiohttp.ClientResponse:
        """Makes a HTTP request using the shared session and state"""
        try:
            kwargs.setdefault("timeout", self._timeout)
            kwargs.setdefault("ssl", True)
            kwargs.setdefault("allow_redirects", True)
            resp = await self._session.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP request failed: {method} {url} - {e}")
            raise SoundsException(f"Request failed: {e}")

    async def _get_json(self, url: str, **kwargs) -> dict:
        """Gets JSON response"""
        kwargs.setdefault("timeout", self._timeout)
        kwargs.setdefault("ssl", True)
        kwargs.setdefault("allow_redirects", True)
        try:
            resp = await self._session.request("GET", url, **kwargs)
            json_resp = await resp.json()
            # resp.raise_for_status()
            return await resp.json()
        except aiohttp.ClientResponseError as e:
            if e.status == 401:
                raise UnauthorisedError(e)
            raise APIResponseError(f"Request failed: {e}")
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP request failed: {url} - {e}")
            raise SoundsException(f"Request failed: {e}")

    async def _get_html(self, url: str, method: str = "GET", **kwargs) -> str:
        kwargs.setdefault("timeout", self._timeout)
        kwargs.setdefault("ssl", True)
        kwargs.setdefault("allow_redirects", True)
        try:
            resp = await self._session.request(method, url, **kwargs)
            resp.raise_for_status()
            return await resp.text()
        except aiohttp.ClientResponseError as e:
            if e.status == 401:
                raise UnauthorisedError(e)
            raise APIResponseError(f"Request failed: {e}")
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP request failed: {method} {url} - {e}")
            raise SoundsException(f"Request failed: {e}")

    async def get_jwt_token(self, station_id):
        resp = self._session.get(URLs.JWT_URL.format(station_id=station_id))
        json = await resp.json()
        return json.get("token")
