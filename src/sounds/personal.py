import asyncio
import logging
from collections.abc import Sequence
from enum import StrEnum, auto

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

    async def construct_uk_menu(
        self,
        listen_live: MenuItem,
        catch_up: MenuItem,
        schedule: MenuItem,
        include_recommendations: bool = True,
    ) -> Menu:
        """Gets the main Sounds menu for UK-based users."""

        json_resp = await self.requests.get_json_response(url=URLs.EXPERIENCE_MENU)
        menu = self.parser.parse_menu(json_resp)
        if not isinstance(menu, Menu) or not menu or len(menu.sub_items) == 0:
            raise APIResponseError("Menu not converted correctly.")
        if include_recommendations:
            menu.sub_items = list(menu.sub_items)
        else:
            # Filter out recommendations if needed
            menu.sub_items = [
                item
                for item in menu.sub_items
                if item
                and (
                    not include_recommendations
                    and type(item) is not RecommendedMenuItem
                )
            ]
        menu.sub_items = [
            listen_live,
            catch_up,
            schedule,
            *menu.sub_items,
            await self.get_explore_all(),
        ]
        return menu

    async def get_recommendations(self) -> Sequence[RecommendedMenuItem]:
        json_resp = await self.requests.get_json_response(url=URLs.EXPERIENCE_MENU)
        menu = self.parser.parse_menu(json_resp)
        return [
            recommendation
            for recommendation in menu.sub_items
            if isinstance(recommendation, RecommendedMenuItem)
        ]

    async def construct_international_menu(
        self,
        listen_live: MenuItem,
        catch_up: MenuItem,
        schedule: MenuItem,
    ) -> Menu:
        """Gets the main Sounds menu for international users."""

        return Menu(
            sub_items=[
                listen_live,
                catch_up,
                schedule,
                await self.get_explore_all(),
            ]
        )

    def get_listen_live(self):
        return MenuItem(title="Listen Live", id="listen_live", sub_items=self.sta)

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
        return self.parser.parse_container(
            await self.requests.get_json_response(url=URLs.LATEST)
        )

    async def get_subscriptions(self):
        return self.parser.parse_container(
            await self.requests.get_json_response(url=URLs.SUBSCRIBED)
        )

    async def get_bookmarks(self):
        return self.parser.parse_container(
            await self.requests.get_json_response(url=URLs.BOOKMARKS)
        )

    async def get_continue_listening(self) -> list[PlayableItem] | None:
        json_response = await self.requests.get_json_response(url=URLs.CONTINUE)
        container = self.parser.parse_container(json_response)
        if isinstance(container, list):
            return [item for item in container if isinstance(item, PlayableItem)]
        return None
