import json
import logging
import os
import re
from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING, Literal

import aiofiles
import aiohttp

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
    url_str: str = url.value if isinstance(url, URLs) else url
    pattern = re.compile(r".*(\{.*}).*")
    parameters_required = re.findall(pattern, url_str)
    for keyword in parameters_required:
        keyword = keyword.replace("{", "").replace("}", "")
        if not url_args or keyword not in url_args:
            raise InvalidArgumentsError(
                f"{keyword} is a required parameter for the URL, but it is not in url_args."
            )
    if parameters_required and url_args:
        return url_str.format(**url_args)
    return url_str


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
        mock_data: bool = False,
        login_details_provided: bool = False,
        reauth_handler: Callable | None = None,
    ):
        self._session: ClientSession = session
        self.timeout: ClientTimeout = timeout
        self.mock_data: bool = mock_data
        self.login_details_provided: bool = login_details_provided
        self.reauth_handler: Callable | None = reauth_handler

    async def run(self, call):
        """Runs `call`, falling back to `reauth_handler`, if set, to retry auth.

        `reauth_handler` (just `AuthService.retry_with_reauth` at present) owns
        the authenticated endpoint lifecycle: trying `call` > checking
        credentials > renewing/logging in, and retrying. `run()` just passes
        it over.
        """

        logger.debug(f"Running {call}")
        if self.reauth_handler:
            logger.debug("Calling reauth_handler %s.", self.reauth_handler)
            return await self.reauth_handler(call)
        return await call()

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

        if not self.mock_data:
            resp = await self.make_request(
                method="GET", url=url, url_args=url_args, **kwargs
            )
            json_resp: dict = await resp.json()
            _raise_for_api_errors(json_resp)
            return json_resp
        else:
            try:
                json_file = os.path.join(FIXTURES_FOLDER, url.name + ".json")
                async with aiofiles.open(json_file) as file_reader:
                    return json.loads(await file_reader.read())
            except FileNotFoundError:
                raise InvalidArgumentsError(f"No matching fixture for {url}")

    async def get_html_response(
        self,
        url: URLs | str,
        url_args: dict | None = None,
        method: Literal["GET", "POST"] = "GET",
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
