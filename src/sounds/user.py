from sounds.base import Base
from sounds.constants import URLs


class UserService(Base):
    def __init__(self) -> None:
        self.user_info: dict[str, str] | None = None

    async def refresh(self) -> None:
        self.user_info = await self._get_json(url_template=URLs.USER_INFO)

    async def listener_country(self) -> str | None:
        """Return the listener's current country."""
        if self.user_info:
            return self.user_info.get("X-Country")
        return None

    async def is_in_uk(self) -> bool:
        """Listener is in the UK."""
        if self.user_info:
            return self.user_info.get("X-Country") == "gb"
        return False

    async def is_uk_listener(self) -> bool:
        """Listener has a UK-based account and is in the UK."""
        if self.user_info:
            return self.user_info["X-Ip_is_uk_combined"] == "yes"
        return False
