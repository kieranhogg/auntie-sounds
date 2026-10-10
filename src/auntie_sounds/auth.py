"""AuthService handles authentication with BBC Sounds.

There is no public or private API available for authentication, which is the exception.
This service therefore implements logging in by logging in via HTTP requests, which
unfortunately makes this process brittle and highly-coupled to the URLs and HTML content
of the pages requested.
"""

import asyncio
import logging
import math
import time
from pathlib import Path

import aiohttp
from bs4 import BeautifulSoup, Tag
from yarl import URL

from auntie_sounds import VERBOSE_LOG_LEVEL
from auntie_sounds.cookies import CookieStore
from auntie_sounds.endpoints import URLs
from auntie_sounds.exceptions import (
    CredentialsRejectedError,
    InvalidArgumentsError,
    LoginFailedError,
    MultipleObjectsFound,
    NetworkError,
    NotFoundError,
    SoundsException,
    UnauthorisedError,
)
from auntie_sounds.requests import RequestManager, build_headers
from auntie_sounds.utils import _get_data_dir

logger = logging.getLogger(__name__)

# Errors a login or renewal attempt can raise; anything else is a bug and propagates
_AUTH_ERRORS = (SoundsException, aiohttp.ClientError, TimeoutError)


def _get_form_action(html: str) -> str:
    """Finds the target of a form action from HTML markup.

    :raises NotFoundError if a valid form isn't found
    :raises MultipleObjectsFound if more than one valid form is found
    """

    soup = BeautifulSoup(html, "html.parser")
    forms = soup.find_all("form", {"action": True})
    logger.debug(forms)
    number_of_forms = len(forms)

    # No forms on page at all
    if number_of_forms == 0:
        raise NotFoundError("No forms found on page")

    # Multiple forms found, we're going to find the first valid one
    if number_of_forms > 1:
        raise MultipleObjectsFound

    form = soup.find("form", {"action": True})
    if not (form or isinstance(form, Tag)):
        raise NotFoundError("No valid form found on page")

    action = str(form.get("action"))
    if action == "":
        raise NotFoundError("No valid form found on page")
    return action


