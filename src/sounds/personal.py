from enum import Enum

from .models import Menu, RecommendedMenuItem
from .parser import parse_menu, parse_container
from .auth import AuthService, login_required
from .base import Base
from .constants import URLs, SignedInURLs
from .exceptions import APIResponseError, UnauthorisedError


class MenuRecommendationOptions(Enum):
    EXCLUDE = "Exclude"
    INCLUDE = "Include"
    ONLY = "Only"


class PersonalService(Base):
    def __init__(
        self,
        auth_service: AuthService,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.auth = auth_service

    @login_required
    async def get_experience_menu(
        self,
        recommendations: MenuRecommendationOptions = MenuRecommendationOptions.INCLUDE,
    ) -> Menu:
        """Gets the main Sounds menu."""
        json_resp = await self._get_json(url_template=URLs.EXPERIENCE_MENU)
        menu = parse_menu(json_resp)
        if not isinstance(menu, Menu) or not menu or not menu.sub_items:
            raise APIResponseError("Menu not converted correctly")
        if recommendations == MenuRecommendationOptions.EXCLUDE:
            filtered_menu = [
                item
                for item in menu.sub_items
                if item and type(item) is not RecommendedMenuItem
            ]
        elif recommendations == MenuRecommendationOptions.ONLY:
            filtered_menu = [
                item for item in menu.sub_items if type(item) is RecommendedMenuItem
            ]
        else:
            filtered_menu = list(menu.sub_items)
        menu.sub_items = filtered_menu
        return menu

    @login_required
    async def get_subscriptions(self):
        json_resp = await self._get_json(url_template=SignedInURLs.SUBSCRIBED)
        return parse_container(json_resp)
