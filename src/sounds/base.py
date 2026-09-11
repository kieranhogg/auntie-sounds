import json
import logging
import os
from abc import ABC
from typing import Literal

import aiofiles
import aiohttp
from pytz import tzinfo

from sounds.constants import FIXTURES_FOLDER, SignedInURLs, URLs
from sounds.exceptions import (
    APIResponseError,
    InvalidArgumentsError,
    NetworkError,
    NotFoundError,
    SoundsException,
    UnauthorisedError,
)

logger = logging.getLogger(__name__)

class Base(ABC):
    """Base class for other classes to inherit shared session and state"""

    DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10)

    def __init__(
        self,
        session: aiohttp.ClientSession,
        timezone: tzinfo | None = None,
        timeout: aiohttp.ClientTimeout | None = None,
        mock_session: bool = False,
        *args,
        **kwargs,
    ):
        self._session = session
        self.timezone = timezone
        self._timeout = timeout or self.DEFAULT_TIMEOUT
        self.mock_session = mock_session

    async def _make_request(
        self, method: Literal["GET", "POST"], url: str, **kwargs
    ) -> aiohttp.ClientResponse:
        """Makes an HTTP request using the shared session and state"""
        logger.debug(f"Making HTTP {method} request to {url}")
        try:
            kwargs.setdefault("timeout", self._timeout or self.DEFAULT_TIMEOUT)
            kwargs.setdefault("ssl", True)
            kwargs.setdefault("allow_redirects", True)

            resp = await self._session.request(method, url, **kwargs)

            logger.debug(f"Response content type: {resp.content_type}")
            logger.debug(f"Response status: {resp.status}")
            logger.debug(f"Response url: {resp.url}")
            logger.debug(f"HTTP {method} {url} - Status {resp.status}")
            if (
                not (200 <= resp.status < 400)  # Allow 2xx and 3xx
                and resp.content_type == "application/json"
            ):
                # Check if we got any errors in the API response
                json_resp = await resp.json()
                if "errors" in json_resp:
                    code = json_resp["errors"][0]["status"]
                    message = json_resp["errors"][0]["message"]
                    if code == 401:
                        raise UnauthorisedError(message)
                    else:
                        raise APIResponseError(message)
            return resp
        except aiohttp.ClientConnectorDNSError as e:
            logger.error(f"HTTP request failed: {method} {url} - {e}")
            raise NetworkError(f"Connection failed: {e}")
        except aiohttp.ContentTypeError as e:
            logger.error(f"HTTP request failed: {method} {url} - {e}")
            raise SoundsException(f"Invalid response type: {e}")
        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed: {method} {url} - {e}")
            raise SoundsException(f"Request failed: {e}")

    def _build_url(
        self,
        url: URLs | SignedInURLs | str | None = None,
        url_template: URLs | SignedInURLs | None = None,
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

        if self.mock_session and (url_template or url):
            try:
                filename = (url_template or url).name
                json_file = os.path.join(FIXTURES_FOLDER, filename + ".json")
                async with aiofiles.open(json_file) as file_reader:
                    json_contents = json.loads(await file_reader.read())
                return json_contents
            except KeyError:
                raise InvalidArgumentsError(f"No matching fixture for {url_template}")

        try:
            logger.debug(f"Requesting URL {url}")
            resp = await self._session.request(method="GET", url=url, **kwargs)
            json_resp = await resp.json()

            # Check if we got any errors in the API response
            if "errors" in json_resp:
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
            logger.error(f"HTTP request failed: {url} - {e}")
            raise SoundsException(f"Request failed: {e}")

    async def _get_html(
        self,
        url: str | None = None,
        url_template: URLs | SignedInURLs | None = None,
        url_args: dict | None = None,
        method: str = "GET",
        **kwargs,
    ) -> str:
        kwargs.setdefault("timeout", self._timeout)
        kwargs.setdefault("ssl", True)
        kwargs.setdefault("allow_redirects", True)
        url = self._build_url(url=url, url_template=url_template, url_args=url_args)
        logger.debug(f"Making HTTP {method} request to {url}")

        try:
            resp = await self._session.request(method, url, **kwargs)
            logger.debug(f"Response status: {resp.status}")
            resp.raise_for_status()
            return await resp.text()
        except aiohttp.ClientResponseError as e:
            if e.status == 401:
                raise UnauthorisedError(e)
            raise APIResponseError(f"Request failed: {e}")
        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed: {method} {url} - {e}")
            raise SoundsException(f"Request failed: {e}")
