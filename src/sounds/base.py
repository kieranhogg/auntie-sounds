import json
import logging
import os
from abc import ABC
from typing import Literal, Optional

import aiohttp

from .constants import FIXTURES_FOLDER, Fixtures, SignedInURLs, URLs
from .exceptions import (
    APIResponseError,
    InvalidArgumentsError,
    NetworkError,
    NotFoundError,
    SoundsException,
    UnauthorisedError,
)


class Base(ABC):
    """Base class for other classes to inherit shared session and state"""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        logger: logging.Logger | None = None,
        timeout: Optional[aiohttp.ClientTimeout] = None,
        mock_session: bool = False,
        **kwargs,
    ):
        self._session = session
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
        self._timeout = timeout or aiohttp.ClientTimeout(total=10)
        self.mock_session = mock_session

    async def _make_request(
        self, method: Literal["GET"] | Literal["POST"], url: str, **kwargs
    ) -> aiohttp.ClientResponse:
        """Makes a HTTP request using the shared session and state"""
        self.logger.debug(f"Making HTTP {method} request to {url}")
        self.logger.debug(str(kwargs))
        try:
            kwargs.setdefault("timeout", self._timeout)
            kwargs.setdefault("ssl", True)
            kwargs.setdefault("allow_redirects", True)
            for cookie in self._session.cookie_jar:
                self.logger.debug(
                    f"Cookie before: {cookie.key}={cookie.value} (domain={cookie['domain']})"
                )
            resp = await self._session.request(method, url, **kwargs)
            for cookie in self._session.cookie_jar:
                self.logger.debug(
                    f"Cookie after: {cookie.key}={cookie.value} (domain={cookie['domain']})"
                )

            self.logger.debug(f"Response headers: {resp.headers}")
            self.logger.debug(f"Response content type: {resp.content_type}")
            self.logger.debug(f"Response status: {resp.status}")
            self.logger.debug(f"Response url: {resp.url}")
            self.logger.debug(resp)
            self.logger.debug(f"HTTP {method} {url} - Status {resp.status}")
            if not (200 <= resp.status < 400):  # Allow 2xx and 3xx
                # Check if we got any errors in the API response
                if resp.content_type == "application/json":
                    json_resp = await resp.json()
                    if "errors" in json_resp.keys():
                        code = json_resp["errors"][0]["status"]
                        message = json_resp["errors"][0]["message"]
                        if code == 401:
                            raise UnauthorisedError(message)
                        else:
                            raise APIResponseError(message)
            return resp
        except aiohttp.ClientConnectorDNSError as e:
            self.logger.error(f"HTTP request failed: {method} {url} - {e}")
            raise NetworkError(f"Connection failed: {e}")
        except aiohttp.ContentTypeError as e:
            self.logger.error(f"HTTP request failed: {method} {url} - {e}")
            raise SoundsException(f"Invalid response type: {e}")
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP request failed: {method} {url} - {e}")
            raise SoundsException(f"Request failed: {e}")

    def _build_url(
        self,
        url: Optional[URLs | SignedInURLs | str] = None,
        url_template: Optional[URLs | SignedInURLs] = None,
        url_args=None,
    ) -> str:
        if isinstance(url, str):
            return url
        elif url:
            return url.value
        if url_template and url_args:
            return url_template.value.format(**url_args)
        elif url_template:
            return url_template.value

        raise InvalidArgumentsError("One of url or url_template must be set")

    async def _get_json(
        self,
        url: URLs | SignedInURLs | str | None = None,
        url_template: URLs | SignedInURLs | None = None,
        url_args: dict | None = None,
        **kwargs,
    ) -> dict:
        """Gets JSON response"""
        kwargs.setdefault("timeout", self._timeout)
        kwargs.setdefault("ssl", True)
        kwargs.setdefault("allow_redirects", True)
        url = self._build_url(url=url, url_template=url_template, url_args=url_args)

        if self.mock_session and url_template:
            try:
                filename = Fixtures[url_template.name].value
                json_file = os.path.join(FIXTURES_FOLDER, filename)
                with open(json_file) as file_reader:
                    json_contents = json.loads(file_reader.read())
                return json_contents
            except KeyError:
                raise InvalidArgumentsError(f"No matching fixture for {url_template}")

        try:
            self.logger.debug(f"Requesting URL {url}")
            for cookie in self._session.cookie_jar:
                self.logger.debug(
                    f"Cookie before: {cookie.key}={cookie.value} (domain={cookie['domain']})"
                )
            resp = await self._session.request(method="GET", url=url, **kwargs)
            for cookie in self._session.cookie_jar:
                self.logger.debug(
                    f"Cookie after: {cookie.key}={cookie.value} (domain={cookie['domain']})"
                )
            json_resp = await resp.json()
            # Check if we got any errors in the API response
            if "errors" in json_resp.keys():
                code = json_resp["errors"][0]["status"]
                message = json_resp["errors"][0]["message"]
                if code == 401:
                    raise UnauthorisedError(message)
                elif code == 404:
                    raise NotFoundError(message)
                else:
                    raise APIResponseError(message)
            return json_resp
        except aiohttp.ClientResponseError as e:
            if e.status == 401:
                raise UnauthorisedError(e)
            raise APIResponseError(f"Request failed: {e}")
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP request failed: {url} - {e}")
            raise SoundsException(f"Request failed: {e}")

    async def _get_html(
        self,
        url: str | None = None,
        url_template: Optional[URLs | SignedInURLs] = None,
        url_args: dict | None = None,
        method: str = "GET",
        **kwargs,
    ) -> str:
        kwargs.setdefault("timeout", self._timeout)
        kwargs.setdefault("ssl", True)
        kwargs.setdefault("allow_redirects", True)
        url = self._build_url(url=url, url_template=url_template, url_args=url_args)
        self.logger.debug(f"Making HTTP {method} request to {url}")
        for cookie in self._session.cookie_jar:
            self.logger.debug(
                f"Cookie before: {cookie.key}={cookie.value} (domain={cookie['domain']})"
            )

        try:
            resp = await self._session.request(method, url, **kwargs)
            self.logger.debug(f"Response status: {resp.status}")
            self.logger.debug(f"Response headers: {resp.headers}")
            resp.raise_for_status()
            for cookie in self._session.cookie_jar:
                self.logger.debug(
                    f"Cookie after: {cookie.key}={cookie.value} (domain={cookie['domain']})"
                )
            return await resp.text()
        except aiohttp.ClientResponseError as e:
            if e.status == 401:
                raise UnauthorisedError(e)
            raise APIResponseError(f"Request failed: {e}")
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP request failed: {method} {url} - {e}")
            raise SoundsException(f"Request failed: {e}")

    async def get_jwt_token(self, station_id):
        json = await self._get_json(
            url_template=URLs.JWT, url_args={"station_id": station_id}
        )
        if "token" not in json:
            raise APIResponseError(f"Couldn't get JWT token: {json}")
        return json.get("token")
