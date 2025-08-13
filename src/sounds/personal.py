from .json import parse_menu
from .auth import AuthService
from .base import Base
from .constants import URLs
from .exceptions import APIResponseError


class PersonalService(Base):
    def __init__(
        self,
        auth_service: AuthService,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.auth = auth_service

    # @login_required
    async def get_experience_menu(self):
        """Gets the main Sounds menu."""
        json_resp = await self._get_json(URLs.EXPERIENCE_MENU)

        if not json_resp or "data" not in json_resp:
            raise APIResponseError(
                f"Couldn't get the main menu:\n{json_resp.get("message")}"
            )

        menu = parse_menu(json_resp)
        return menu
