import os
from functools import wraps
from pathlib import Path
from typing import Literal, Optional

from appdirs import AppDirs
from bs4 import BeautifulSoup
from yarl import URL

from . import constants
from .base import Base
from .constants import COOKIE_ID, URLs
from .exceptions import LoginFailedError, NotFoundError, UnauthorisedError

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


def _get_data_dir():
    dir = AppDirs(appname="auntie-sounds", version="1").user_data_dir
    Path(dir).mkdir(parents=True, exist_ok=True)
    return dir


COOKIE_FILE = Path(_get_data_dir(), "sounds_jar")


def login_required(method):
    """Use to catch expired sessions and reauthenticate before trying again."""

    @wraps(method)
    async def _impl(self, *method_args, **method_kwargs):
        self.logger.debug("@login_required")
        try:
            method_output = await method(self, *method_args, **method_kwargs)
            self.logger.debug(f"Ran method {method}")
        except UnauthorisedError:
            self.logger.debug("Hit error")
            if Path.exists(COOKIE_FILE):
                # We have a session, so renew
                await self.auth.renew_session()
                self.logger.debug(f"Logged in: {self.auth.is_logged_in}")
                method_output = await method(self, *method_args, **method_kwargs)
                self.logger.debug("Rewned session and ran method")
            else:
                raise
        return method_output

    return _impl


