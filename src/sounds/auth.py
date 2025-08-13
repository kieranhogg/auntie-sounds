from functools import wraps
import os
from typing import Literal, Optional
from aiohttp import ClientResponse
from bs4 import BeautifulSoup

from yarl import URL

from . import constants
from .base import Base
from .constants import COOKIE_ID, VERBOSE_LOG_LEVEL, URLs
from .exceptions import LoginFailedError, UnauthorisedError

# Some common auth errors to check for
GENERIC_ERRORS = [
    "Sorry, you can't access this page.",
    "We're trying to fix it as soon as possible. Please try again later.",
    "Sorry, it looks like something's not working right now",
    "Looks like something went wrong. Please try again.",
    "Sorry, it looks like something's not working right now",
    "Sorry, we couldn't find the page you were looking for.",
    "Please try again in a few minutes.",
    "Sorry, it looks like something's not working right now. Please try again in a few minutes.",
]
EMAIL_ERRORS = [
    (
        "We don't recognise that email or username. You can try again or",
        "We don't recognise that email or username. You can try again or register for an account",
    ),
] + GENERIC_ERRORS
LOGIN_ERRORS = [
    (
        "That password isn't right. You can try again or",
        "That password isn't right. You can try again or <a>create a new password</a>",
    ),
    "Sorry, your account is locked",
    "We're doing some technical checks, which means you can't sign in or register for a BBC account right now.",
    "We just need to check it's really you before you access your settings.",
    "Failed to sign in with those details, please try again.",
    "Sorry, we can't find an account with that email address.",
    "We don't recognise that email or username. Please try again.",
    "Uh oh, that password doesn't match that account. Please try again.",
    "An unknown error has occurred.",
] + GENERIC_ERRORS


def login_required(method):
    @wraps(method)
    async def _impl(self, *method_args, **method_kwargs):
        self.logger.debug("@login_required")
        # Currently a bit of a hack until I can work out why sessions are expiring before the cookies
        if self.auth.is_logged_in:
            self.logger.debug("Logged in")
            try:
                method_output = await method(self, *method_args, **method_kwargs)
                self.logger.debug(f"Ran method {method}")
            except UnauthorisedError:
                self.logger.debug("Hit error")
                self.renew_session()
                self.authenticate(self.username, self.password)
                method_output = await method(self, *method_args, **method_kwargs)
                self.logger.debug("Rewned session and ran method")
        return method_output

    return _impl


