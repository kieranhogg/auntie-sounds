from enum import Enum
from typing import TYPE_CHECKING

from sounds.auth import AuthService
from sounds.base import Base
from sounds.constants import SignedInURLs, URLs
from sounds.exceptions import APIResponseError
from sounds.models import Menu, MenuItem, RecommendedMenuItem
from sounds.parser import parse_container, parse_menu
from sounds.requests import RequestManager

if TYPE_CHECKING:
    pass


class MenuRecommendationOptions(Enum):
    EXCLUDE = "Exclude"
    INCLUDE = "Include"
    ONLY = "Only"


class PersonalService(Base):
    def __init__(
        self,
        auth: AuthService,
        requests: RequestManager,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.auth = auth
        self.requests = requests

    async def get_uk_menu(
        self,
        recommendations: MenuRecommendationOptions = MenuRecommendationOptions.INCLUDE,
    ) -> Menu:
        """Gets the main Sounds menu."""

        async def call():
            return await self._get_json(url_template=URLs.EXPERIENCE_MENU)

        json_resp = await self.requests.run(call)
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

    async def get_podcasts_menu_item(self) -> MenuItem:
        json = await self._get_json(URLs.PODCASTS)
        return MenuItem(
            id="podcasts",
            title="Podcasts",
            sub_items=parse_menu(json).sub_items,
        )

    async def get_music_menu_item(self) -> MenuItem:
        return MenuItem(
            id="music",
            title="Music",
            sub_items=parse_menu(await self._get_json(URLs.MUSIC)).sub_items,
        )

    async def get_news_menu_item(self) -> MenuItem:
        return MenuItem(
            id="news",
            title="News",
            sub_items=parse_menu(await self._get_json(URLs.NEWS)).sub_items,
        )

    async def get_explore_all(self):
        return MenuItem(
            title="Explore All",
            id="explore",
            sub_items=[
                await self.get_podcasts_menu_item(),
                await self.get_music_menu_item(),
                await self.get_news_menu_item(),
            ],
        )

    async def get_latest(self):
        async def call():
            return await self._get_json(url_template=SignedInURLs.LATEST)

        return parse_container(await self.requests.run(call))

    async def get_subscriptions(self):
        async def call():
            return await self._get_json(url_template=SignedInURLs.SUBSCRIBED)

        return parse_container(await self.requests.run(call))

    async def get_bookmarks(self):
        async def call():
            return await self._get_json(url_template=SignedInURLs.BOOKMARKS)

        return parse_container(await self.requests.run(call))

    async def continue_listening(self):
        async def call():
            return await self._get_json(url_template=SignedInURLs.CONTINUE)

        return parse_container(await self.requests.run(call))
