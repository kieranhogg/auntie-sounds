import json
import logging
import os
import re
import unittest
from functools import partial
from typing import TYPE_CHECKING, Awaitable, Callable, Literal
from unittest.mock import Mock

import aiofiles
import aiohttp
from mypy.build import build

from sounds.cookies import CookieStore
from sounds.endpoints import URLs
from sounds.exceptions import (
    APIResponseError,
    InvalidArgumentsError,
    NetworkError,
    NotFoundError,
    SoundsException,
    UnauthorisedError,
)
from sounds.testing_support import FIXTURES_FOLDER

if TYPE_CHECKING:
    from aiohttp import ClientSession, ClientTimeout

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10)


def build_url(
    url: URLs | str,
    url_args: dict | None = None,
) -> str:
    if isinstance(url, URLs):
        url = url.value
    pattern = re.compile(r".*(\{.*}).*")
    parameters_required = re.findall(pattern, url)
    for keyword in parameters_required:
        keyword = keyword.replace("{", "").replace("}", "")
        if not url_args or keyword not in url_args:
            raise InvalidArgumentsError(
                f"{keyword} is a required parameter for the URL, but it is not in url_args."
            )
    if parameters_required and url_args:
        return url.format(**url_args)
    return url


def build_headers(referer: str | None = None) -> dict:
    """Builds the standard headers to send."""
    base_headers = {
        "Accept-Language": "en-GB,en;q=0.9",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "Origin": URLs.LOGIN_BASE.value,
        "Cache-Control": "max-age=0",
    }
    if referer:
        base_headers["Referer"] = referer
    return base_headers


def _raise_for_api_errors(json_resp: dict) -> None:
    """Raises the right exception if the API response body carries an errors block."""
    errors = json_resp.get("errors")
    if not errors:
        return
    code = errors[0]["status"]
    message = errors[0]["message"]
    if code == 401:
        raise UnauthorisedError(message)
    elif code == 404:
        raise NotFoundError(message)
    raise APIResponseError(message)


class RequestManager:
    def __init__(
        self,
        session: ClientSession,
        timeout: ClientTimeout = DEFAULT_TIMEOUT,
        mock_session: bool = False,
        username: str | None = None,
        password: str | None = None,
        reauth_handler: Callable | None = None,
    ):
        self._session: ClientSession = session
        self.timeout: ClientTimeout = timeout
        self.mock_session: bool = mock_session
        self.username: str | None = username
        self.password: str | None = password
        self.reauth_handler: Callable | None = reauth_handler

    async def run(self, call):
        """Ensures user is logged in before running `call`."""
        try:
            logger.debug(f"Running {call}")
            return await call()
        except UnauthorisedError:
            logger.debug("Unauthorised when accessing an authenticated endpoint.")

            if not self.username or not self.password:
                logger.error("No username and/or password provided.")
                raise UnauthorisedError(
                    "No username and/or password provided and endpoint requires authentication."
                )

            if self.reauth_handler:
                logger.debug("Calling reauth_handler %s.", self.reauth_handler)
                await self.reauth_handler()
                return await call()
            raise

    async def _request_or_raise(self, method, url, **kwargs) -> aiohttp.ClientResponse:
        """Make a HTTP request, converting any 401s errors into UnauthorisedError

        run() checks against authenticated endpoints, renewing a session if required.
        To do this we need intercept 401s and raise an UnauthorisedError so it can
        be retried
        """
        resp = await self._session.request(method, url, **kwargs)
        if resp.status == 401:
            raise UnauthorisedError(resp.reason)
        return resp

    async def make_request(
        self,
        method: Literal["GET", "POST"],
        url: URLs | str,
        url_args: dict | None = None,
        login_required: bool = False,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Makes an HTTP request using the shared session, applying defaults
        and handling connection-level errors. Also ensures auth, if needed."""
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("ssl", True)
        kwargs.setdefault("allow_redirects", True)
        # kwargs.setdefault("headers", build_headers())

        if isinstance(url, URLs):
            # If we have a endpoint, we can check if it's an authenticated one
            login_required = url.login_required
            url = build_url(url, url_args)
        else:
            if url in URLs:
                raise InvalidArgumentsError(
                    "URL passed a string, use a URL instance instead."
                )
        logger.debug(f"Making HTTP {method} request to {url}")
        try:
            if login_required:
                resp = await self.run(
                    partial(self._request_or_raise, method=method, url=url, **kwargs)
                )
            else:
                resp = await self._request_or_raise(method, url, **kwargs)
            logger.debug(f"HTTP {method} {url} - Status {resp.status}")
            resp.raise_for_status()
            return resp
        except aiohttp.ClientConnectorDNSError as e:
            logger.error(f"HTTP request failed: {method} {url} - {e}")
            raise NetworkError(f"Connection failed: {e}") from e
        except aiohttp.ContentTypeError as e:
            logger.error(f"HTTP request failed: {method} {url} - {e}")
            raise SoundsException(f"Invalid response type: {e}") from e
        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed: {method} {url} - {e}")
            raise SoundsException(f"Request failed: {e}") from e

    async def get_json_response(
        self,
        url: URLs,
        url_args: dict | None = None,
        **kwargs,
    ) -> dict:
        """Gets JSON response from an endpoint."""
        # built_url = build_url(url=url, url_args=url_args)

        if not self.mock_session:
            resp = await self.make_request(
                method="GET", url=url, url_args=url_args, **kwargs
            )
            json_resp = await resp.json()
            _raise_for_api_errors(json_resp)
            return json_resp
        else:
            try:
                json_file = os.path.join(FIXTURES_FOLDER, url.name + ".json")
                async with aiofiles.open(json_file) as file_reader:
                    return json.loads(await file_reader.read())
            except KeyError:
                raise InvalidArgumentsError(f"No matching fixture for {url}")

    async def get_html_response(
        self,
        url: URLs | str,
        url_args: dict | None = None,
        method: str = "GET",
        **kwargs,
    ) -> str:
        """Gets raw text/HTML response."""
        built_url = build_url(url=url, url_args=url_args)
        try:
            resp = await self.make_request(method, built_url, **kwargs)
        except aiohttp.ClientResponseError as e:
            if e.status == 401:
                raise UnauthorisedError(e) from e
            raise APIResponseError(f"Request failed: {e}") from e
        return await resp.text()

    def set_reauth_handler(self, call: Callable):
        self.reauth_handler = call
