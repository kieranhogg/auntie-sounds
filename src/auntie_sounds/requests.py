import logging
import re
from collections.abc import Callable
from functools import partial
from typing import Literal

import aiohttp
from aiohttp import ClientConnectionError

from auntie_sounds.endpoints import Endpoints, URLs
from auntie_sounds.exceptions import (
    APIResponseError,
    InvalidArgumentsError,
    NetworkError,
    NotFoundError,
    SoundsException,
    SoundsHttpException,
    UnauthorisedError,
)

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10)
DEFAULT_LIMIT = 100
URL_BASE = "https://rms.api.bbc.co.uk"

# Specific status codes we care enough to map to specific exceptions
_STATUS_ERRORS: dict[int, type[SoundsHttpException]] = {
    401: UnauthorisedError,
    404: NotFoundError,
}


async def _error_message(resp: aiohttp.ClientResponse) -> str:
    """Attempt to get error message(s), if any."""
    try:
        body = await resp.json(content_type=None)
        return body["errors"][0]["message"]
    except (
        ValueError,
        KeyError,
        IndexError,
        TypeError,
        aiohttp.ClientError,
        TimeoutError,
    ):
        return resp.reason or str(resp.status)


def build_url(
    url: Endpoints | URLs | str,
    url_args: dict | None = None,
) -> str:
    default_args = {"limit": DEFAULT_LIMIT}

    if isinstance(url, Endpoints):
        url_str = url.value
    else:
        url_str = url

    if not url_args:
        url_args = {}

    # /url/{param}/{thing}/ -> ["param", "thing"]
    pattern = re.compile(r"\{(.*?)}")
    parameters_required = re.findall(pattern, url_str)

    for keyword in parameters_required:
        if keyword not in url_args:
            if keyword in default_args:
                # We didn't receive an argument, but we have a default set so use that
                url_args[keyword] = default_args[keyword]
            else:
                raise InvalidArgumentsError(
                    f"{keyword} is a required parameter for the URL, but it is not in url_args."
                )
    if parameters_required and url_args:
        return (
            URL_BASE + url_str.format(**url_args)
            if "https://" not in url_str
            else url_str.format(**url_args)
        )
    return URL_BASE + url_str if "https://" not in url_str else url_str


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
    raise APIResponseError(message, status_code=code)