class AuthService:
    """Service to handle authentication with BBC Sounds."""

    ERROR_CLASS = "sb-form-message--error"
    EMAIL_ERROR_MSG = "We don’t recognise that email or username. You can try again or register for an account"
    PASSWORD_ERROR_MSG = (
        "That password isn’t right. You can try again or reset your password"
    )
    PASSWORD_LENGTH_MSG = (
        "Sorry, that password is too short. It needs to be eight characters or more."
    )
    PASSWORD_TOO_EASY_ERROR_MSG = (
        "Sorry, that password isn't valid. Make sure it's hard to guess."
    )
    # Minimum time after a successful full login before another automatic
    # re-authentication; a 401 inside this window is treated as not auth-related.
    MIN_LOGIN_INTERVAL = 60.0
    # Backoff after a transient login failure (network, page structure)
    FAILURE_BACKOFF_INITIAL = 30.0
    FAILURE_BACKOFF_MAX = 900.0

    PASSWORD_NUMBER_SYMBOL_ERROR_MSG = "Sorry, that password isn't valid. Please include something that isn't a letter."

    def __init__(
        self,
        requests: RequestManager,
        cookie_store: CookieStore,
        username: str | None = None,
        password: str | None = None,
        debug_login: bool = False,
        on_login_success=None,
    ):
        self.user_info = None
        self.requests = requests
        self.cookie_store = cookie_store
        self.username = username
        self.password = password
        self.debug_login = debug_login
        self._on_login_success = on_login_success
        self._reauth_lock = asyncio.Lock()
        self._auth_generation = 0
        self._login_generation = -1
        self._clock = time.monotonic
        self._last_login: float | None = None
        # Last login failure, the credentials it was for, and when to allow a retry
        self._failure: SoundsException | None = None
        self._failure_credentials: tuple[str | None, str | None] | None = None
        self._blocked_until = 0.0
        self._backoff = self.FAILURE_BACKOFF_INITIAL

        if self.debug_login:
            logger.info("Saving login pages to file as requested")

    async def login(self, username: str, password: str) -> bool:
        """
        Try to do a full login via the BBC website, which is a two-step process.

        :raises LoginFailedError: if a failure is encountered
        """
        self.cookie_store.clear()

        username_url = await self._get_login_form()
        password_url = await self._submit_username(url=username_url, username=username)

        if password_url == username_url:
            error = "Login did not succeed to stage 2 successfully"
            logger.error(error)
            raise LoginFailedError(error)

        logged_in = await self._do_login(
            url=password_url,
            username=username,
            password=password,
            referrer_url=username_url,
        )

        if not (logged_in and self.cookie_store.is_signed_in):
            error = "Login failed at final stage attempting to log in."
            logger.error(error)
            raise LoginFailedError(error)

        if self._on_login_success:
            try:
                await self._on_login_success()
            except Exception:
                # The session is valid so don't fail at this stage if there is anything
                # wrong with _on_login_success
                logger.warning("on_login_success callback failed", exc_info=True)

        return True

    async def retry_with_reauth(self, call):
        """Runs `call`, renewing the session or logging in on a 401, then retrying.

        Escalates at most once: renewal, then full login. A 401 after a full login
        is raised. Used as RequestManager's reauth handler for login_required endpoints.

        :raises InvalidArgumentsError: if a login is needed but no credentials are set
        """
        seen = self._auth_generation
        if self.cookie_store.is_signed_in and not self.cookie_store.has_access_token:
            seen = await self._reauthenticate(seen)
        try:
            return await call()
        except UnauthorisedError:
            pass

        generation = await self._reauthenticate(seen)
        try:
            return await call()
        except UnauthorisedError:
            if self._login_generation == generation:
                raise

        await self._reauthenticate(generation, force_login=True)
        return await call()

    async def authenticate(self) -> None:
        """Ensure a usable session: renew if a session cookie exists, else log in.

        Shares the re-authentication lock, so it's safe to call alongside requests
        already being retried.

        :raises InvalidArgumentsError: if a login is needed but no credentials are set
        :raises LoginFailedError: if logging in fails
        """
        if self.cookie_store.has_access_token:
            return
        await self._reauthenticate(self._auth_generation, explicit=True)

    async def renew_session(self) -> bool:
        """Renew a session which has expired, but user is logged in.

        Returns True if the renewal request succeeded, False otherwise. Success
        doesn't guarantee the session is valid; retry_with_reauth escalates to
        a full login if the next request is still unauthorised."""
        try:
            await self.requests.make_request("GET", URLs.RENEW_SESSION)
        except _AUTH_ERRORS as e:
            logger.warning("Failed to renew session: %s", e)
            return False
        return self.cookie_store.has_access_token

    async def _reauthenticate(
        self, seen: int, force_login: bool = False, explicit: bool = False
    ) -> int:
        """Renew or log in once on behalf of all callers that saw generation `seen`.

        Without this, concurrent requests invalidated together would each
        re-authenticate independently.

        Automatic (non-explicit) attempts are limited so a misbehaving endpoint
        or bad credentials can't cause repeated logins:
        - after a login failure, attempts raise that failure until a backoff
          expires; a credential rejection blocks until the credentials change
        - within MIN_LOGIN_INTERVAL of a successful login, a 401 is raised
          rather than renewing or logging in again
        """
        async with self._reauth_lock:
            self._raise_if_blocked(explicit)
            if self._auth_generation != seen:
                # someone else has already re-authenticated
                return self._auth_generation
            if (
                not explicit
                and self._last_login is not None
                and self._clock() - self._last_login < self.MIN_LOGIN_INTERVAL
            ):
                raise UnauthorisedError(
                    "Still unauthorised shortly after logging in; not re-authenticating"
                )
            if not force_login and self.cookie_store.is_signed_in:
                if await self.renew_session():
                    self._auth_generation += 1
                    self.cookie_store.save()
                    return self._auth_generation
                logger.warning("Session renewal failed, trying full login...")
            if not (self.username and self.password):
                raise InvalidArgumentsError("Login required but no credentials set")
            try:
                await self.login(username=self.username, password=self.password)
            except _AUTH_ERRORS as e:
                failure = e if isinstance(e, SoundsException) else NetworkError(repr(e))
                self._record_failure(failure)
                if failure is e:
                    raise
                raise failure from e
            self._clear_failure()
            self._last_login = self._clock()
            self._auth_generation += 1
            self._login_generation = self._auth_generation
            return self._auth_generation

    def _record_failure(self, failure: SoundsException) -> None:
        self._failure = failure
        self._failure_credentials = (self.username, self.password)
        if isinstance(failure, CredentialsRejectedError):
            self._blocked_until = math.inf
            logger.error(
                "Credentials rejected. Automatic re-authentication is paused until "
                "they change or login() is called explicitly"
            )
            return
        self._blocked_until = self._clock() + self._backoff
        logger.warning("Login failed; retrying in %.0fs", self._backoff)
        self._backoff = min(self._backoff * 2, self.FAILURE_BACKOFF_MAX)

    def _clear_failure(self) -> None:
        self._failure = None
        self._failure_credentials = None
        self._blocked_until = 0.0
        self._backoff = self.FAILURE_BACKOFF_INITIAL

    def _raise_if_blocked(self, explicit: bool) -> None:
        """Re-raise the last login failure while retries are blocked."""
        if self._failure is None:
            return
        if explicit or self._failure_credentials != (self.username, self.password):
            self._clear_failure()
            return
        if self._clock() >= self._blocked_until:
            return
        raise type(self._failure)(str(self._failure)) from self._failure

    async def _get_login_form(self, max_redirects=5) -> str:
        """Get the initial form to log in with.

        There are a few conditions we need to handle with in this process, we can't
        just rely on getting a fixed URL to log in with.

        :raises LoginFailedError: if the login page, or suitable form, cannot be located
        """
        logger.debug("Getting initial login page")

        # Get the initial login page form target
        request = await self.requests.make_request(
            method="GET",
            url=URLs.LOGIN_START,
            headers=build_headers(),
            allow_redirects=False,
        )

        # Intercept the redirection flow
        redirects = 0
        while request.status in [301, 302, 303, 307, 308]:
            if redirects == max_redirects:
                msg = (
                    f"Hit the maximum number of redirects allowed ({max_redirects}) "
                    "when fetching the login form. Either it couldn't be found, or "
                    "consider increasing `max_redirects`."
                )
                logger.error(msg)
                raise LoginFailedError(msg)
            logger.debug(
                f"Redirected with status {request.status} to {request.headers.get('Location')}"
            )
            location = request.headers.get("Location")
            if not location:
                break
            # Location may be relative; resolve against the URL that sent it
            location = str(request.url.join(URL(location)))

            # Ensure we don't get the magic link signin page
            if "/identifier/signin?" in location:
                logger.debug("Redirected to magic link signin page, removing")
                location = location.replace("/identifier/signin?", "?")

            request = await self.requests.make_request(
                "GET",
                url=location,
                headers=build_headers(),
                allow_redirects=False,
            )
            redirects += 1

        if not request.ok:
            error = "Failed to get initial login page"
            logger.error(error)
            raise LoginFailedError(error)

        html_contents = await request.text()

        self._save_file_if_needed(html_contents, "login_form.html")

        try:
            username_form_action = _get_form_action(html_contents)
        except MultipleObjectsFound as e:
            error_msg = "Didn't get the username form successfully: multiple valid forms found on page."
            logger.error(error_msg)
            raise LoginFailedError(error_msg) from e
        except NotFoundError as e:
            error_msg = "Didn't get the username form successfully: no valid form action found on page."
            logger.error(error_msg)
            raise LoginFailedError(error_msg) from e

        logger.debug(f"Found username form target: {username_form_action}")
        return URLs.LOGIN_BASE + username_form_action

    async def _submit_username(self, url: str, username: str) -> str:
        """Post username to get to the next login step.

        :raises LoginFailedError if the password (second stage) form isn't found."""
        logger.debug("Submitting username")
        data = {"username": username}
        html_contents = await self.requests.get_html_response(
            url=url,
            method="POST",
            data=data,
            headers=build_headers(referer=URLs.LOGIN_START),
        )
        soup = BeautifulSoup(html_contents, "html.parser")
        error_el = soup.select_one(f".{self.ERROR_CLASS}")
        if error_el:
            logger.error(f"Login failed: {error_el.text}")
            raise CredentialsRejectedError(error_el.text)
        self._save_file_if_needed(html_contents, "password_form.html")

        # Grab the form target for the password page
        password_form_action = _get_form_action(html_contents)
        if password_form_action is None:
            raise LoginFailedError("Could not find password form URL")
        password_url = URLs.LOGIN_BASE + password_form_action
        logger.debug(f"Found password form target: {password_url}")
        return password_url

    async def _do_login(
        self,
        url: str,
        username: str,
        password: str,
        referrer_url: str,
    ) -> bool:
        """Send both username and password to the user/pass form to authenticate.

        :raises LoginFailedError: if we find a recognised error message on the page
        """
        logger.debug("Logging in...")
        headers = build_headers(referer=referrer_url)
        data = {"username": username, "password": password}
        resp = await self.requests.make_request(
            method="POST",
            url=url,
            data=data,
            allow_redirects=True,
            headers=headers,
        )
        response_text = await resp.text()
        logger.log(VERBOSE_LOG_LEVEL, response_text)
        soup = BeautifulSoup(response_text, "html.parser")
        error = soup.find("div", attrs={"class": "sb-form-message--error"})
        if error:
            logger.error(f"Login failed: {error.text}")
            raise CredentialsRejectedError(error.text)
        self._save_file_if_needed(response_text, "login_response.html")

        if not resp.ok:
            error_string = f"BBC sign-in failed: {resp.status}"
            logger.error(error_string)
            raise LoginFailedError(error_string)
        else:
            logger.debug("Authenticated successfully")
            return True

    def _save_file_if_needed(self, html: str | bytes, filename: str):
        """Save the login pages to aid with debugging, if requested."""
        if self.debug_login:
            with open(Path(_get_data_dir(), filename), "w") as page:
                html = BeautifulSoup(html, features="html.parser").prettify()
                page.write(str(html))
