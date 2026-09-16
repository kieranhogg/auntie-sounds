import asyncio
import logging
from enum import Enum, StrEnum, auto
from typing import Sequence

from sounds.auth import AuthService
from sounds.endpoints import URLs
from sounds.exceptions import APIResponseError
from sounds.models import Menu, MenuItem, PlayableItem, RecommendedMenuItem
from sounds.parser import Parser
from sounds.requests import RequestManager

logger = logging.getLogger(__name__)


class MenuRecommendationOptions(StrEnum):
    EXCLUDE = auto()
    INCLUDE = auto()
    ONLY = auto()


class PersonalService:
    """PersonalService interacts with the personalised endpoints of the API.

    The main API returns a fairly comprehensive nested menu structure for those
    users who are logged in. It also has some fairly noteable items missing,
    such as live radio stations and catch-up. This service ultimately constructs
    the menus for both logged-in users, and a smaller version for logged-out
    users, or international."""

    def __init__(
        self,
        auth: AuthService,
        requests: RequestManager,
    ):
        self.auth = auth
        self.requests = requests
        self.parser = Parser()

    async def get_uk_menu(
        self,
        recommendations: MenuRecommendationOptions = MenuRecommendationOptions.INCLUDE,
    ) -> Menu:
        """Gets the main Sounds menu."""

        async def call():
            return await self.requests.get_json_response(url=URLs.EXPERIENCE_MENU)

        json_resp = await self.requests.run(call)
        menu = self.parser.parse_menu(json_resp)
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
        json = await self.requests.get_json_response(URLs.PODCASTS)
        return MenuItem(
            id="podcasts",
            title="Podcasts",
            sub_items=self.parser.parse_menu(json).sub_items,
        )

    async def get_music_menu_item(self) -> MenuItem:
        return MenuItem(
            id="music",
            title="Music",
            sub_items=self.parser.parse_menu(
                await self.requests.get_json_response(URLs.MUSIC)
            ).sub_items,
        )

    async def get_news_menu_item(self) -> MenuItem:
        return MenuItem(
            id="news",
            title="News",
            sub_items=self.parser.parse_menu(
                await self.requests.get_json_response(URLs.NEWS)
            ).sub_items,
        )

    async def get_explore_all(self):
        explore_items = await asyncio.gather(
            self.get_podcasts_menu_item(),
            self.get_music_menu_item(),
            self.get_news_menu_item(),
        )

        return MenuItem(title="Explore All", id="explore", sub_items=explore_items)

    async def get_latest(self):
        async def call():
            return await self.requests.get_json_response(url=URLs.LATEST)

        return self.parser.parse_container(await self.requests.run(call))

    async def get_subscriptions(self):
        async def call():
            return await self.requests.get_json_response(url=URLs.SUBSCRIBED)

        return self.parser.parse_container(await self.requests.run(call))

    async def get_bookmarks(self):
        async def call():
            return await self.requests.get_json_response(url=URLs.BOOKMARKS)

        return self.parser.parse_container(await self.requests.run(call))

    async def get_continue_listening(self) -> list[PlayableItem] | None:
        async def call():
            return await self.requests.get_json_response(url=URLs.CONTINUE)

        container = self.parser.parse_container(await self.requests.run(call))
        if isinstance(container, list):
            return [item for item in container if isinstance(item, PlayableItem)]
        return None
