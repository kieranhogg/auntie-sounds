from enum import Enum

from sounds.auth import AuthService, login_required
from sounds.base import Base
from sounds.constants import SignedInURLs, URLs
from sounds.exceptions import APIResponseError
from sounds.models import Menu, RecommendedMenuItem
from sounds.parser import parse_container, parse_menu


class MenuRecommendationOptions(Enum):
    EXCLUDE = "Exclude"
    INCLUDE = "Include"
    ONLY = "Only"


class PersonalService(Base):
    def __init__(
        self,
        auth: AuthService,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.auth = auth

    @login_required
    async def get_experience_menu(
        self,
        recommendations: MenuRecommendationOptions = MenuRecommendationOptions.INCLUDE,
    ) -> Menu:
        """Gets the main Sounds menu."""
        json_resp = await self._get_json(url_template=URLs.EXPERIENCE_MENU)
        menu = parse_menu(json_resp)
        if not isinstance(menu, Menu) or not menu or len(menu.sub_items) == 0:
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

    @login_required
    async def get_bookmarks(self):
        json_resp = await self._get_json(url_template=SignedInURLs.BOOKMARKS)
        return parse_container(json_resp)

    @login_required
    async def continue_listening(self):
        json_resp = await self._get_json(url_template=SignedInURLs.CONTINUE)
        return parse_container(json_resp)
