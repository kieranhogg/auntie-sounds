import json
import logging
import os
import re
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
    from sounds.client import SoundsClient

logger = logging.getLogger(__name__)


async def _build_headers(referer: str | None = None) -> dict:
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


class RequestManager:
    def __init__(
        self,
        client: SoundsClient,
        username: str | None = None,
        password: str | None = None,
    ):
        self._client = client
        self.username = username
        self.password = password

    async def run(self, call):
        """Ensures user is logged in before running `call`."""
        try:
            logger.debug(f"Running {call}")
            return await call()
        except UnauthorisedError:
            logger.debug("Unauthorised when accessing an authenticated endpoint.")

            if not self.username or not self.password:
                logger.error("No username and/or password provided.")
                raise UnauthorisedError("No username and/or password provided.")

            if self._client.cookie_store.has_session_cookie:
                logger.debug("Cookie present, renewing session...")
                try:
                    await self._client.auth.renew_session()
                    return await call()
                except UnauthorisedError:
                    logger.error("Session renewal failed, trying full login...")

            await self._client.auth.login(
                username=self.username, password=self.password
            )
            logger.info("Logged in.")
            return await call()

    async def make_request(
        self,
        method: Literal["GET", "POST"],
        url: URLs | str,
        login_required: bool = False,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Makes an HTTP request using the shared session, applying defaults
        and handling connection-level errors. Also ensures auth, if needed."""
        kwargs.setdefault("timeout", self._client.timeout)
        kwargs.setdefault("ssl", True)
        kwargs.setdefault("allow_redirects", True)
        kwargs.setdefault("headers", await _build_headers())

        # If we have a endpoint, we can check if it's an authenticated one
        if isinstance(url, URLs):
            login_required = url.login_required
        url = build_url(url)
        logger.debug(f"Making HTTP {method} request to {url}")
        try:
            if login_required:
                resp = await self.run(
                    partial(
                        self._client._session.request, method=method, url=url, **kwargs
                    )
                )
            else:
                resp = await self._client._session.request(method, url, **kwargs)
            logger.debug(f"HTTP {method} {url} - Status {resp.status}")
            if resp.status == 401:
                raise UnauthorisedError(resp.reason)
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

    @staticmethod
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

    async def get_json_response(
        self,
        url: URLs,
        url_args: dict | None = None,
        **kwargs,
    ) -> dict:
        """Gets JSON response from an endpoint."""
        built_url = build_url(url=url, url_args=url_args)

        if self._client.mock_session and built_url:
            try:
                json_file = os.path.join(FIXTURES_FOLDER, url.name + ".json")
                async with aiofiles.open(json_file) as file_reader:
                    return json.loads(await file_reader.read())
            except KeyError:
                raise InvalidArgumentsError(f"No matching fixture for {built_url}")

        resp = await self.make_request(
            method="GET", url=built_url, login_required=url.login_required, **kwargs
        )
        json_resp = await resp.json()
        self._raise_for_api_errors(json_resp)
        return json_resp

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
