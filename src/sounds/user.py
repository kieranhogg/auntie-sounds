from sounds.base import Base
from sounds.constants import URLs
from sounds.session import Session


class UserService(Base):
    def __init__(
        self, state: Session, login_details_provided: bool, *args, **kwargs
    ) -> None:
        super().__init__(state=state, *args, **kwargs)
        self._user_info: dict[str, str] = dict()
        self.login_details_provided = login_details_provided

    async def refresh(self) -> None:
        self._user_info = await self._get_json(url_template=URLs.USER_INFO)

    async def _ensure_loaded(self):
        if not self._user_info:
            await self.refresh()

    async def listener_country(self) -> str | None:
        """Return the listener's current country."""
        await self._ensure_loaded()
        return self._user_info.get("X-Country")

    async def is_in_uk(self) -> bool:
        """Listener is in the UK."""
        await self._ensure_loaded()
        return self._user_info.get("X-Country") == "gb"

    async def is_uk_listener(self) -> bool:
        """Listener has a UK-based account and is in the UK."""
        await self._ensure_loaded()
        return self._user_info["X-Ip_is_uk_combined"] == "yes"
