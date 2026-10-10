import logging

from auntie_sounds.endpoints import URLs
from auntie_sounds.exceptions import APIResponseError, NotFoundError, UnauthorisedError
from auntie_sounds.requests import RequestManager

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, requests: RequestManager, login_details_provided: bool) -> None:
        self.requests = requests
        self._user_info: dict[str, str] = {}
        self.login_details_provided = login_details_provided

    async def refresh(self) -> None:
        self._user_info = await self.requests.get_json_response(url=URLs.USER_INFO)

    async def _ensure_loaded(self):
        if not self._user_info:
            try:
                await self.refresh()
            except UnauthorisedError, NotFoundError, APIResponseError:
                logger.warning("Couldn't get user_info")

    async def listener_country(self) -> str | None:
        """Return the listener's current country."""
        await self._ensure_loaded()
        return self._user_info.get("X-Country", "us")

    async def is_geolocated_in_uk(self) -> bool:
        """Listener is in the UK."""
        await self._ensure_loaded()
        return self._user_info.get("X-Country", "us") == "gb"

    async def is_uk_account_and_location(self) -> bool:
        """Listener has a UK-based account and is in the UK."""
        await self._ensure_loaded()
        return self._user_info.get("X-Ip_is_uk_combined", "no") == "yes"
