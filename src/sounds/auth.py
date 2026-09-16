"""AuthService handles authentication with BBC Sounds.

There is no public or private API available for authentication, which is the exception. This service therefore
implements logging in by logging in via HTTP requests, which unfortunately makes this process brittle and
highly-coupled to the URLs and HTML content of the pages requested.
"""

import logging
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from sounds import VERBOSE_LOG_LEVEL, endpoints
from sounds.cookies import CookieStore
from sounds.endpoints import URLs
from sounds.exceptions import (
    LoginFailedError,
    MultipleObjectsFound,
    NotFoundError,
    UnauthorisedError,
)
from sounds.requests import RequestManager, build_headers, build_url
from sounds.utils import _get_data_dir

logger = logging.getLogger(__name__)


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
    PASSWORD_NUMBER_SYMBOL_ERROR_MSG = "Sorry, that password isn't valid. Please include something that isn't a letter."

    def __init__(
        self,
        requests: RequestManager,
        cookie_store: CookieStore,
        username: str | None = None,
        password: str | None = None,
        mock_session: bool = False,
        debug_login: bool = False,
        on_login_success=None,
    ):
        self.user_info = None
        self.requests = requests
        self.cookie_store = cookie_store
        self.username = username
        self.password = password
        self.mock_session = mock_session
        self.debug_login = debug_login
        self._on_login_success = on_login_success

        if self.mock_session:
            return
        if self.debug_login:
            logger.info("Saving login pages to file as requested")

    async def login(self, username: str, password: str) -> bool:
        """

        :raises LoginFailedError: if we didn't get to the second part of the login process
        """
        username_url = await self._get_login_form()
        password_url = await self._submit_username(url=username_url, username=username)
        if password_url == username_url:
            error = "Login did not succeed to stage 2 successfully"
            logger.error(error)
            raise LoginFailedError(error)
        ok = await self._do_login(
            url=password_url,
            username=username,
            password=password,
            referrer_url=username_url,
        )
        return ok

    async def retry_with_reauth(self, call):
        """Runs `call`, transparently renewing/re-logging-in on a 401.

        This can be used to handle authentication failures encountered in services.
        E.g. RequestManager uses this as its login_required retry hook."""
        try:
            return await call()
        except UnauthorisedError:
            if not self.username or not self.password:
                raise UnauthorisedError("No username and/or password provided.")
            if self.cookie_store.has_session_cookie:
                try:
                    await self.renew_session()
                    return await call()
                except UnauthorisedError:
                    logger.error("Session renewal failed, trying full login...")
            await self.login(username=self.username, password=self.password)
            return await call()

    async def renew_session(self) -> bool:
        """Renew a session which has expired, but user is logged in."""
        try:
            url = build_url(url=endpoints.URLs.RENEW_SESSION)
            await self.requests.make_request("GET", url)
            return True
        except UnauthorisedError:
            logger.error("Failed to renew session")
            return False

    async def _get_login_form(self) -> str:
        """
        :raises LoginFailedError: if the login page, or form, cannot be located
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
        while request.status in [301, 302, 303, 307, 308]:
            logger.debug(
                f"Redirected with status {request.status} to {request.headers.get('Location')}"
            )
            location = request.headers.get("Location")
            if not location:
                break

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
        return URLs.LOGIN_BASE.value + username_form_action

    async def _submit_username(self, url: str, username: str) -> str:
        """Post username to get to the next login step"""
        logger.debug("Submitting username")
        data = {"username": username}
        html_contents = await self.requests.get_html_response(
            url=url,
            method="POST",
            data=data,
            headers=build_headers(referer=URLs.LOGIN_START.value),
        )
        soup = BeautifulSoup(html_contents, "html.parser")
        error_el = soup.select_one(f".{self.ERROR_CLASS}")
        if error_el:
            logger.error(f"Login failed: {error_el.text}")
            raise LoginFailedError(error_el.text)
        self._save_file_if_needed(html_contents, "password_form.html")

        # Grab the form target for the password page
        password_form_action = _get_form_action(html_contents)
        if password_form_action is None:
            raise LoginFailedError("Could not find password form URL")
        password_url = URLs.LOGIN_BASE.value + password_form_action
        logger.debug(f"Found password form target: {password_url}")
        return password_url

    async def _do_login(
        self,
        url: str,
        username: str,
        password: str,
        referrer_url: str,
    ) -> bool:
        """Send both username and password to authenticate.

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
            raise LoginFailedError(error.text)
        self._save_file_if_needed(response_text, "login_response.html")

        if not resp.ok:
            error_string = f"BBC sign-in failed: {resp.status}"
            logger.error(error_string)
            raise LoginFailedError(error_string)
        else:
            if self._on_login_success:
                self._on_login_success()
            logger.debug("Authenticated successfully")
            return True

    def _save_file_if_needed(self, html: str | bytes, filename: str):
        if self.debug_login:
            with open(Path(_get_data_dir(), filename), "w") as page:
                html = BeautifulSoup(html, features="html.parser").prettify()
                page.write(str(html))
