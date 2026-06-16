from functools import wraps
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup, Tag

from sounds import constants
from sounds.base import Base
from sounds.constants import URLs
from sounds.exceptions import LoginFailedError, NotFoundError, UnauthorisedError
from sounds.utils import _get_data_dir


def login_required(method):
    """Decorator to catch expired sessions and reauthenticate before trying again."""

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
    """Service to handle authentication with BBC Sounds."""

    def __init__(self, on_login_success=None, *args, **kwargs):
        self.user_info = None
        self.debug_login = False
        self._on_login_success = on_login_success
        if "debug_login" in kwargs:
            self.debug_login = kwargs.pop("debug_login")
        if kwargs.get("mock_session"):
            self.mock_session = True
            return
        super().__init__(**kwargs)

        if self.debug_login:
            # Can't move this to the above conditional as self.logger not initialised yet
            self.logger.info("Saving login pages to file as requested")

    async def _build_headers(self, referer: Optional[str] = None) -> dict:
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
        if not await self.is_uk_listener:
            self.logger.debug("International user")
        else:
            self.logger.debug("UK user")

        username_url = await self._get_login_form()
        password_url = await self._submit_username(url=username_url, username=username)
        if password_url == username_url:
            error = "Login did not succeed to stage 2 successfully"
            self.logger.error(error)
            raise LoginFailedError(error)
        ok = await self._do_login(
            url=password_url,
            username=username,
            password=password,
            referrer_url=username_url,
        )
        return ok

    async def _get_form_action(self, html: str) -> Optional[str]:
        """Finds the target of a form action from HTML markup"""
        soup = BeautifulSoup(html, "html.parser")
        forms = soup.find_all("form")
        if len(forms) > 1:
            self.logger.debug(
                f"Found {len(forms)} forms on page, returning the first one"
            )
        form = soup.find("form")
        if form is not None and isinstance(form, Tag):
            form_action = form.get("action", None)
            if form_action is not None:
                return str(form_action)
        error = "Couldn't get form action"
        self.logger.error(error)
        self.logger.debug(forms)
        raise NotFoundError(error)

    async def _get_login_form(self) -> str:
        # Get the initial login page form target
        self.logger.debug("Getting initial login page")
        request = await self._make_request(
            method="GET",
            url=URLs.LOGIN_START.value,
            headers=await self._build_headers(),
            allow_redirects=False,
        )

        # Intercept the redirection flow
        while request.status in [301, 302, 303, 307, 308]:
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

        if not request.ok:
            error = "Failed to get initial login page"
            self.logger.error(error)
            raise LoginFailedError(error)

        html_contents = await request.text()

        self._save_file_if_needed(html_contents, "login_form.html")

        username_form_action = await self._get_form_action(html_contents)
        if username_form_action is None:
            error = "Didn't get the username form successfully"
            self.logger.error(error)
            raise LoginFailedError(error)

        self.logger.debug(f"Found username form target: {username_form_action}")
        return URLs.LOGIN_BASE.value + username_form_action

    async def _submit_username(self, url: str, username: str) -> str:
        """Post username to get to the next login step"""
        self.logger.debug("Submitting username")
        data = {"username": username}
        html_contents = await self._get_html(
            url=url,
            method="POST",
            data=data,
            headers=await self._build_headers(referer=URLs.LOGIN_START.value),
        )
        self._save_file_if_needed(html_contents, "password_form.html")

        # Grab the form target for the password page
        password_form_action = await self._get_form_action(html_contents)
        if password_form_action is None:
            raise LoginFailedError("Could not find password form URL")
        password_url = URLs.LOGIN_BASE.value + password_form_action
        self.logger.debug(f"Found password form target: {password_url}")
        return password_url

    async def _do_login(
        self,
        url: str,
        username: str,
        password: str,
        referrer_url: str,
    ) -> bool:
        """Send both username and password to authenticate."""
        self.logger.debug("Logging in...")
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
        self._save_file_if_needed(response_text, "login_response.html")

        if not resp.ok:
            error_string = f"BBC sign-in failed: {resp.status}"
            self.logger.error(error_string)
            raise LoginFailedError(error_string)
        else:
            if self._on_login_success:
                self._on_login_success()
            self.logger.debug("Authenticated succesfully")
            return True

    def _save_file_if_needed(self, html: str | bytes, filename: str):
        if self.debug_login:
            with open(Path(_get_data_dir(), filename), "w") as page:
                html = BeautifulSoup(html, features="html.parser").prettify()
                page.write(str(html))

    async def renew_session(self):
        """Renew a session which has expired, but user is logged in."""
        url = self._build_url(url_template=constants.SignedInURLs.RENEW_SESSION)
        await self._make_request("GET", url)
        await self.set_user_info()