class AuthService(Base):
    COOKIE_FILE = "./.sounds_jar"

    def __init__(self, *args, **kwargs):
        self.user_info = None
        self.debug_login = False
        if "debug_login" in kwargs:
            self.debug_login = kwargs.pop("debug_login")
        super().__init__(**kwargs)

        if self.debug_login:
            # Can't move this to the above conditional as self.logger not initialised yet
            self.logger.info("Saving login pages to file as requested")

        try:
            self._session._cookie_jar.load(self.COOKIE_FILE)  # type: ignore
            # self._session.cookie_jar.update_cookies(open(self.COOKIE_FILE, "r").read())
        except FileNotFoundError:
            pass

    @property
    def is_logged_in(self) -> bool:
        """Checks if we have a valid session"""
        return COOKIE_ID in self._session._cookie_jar.filter_cookies(
            URL(URLs.COOKIE_URL)
        )

    @property
    async def is_uk_listener(self):
        if not self.user_info:
            self.user_info = await self._get_json(URLs.USER_INFO)
        return self.user_info["X-Ip_is_uk_combined"] == "yes"

    async def _build_headers(self, referer: Optional[str] = None) -> dict:
        """Builds the standard headers to send when logging in"""
        base_headers = {
            "Accept-Language": "en-GB,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "Origin": URLs.LOGIN_BASE,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Cache-Control": "max-age=0",
        }
        if referer:
            base_headers["Referer"] = referer
        return base_headers

    async def authenticate(self, username: str, password: str) -> bool:
        """Signs into BBC Sounds"""
        self.username = username
        self.password = password
        if self.is_logged_in:
            self.logger.info("Existing session found, reusing")
            await self.renew_session()
            return True

        username_url = await self._get_login_form()
        password_url = await self._submit_username(url=username_url, username=username)
        await self._do_login(
            url=password_url,
            username=username,
            password=password,
            referrer_url=username_url,
        )
        return self.is_logged_in

    async def _get_form_action(self, html: str) -> Optional[str]:
        self.logger.log(VERBOSE_LOG_LEVEL, "_get_form_action()")

        """Finds the target of a form action from HTML markup"""
        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form")
        if form:
            self.logger.debug("Found form successfully")
            return str(form.get("action"))  # type: ignore
        else:
            return None

    async def _get_login_form(self) -> str:
        self.logger.log(VERBOSE_LOG_LEVEL, "_get_login_form()")

        # Get the initial login page form target
        html_contents = await self._get_html(
            URLs.LOGIN_START,
            "GET",
            headers=await self._build_headers(),
        )
        self._save_file_if_needed(html_contents, "login_form.html")

        username_form_action = await self._get_form_action(html_contents)
        self.logger.debug(f"Found username form target: {username_form_action}")
        if not username_form_action:
            raise RuntimeError("Could not find BBC sign-in form URL")
        url = f"{URLs.LOGIN_BASE}{username_form_action}"
        return url

    async def _submit_username(self, url: str, username: str) -> str:
        self.logger.log(VERBOSE_LOG_LEVEL, "_submit_username()")

        """Post username to get to the next login step"""
        html_contents = await self._get_html(
            url,
            "POST",
            data={"username": username},
            headers=await self._build_headers(referer=URLs.LOGIN_START),
        )
        self._save_file_if_needed(html_contents, "password_form.html")
        found_error = self._check_for_login_errors(html_contents, stage="login")
        if found_error:
            raise LoginFailedError(f"BBC sign-in failed: {found_error}")

        # Grab the form target for the password page
        password_form_action = await self._get_form_action(html_contents)
        if not password_form_action:
            raise LoginFailedError("Could not find BBC password form URL")
        password_url = f"{URLs.LOGIN_BASE}{password_form_action}"
        self.logger.debug(f"Found password form target: {password_url}")

        return password_url

    async def _do_login(
        self, url: str, username: str, password: str, referrer_url: str
    ) -> None:
        self.logger.log(VERBOSE_LOG_LEVEL, "_do_login()")
        """Send both username and password to authenticate."""
        resp = await self._make_request(
            "POST",
            url,
            data={"username": username, "password": password},
            headers=await self._build_headers(referer=referrer_url),
            allow_redirects=True,
        )
        response_text = await resp.text()
        self._save_file_if_needed(response_text, "login_response.html")

        if resp.status != 200 or not self.is_logged_in:
            found_error = self._check_for_login_errors(await resp.text(), stage="login")
            error_string = f"BBC sign-in failed: {resp.status}"
            if found_error:
                error_string += f" {found_error}"
                self.logger.error(error_string)
            raise LoginFailedError(error_string)
        else:
            self.save_cookies_to_disk()
            self.logger.info("Authenticated succesfully")

    def _save_file_if_needed(self, html: str | bytes, filename: str):
        if self.debug_login:
            with open(filename, "w") as page:
                html = BeautifulSoup(html, features="html.parser").prettify()
                page.write(str(html))

    def save_cookies_to_disk(self):
        return self._session._cookie_jar.save(self.COOKIE_FILE)
        # return open(self.COOKIE_FILE, "w").write(self._session.cookie_jar.filter_cookies(constants.COOKIE_ID))  # type: ignore

    def _check_for_login_errors(
        self, html: str, stage: Literal["email"] | Literal["login"]
    ):
        """See if we can extract a meaningful error from the HTML."""
        return None
        html_content = BeautifulSoup(html, features="html.parser").find("div").text
        if stage == "email":
            errors = EMAIL_ERRORS
        else:
            errors = LOGIN_ERRORS

        for error in errors:
            if type(error) is tuple and error[0] in html_content:
                return error[1]
            elif type(error) is str and error in html:
                return error
        return None

    async def renew_session(self):
        await self._make_request("GET", constants.SignedInURLs.RENEW_SESSION)

    def logout(self):
        try:
            os.remove(self.COOKIE_FILE)
            self._session._cookie_jar.clear()
        except Exception:
            pass
