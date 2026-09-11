"""AuthService handles authentication with BBC Sounds.

There is no public or private API available for authentication, which is the exception. This service therefore
implements logging in by logging in via HTTP requests, which unfortunately makes this process brittle and
highly-coupled to the URLs and HTML content of the pages requested.
"""

import logging
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from sounds import constants
from sounds.base import Base
from sounds.constants import VERBOSE_LOG_LEVEL, URLs
from sounds.cookies import CookieStore
from sounds.exceptions import (
    LoginFailedError,
    MultipleObjectsFound,
    NotFoundError,
    UnauthorisedError,
)
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


class AuthService(Base):
    """Service to handle authentication with BBC Sounds."""

    ERROR_CLASS = "sb-form-message--error"
    EMAIL_ERROR_MSG = "We don’t recognise that email or username. You can try again or register for an account"
    PASSWORD_ERROR_MSG = (
        "That password isn’t right. You can try again or reset your password"
    )
    PASSWORD_LENGTH_MSG = (
        "Sorry, that password is too short. It needs to be eight characters or more."
    )
    PASSWORD_TOO_EASY_ERROR_MSG = "Sorry, that password isn't valid. Make sure it's hard to guess."
    PASSWORD_NUMBER_SYMBOL_ERROR_MSG = "Sorry, that password isn't valid. Please include something that isn't a letter."

    def __init__(
        self,
        cookie_store: CookieStore,
        on_login_success=None,
        debug_login=False,
        **kwargs,
    ):
        super().__init__(cookie_store=cookie_store, **kwargs)
        self.user_info = None
        self.debug_login = debug_login
        self._on_login_success = on_login_success
        self.debug_login = debug_login
        if kwargs.get("mock_session"):
            self.mock_session = True
            return

        if self.debug_login:
            # Can't move this to the above conditional as logger not initialised yet
            logger.info("Saving login pages to file as requested")

    async def _build_headers(self, referer: str | None = None) -> dict:
        """Builds the standard headers to send when logging in"""
        base_headers = {
            "Accept-Language": "en-GB,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "Origin": URLs.LOGIN_BASE.value,
            "Cache-Control": "max-age=0",
        }
        if referer:
            base_headers["Referer"] = referer
        return base_headers

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

    async def _get_login_form(self) -> str:
        """
        :raises LoginFailedError: if the login page, or form, cannot be located
        """
        logger.debug("Getting initial login page")

        # Get the initial login page form target
        request = await self._make_request(
            method="GET",
            url=URLs.LOGIN_START.value,
            headers=await self._build_headers(),
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

            request = await self._make_request(
                "GET",
                url=location,
                headers=await self._build_headers(),
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
        html_contents = await self._get_html(
            url=url,
            method="POST",
            data=data,
            headers=await self._build_headers(referer=URLs.LOGIN_START.value),
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
        headers = await self._build_headers(referer=referrer_url)
        data = {"username": username, "password": password}
        resp = await self._make_request(
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

    async def renew_session(self) -> bool:
        """Renew a session which has expired, but user is logged in."""
        try:
            url = self._build_url(url_template=constants.SignedInURLs.RENEW_SESSION)
            await self._make_request("GET", url)
            return True
        except UnauthorisedError:
            logger.error("Failed to renew session")
            return False
