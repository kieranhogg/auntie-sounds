import logging
from typing import Optional
from bs4 import BeautifulSoup

from yarl import URL

from . import constants
from .base import Base
from .constants import COOKIE_ID, VERBOSE_LOG_LEVEL, URLs
from .exceptions import LoginFailedException


class AuthService(Base):
    @property
    def authenticated(self) -> bool:
        """Checks if we have a valid session"""
        return COOKIE_ID in self._session.cookie_jar.filter_cookies(
            URL(URLs.COOKIE_URL)
        )

    def _build_headers(self, referer: Optional[str] = None) -> dict:
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
        if self.authenticated:
            self.logger.log(VERBOSE_LOG_LEVEL, "Existing session found, reusing")
            return True

        username_url = await self._get_login_form()
        password_url = await self._submit_username(url=username_url, username=username)
        await self._do_login(url=password_url, username=username, password=password)
        return self.authenticated

    def _get_form_action(self, html: str) -> Optional[str]:
        """Finds the target of a form action from HTML markup"""
        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form")
        if form:
            self.logger.debug("Found form successfully")
        # form = soup.find("form", attrs={"id": "loginForm"}) or soup.select_one(
        # "form[action]"
        # )
        return form.get("action") if form else None

    async def _get_login_form(self) -> str:
        # Get the initial login page form target
        html_contents = await self._get_html(
            URLs.LOGIN_START,
            "GET",
            headers=self._build_headers(),
        )
        username_form_action = self._get_form_action(html_contents)
        self.logger.debug(f"Found username form target: {username_form_action}")
        if not username_form_action:
            raise RuntimeError("Could not find BBC sign-in form URL")
        url = f"{URLs.LOGIN_BASE}{username_form_action}"
        return url

    async def _submit_username(self, url: str, username: str) -> str:
        """Post username to get to the next login step"""
        html_contents = await self._get_html(
            url,
            "POST",
            data={"username": username},
            headers=self._build_headers(referer=URLs.LOGIN_START),
        )
        self.logger.log(VERBOSE_LOG_LEVEL, html_contents[:200])

        # Grab the form target for the password page
        password_form_action = self._get_form_action(html_contents)
        if not password_form_action:
            raise LoginFailedException("Could not find BBC password form URL")
        password_url = f"{URLs.LOGIN_BASE}{password_form_action}"
        self.logger.debug(f"Found password form target: {password_url}")

        return password_url

    async def _do_login(self, url: str, username: str, password: str) -> None:
        """Send both username and password to authenticate."""
        async with await self._make_request(
            "POST",
            url,
            data={"username": username, "password": password},
            headers=self._build_headers(referer=url),
            allow_redirects=True,
        ) as resp:
            if resp.status != 200 or not self.authenticated:
                self.logger.error(f"Login failed, response code {resp.status}")
                self.logger.log(constants.VERBOSE_LOG_LEVEL, resp)
                raise LoginFailedException(f"BBC sign-in failed: {resp.status}")
            self.logger.info("Authenticated succesfully")