class RequestManager:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
        login_details_provided: bool = False,
        reauth_handler: Callable | None = None,
    ):
        self._session: aiohttp.ClientSession = session
        self.timeout: aiohttp.ClientTimeout = timeout
        self.login_details_provided: bool = login_details_provided
        self.reauth_handler: Callable | None = reauth_handler

    async def run(self, call):
        """Runs `call`, falling back to `reauth_handler`, if set, to retry auth.

        `reauth_handler` (just `AuthService.retry_with_reauth` at present) owns
        the authenticated endpoint lifecycle: trying `call` > checking
        credentials > renewing/logging in, and retrying. `run()` just passes
        it over.
        """

        if self.reauth_handler:
            return await self.reauth_handler(call)
        return await call()

    async def _request_or_raise(self, method, url, **kwargs) -> aiohttp.ClientResponse:
        """Make a HTTP request, converting any 401s errors into UnauthorisedError

        run() checks against authenticated endpoints, renewing a session if required.
        To do this we need intercept 401s and raise an UnauthorisedError so it can
        be retried
        """
        try:
            resp = await self._session.request(method, url, **kwargs)
            logger.debug("Final URL requested: %s", resp.url)
        except ClientConnectionError as e:
            raise NetworkError(str(e)) from e
        if resp.status >= 400:
            message = await _error_message(resp)
            resp.release()
            logger.debug("HTTP %s from %s: %s", resp.status, resp.url, message)
            raise _STATUS_ERRORS.get(resp.status, APIResponseError)(
                message, status_code=resp.status
            )
        return resp

    async def make_request(
        self,
        method: Literal["GET", "POST"],
        url: Endpoints | URLs | str,
        url_args: dict | None = None,
        login_required: bool = False,
        offset: int | None = None,
        limit: int | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Makes an HTTP request using the shared session, applying defaults
        and handling connection-level errors. Also ensures auth, if needed."""
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("ssl", True)
        kwargs.setdefault("allow_redirects", True)
        # kwargs.setdefault("headers", build_headers())

        params = dict(kwargs.get("params") or {})

        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit
        if params:
            kwargs["params"] = params

        logger.debug("Preparing to request %s", url)
        if isinstance(url, Endpoints):
            # If we have a endpoint, we can check if it's an authenticated one
            login_required = url.login_required
            url = build_url(url=url, url_args=url_args)
        elif isinstance(url, URLs):
            url = build_url(url=url, url_args=url_args)
        else:
            if url in Endpoints:
                logger.warning(
                    "URL used a string found in Endpoints enum, use that directly instead."
                )
            elif url in URLs:
                logger.warning(
                    "URL used a string found in URLs enum, use that directly instead."
                )
        logger.debug(
            "Making HTTP %s request to %s%s",
            method,
            url,
            f" with params {params}" if params else "",
        )
        try:
            if login_required:
                resp = await self.run(
                    partial(self._request_or_raise, method=method, url=url, **kwargs)
                )
            else:
                resp = await self._request_or_raise(method, url, **kwargs)
            logger.debug(f"HTTP {method} {url} - Status {resp.status}")
            return resp
        except aiohttp.ClientConnectorDNSError as e:
            logger.error(f"HTTP request failed: {method} {url} - {e}")
            raise NetworkError(f"Connection failed: {e}") from e
        except TimeoutError as e:
            # Total timeouts raise a bare TimeoutError, not a ClientError
            logger.error(f"HTTP request timed out: {method} {url}")
            raise NetworkError(f"Request timed out: {method} {url}") from e
        except aiohttp.ContentTypeError as e:
            logger.error(f"HTTP request failed: {method} {url} - {e}")
            raise SoundsException(f"Invalid response type: {e}") from e
        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed: {method} {url} - {e}")
            raise SoundsException(f"Request failed: {e}") from e

    async def get_json_response(
        self,
        url: Endpoints | URLs | str,
        url_args: dict | None = None,
        fetch_all_items: bool = False,
        max_items: int | None = None,
        page_size: int = DEFAULT_LIMIT,
        **kwargs,
    ) -> dict:
        """Gets JSON response from an endpoint."""
        if fetch_all_items and max_items is not None:
            raise InvalidArgumentsError("Pass fetch_all_items or max_items, not both")

        paging = fetch_all_items or max_items is not None
        # Only send `limit` when paging, so callers' own params (and endpoints
        # that don't take a limit) are left alone.
        first_limit = min(page_size, max_items) if max_items is not None else page_size

        resp = await self.make_request(
            method="GET",
            url=url,
            url_args=url_args,
            limit=first_limit if paging else None,
            **kwargs,
        )
        first_page: dict = await self._read_json(resp, url)

        if not paging or "total" not in first_page:
            return first_page

        key_to_build = next((k for k in ("data", "results") if k in first_page), None)
        if key_to_build is None:
            logger.debug("Paged response from %s has no data/results key", url)
            return first_page

        logger.debug("Continuing to get paged response, if needed")
        total = int(first_page["total"])
        items: list = list(first_page.get(key_to_build) or [])

        target = total if max_items is None else min(total, max_items)
        offset = int(first_page.get("offset") or 0) + len(items)
        server_page_size = int(first_page.get("limit") or page_size)

        while len(items) < target:
            logger.debug(
                "Fetching page at offset %s (%s/%s)", offset, len(items), target
            )
            resp = await self.make_request(
                method="GET",
                url=url,
                url_args=url_args,
                offset=offset,
                limit=server_page_size,
                **kwargs,
            )
            page_items = (await self._read_json(resp, url)).get(key_to_build) or []
            if not page_items:
                break

            items.extend(page_items)
            offset += len(page_items)

        first_page[key_to_build] = items[:target]
        return first_page

    async def get_html_response(
        self,
        url: Endpoints | URLs | str,
        url_args: dict | None = None,
        method: Literal["GET", "POST"] = "GET",
        **kwargs,
    ) -> str:
        """Gets raw text/HTML response."""
        built_url = build_url(url=url, url_args=url_args)
        resp = await self.make_request(method, built_url, **kwargs)
        return await resp.text()

    def set_reauth_handler(self, call: Callable):
        self.reauth_handler = call

    async def _read_json(self, resp, url) -> dict:
        try:
            body: dict = await resp.json()
        except aiohttp.ContentTypeError as e:
            raise APIResponseError(f"{e.message}. URL: {url}") from e
        _raise_for_api_errors(body)
        return body
