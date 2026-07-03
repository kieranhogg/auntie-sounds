from logging import Logger

from sounds.auth import AuthService
from sounds.cookies import CookieStore
from sounds.exceptions import UnauthorisedError


class RequestManager:
    def __init__(
        self,
        auth: AuthService,
        cookie_store: CookieStore,
        logger: Logger,
        username: str | None,
        password: str | None,
    ):
        self.logger = logger
        self.auth = auth
        self.cookies = cookie_store
        self.username = username
        self.password = password

    async def run(self, call):
        """Ensures user is logged in before running `call`."""
        try:
            self.logger.debug(f"Running {call}")
            return await call()
        except UnauthorisedError:
            self.logger.debug("Unauthorised when accessing an authenticated endpoint.")

            if self.cookies.has_session_cookie:
                self.logger.debug("Cookie present, renewing session...")
                try:
                    await self.auth.renew_session()
                    return await call()
                except UnauthorisedError:
                    self.logger.error("Session renewal failed, trying full login...")

            if not self.username or not self.password:
                self.logger.error(
                    "No username and/or password provided to SoundsClient."
                )
                raise UnauthorisedError(
                    "No username and/or password provided to SoundsClient."
                )

            await self.auth.login(username=self.username, password=self.password)
            self.logger.info("Logged in.")
            return await call()