class AuthService(Base):
    def __init__(self, *args, **kwargs):
        self.user_info = None
        self.debug_login = False
        if "debug_login" in kwargs:
            self.debug_login = kwargs.pop("debug_login")
        if kwargs.get("mock_session"):
            self.mock_session = True
            return
        super().__init__(**kwargs)

        if self.debug_login:
            # Can't move this to the above conditional as self.logger not initialised yet
            self.logger.info("Saving login pages to file as requested")

        try:
            self._session._cookie_jar.load(COOKIE_FILE)  # type: ignore
        except FileNotFoundError:
            pass

    async def set_user_info(self) -> None:
        self.user_info = await self._get_json(url_template=URLs.USER_INFO)

    @property
    def is_logged_in(self) -> bool:
        """Checks if we have a valid session"""
        if self.mock_session:
            return True
        return (
            COOKIE_ID
            in self._session._cookie_jar.filter_cookies(URL(URLs.COOKIE_BASE.value))
        ) or (
            COOKIE_ID
            in self._session._cookie_jar.filter_cookies(
                URL(URLs.COOKIE_BASE_I18N.value)
            )
        )

    @property
    def listener_country(self) -> Optional[str]:
        """Return the listener's current country."""
        if self.user_info:
            return self.user_info.get("X-Country")
        return None

    @property
    def is_in_uk(self) -> bool:
        """Listener is in the UK."""
        if self.user_info:
            return self.user_info.get("X-Country") == "gb"
        return False

    @property
    def is_uk_listener(self) -> bool:
        """Listener has a UK-based account and is in the UK."""
        if self.user_info:
            return self.user_info["X-Ip_is_uk_combined"] == "yes"
        return False

    async def _build_headers(self, referer: Optional[str] = None) -> dict:
        """Builds the standard headers to send when logging in"""
        base_headers = {
            "Accept-Language": "en-GB,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "Origin": URLs.LOGIN_BASE.value,
            # "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Cache-Control": "max-age=0",
        }
        if referer:
            base_headers["Referer"] = referer
        return base_headers

    async def authenticate(self, username: str, password: str) -> bool:
        """Signs into BBC Sounds.

        :param username: The username or email address to sign in with
        :param password: The password to sign in with
        :return: True if successfully logged in, False otherwise
        :rtype: bool
        :raises LoginFailedError: If the login fails for any reason
        :raises UnauthorisedError: If the login is not authorised
        """
        if self.mock_session:
            return True

        await self.set_user_info()
        self.username = username
        self.password = password

        if self.is_logged_in:
            self.logger.info("Existing session found, reusing")
            await self.renew_session()
            return True

        if not self.is_uk_listener:
            self.logger.debug("Using international login flow")
            # initial_url = self._build_url(url_template=URLs.LOGIN_START_I18N)
            # initial_url = self._build_url(url_template=URLs.LOGIN_START_I18N)
            # self.logger.debug(f"Accessing international login start URL: {initial_url}")
            username_url = await self._get_login_form()
            password_url = await self._submit_username(
                url=username_url, username=username
            )
            await self._do_login(
                url=password_url,
                username=username,
                password=password,
                referrer_url=username_url,
            )
        else:
            username_url = await self._get_login_form()
            password_url = await self._submit_username(
                url=username_url, username=username
            )
            await self._do_login(
                url=password_url,
                username=username,
                password=password,
                referrer_url=username_url,
            )

        return self.is_logged_in

    async def _get_form_action(self, html: str) -> Optional[str]:
        """Finds the target of a form action from HTML markup"""
        soup = BeautifulSoup(html, "html.parser")
        forms = soup.find_all("form")
        if len(forms) > 1:
            self.logger.debug(
                f"Found {len(forms)} forms on page, returning the first one"
            )
        form = soup.find("form")
        if form is not None:
            form_action = form.get("action", None)
            if form_action is not None:
                return str(form_action)
        error = "Couldn't get form action"
        self.logger.error(error)
        self.logger.debug(forms)
        raise NotFoundError(error)

    async def _get_login_form(self, url=URLs.LOGIN_START.value) -> str:
        # Get the initial login page form target
        self.logger.debug(f"Getting initial login page: {url}")
        request = await self._make_request(
            method="GET",
            url=url,
            headers=await self._build_headers(),
            allow_redirects=False,
        )

        while request.status in (301, 302, 303, 307, 308):
            self.logger.debug(
                f"Redirected with status {request.status} to {request.headers.get('Location')}"
            )
            location = request.headers.get("Location")
            if not location:
                break

            # Ensure we don't get the magic link signin page
            if "/identifier/signin?" in location:
                self.logger.debug("Redirected to magic link signin page, removing")
                location = location.replace("/identifier/signin?", "?")

            request = await self._make_request(
                "GET",
                url=location,
                headers=await self._build_headers(),
                allow_redirects=False,
            )

        self.logger.debug("Response cookies from server:")
        for cookie in request.cookies.values():
            self.logger.debug(
                f"  Set-Cookie: {cookie.key}={cookie.value} (domain={cookie['domain']})"
            )

        # Log what's actually stored in the jar
        self.logger.debug("\nCookies in jar after GET:")
        for cookie in self._session.cookie_jar:
            self.logger.debug(
                f"  Stored: {cookie.key}={cookie.value} (domain={cookie['domain']})"
            )

        if not request.ok:
            error = f"Failed to get initial login page {url}"
            self.logger.error(error)
            raise LoginFailedError(error)

        html_contents = await request.text()

        # if len(request.history) > 0:
        #     history = ", ".join([str(h.url) for h in request.history])
        #     self.logger.debug(f"Login page request was redirected: {history}")
        #     url = str(request.history[-1].url)

        self._save_file_if_needed(html_contents, "login_form.html")

        username_form_action = await self._get_form_action(html_contents)
        if username_form_action is None:
            error = f"Didn't get the username form successfully from {url}"
            self.logger.error(error)
            raise LoginFailedError(error)

        self.logger.debug(f"Found username form target: {username_form_action}")
        return f"{URLs.LOGIN_BASE.value}{username_form_action}"

    async def _submit_username(
        self, url: str, username: Optional[str] = None, email: Optional[str] = None
    ) -> str:
        """Post username to get to the next login step"""
        self.logger.debug("Submitting username")
        if not (username or email):
            raise LoginFailedError("No username or email provided for login")

        if username:
            self.logger.debug(f"Using username: {username}")
            data = {"username": username}
        if email:
            self.logger.debug(f"Using email: {email}")
            data = {"email": email}
        html_contents = await self._get_html(
            url=url,
            method="POST",
            data=data,
            headers=await self._build_headers(referer=URLs.LOGIN_START.value),
        )
        self._save_file_if_needed(html_contents, "password_form.html")
        found_error = self._check_for_login_errors(html_contents, stage="login")
        if found_error:
            raise LoginFailedError(f"BBC sign-in failed: {found_error}")

        # Grab the form target for the password page
        password_form_action = await self._get_form_action(html_contents)
        if password_form_action is None:
            raise LoginFailedError("Could not find BBC password form URL")
        password_url = URLs.LOGIN_BASE.value + password_form_action
        self.logger.debug(f"Found password form target: {password_url}")
        return password_url

    async def _do_login(
        self,
        url: str,
        username: str,
        password: str,
        referrer_url: str,
    ) -> None:
        """Send both username and password to authenticate."""
        self.logger.debug("Logging in...")
        headers = await self._build_headers(referer=referrer_url)

        data = {"username": username, "password": password, "hasPassword": ""}
        resp = await self._make_request(
            method="POST",
            url=url,
            data=data,
            allow_redirects=True,
            headers=headers,
        )
        response_text = await resp.text()
        self._save_file_if_needed(response_text, "login_response.html")

        if not resp.ok or not self.is_logged_in:
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
            with open(Path(_get_data_dir(), filename), "w") as page:
                html = BeautifulSoup(html, features="html.parser").prettify()
                page.write(str(html))

    def save_cookies_to_disk(self):
        """Saved the cookie jar to disk to persist a session."""
        return self._session._cookie_jar.save(COOKIE_FILE)  # pyright: ignore[reportAttributeAccessIssue]

    def _check_for_login_errors(
        self, html: str, stage: Literal["email"] | Literal["login"]
    ):
        """See if we can extract a meaningful error from the HTML."""
        return None
        # FIXME: was false positives
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
        """Renew a session which has expired, but user is logged in."""
        url = self._build_url(url_template=constants.SignedInURLs.RENEW_SESSION)
        await self._make_request("GET", url)

    async def logout(self):
        try:
            os.remove(COOKIE_FILE)
        except FileNotFoundError:
            pass
        self._session._cookie_jar.clear()
