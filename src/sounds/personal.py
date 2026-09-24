import asyncio
import logging
from collections.abc import Sequence
from enum import StrEnum, auto

from sounds.auth import AuthService
from sounds.endpoints import Endpoints
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
        radio: MenuItem,
        catch_up: MenuItem,
        schedule: MenuItem,
        include_recommendations: bool = True,
    ) -> Menu:
        """Gets the main Sounds menu for UK-based users."""

        json_resp = await self.requests.get_json_response(url=Endpoints.EXPERIENCE_MENU)
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

        # Remove the API's listen_live to replace with ours (as it's better)
        menu.sub_items = [
            obj
            for obj in menu.sub_items
            if obj.id not in ["listen_live", "continue_listening"]
        ]

        latest, bookmarks, subscribed, continue_listening = await asyncio.gather(
            self.get_latest_menu(),
            self.get_bookmarks_menu(),
            self.get_subscriptions_menu(),
            self.get_continue_listening_menu(),
        )

        my_sounds = MenuItem(
            title="My Sounds",
            id="my_sounds",
            sub_items=[continue_listening, subscribed, latest, bookmarks],
        )

        menu.sub_items = [
            radio,
            catch_up,
            schedule,
            my_sounds,
            *menu.sub_items,
            await self.get_explore_all(),
        ]
        return menu

    async def get_recommendations(self) -> Sequence[RecommendedMenuItem]:
        json_resp = await self.requests.get_json_response(url=Endpoints.EXPERIENCE_MENU)
        menu = self.parser.parse_menu(json_resp)
        return [
            recommendation
            for recommendation in menu.sub_items
            if isinstance(recommendation, RecommendedMenuItem)
        ]

    async def construct_international_menu(
        self,
        radio: MenuItem,
        catch_up: MenuItem,
        schedule: MenuItem,
    ) -> Menu:
        """Gets the main Sounds menu for international users."""

        return Menu(
            sub_items=[
                radio,
                catch_up,
                schedule,
                await self.get_explore_all(),
            ]
        )

    async def get_podcasts_menu_item(self) -> MenuItem:
        json = await self.requests.get_json_response(Endpoints.PODCASTS)
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
                await self.requests.get_json_response(Endpoints.MUSIC)
            ).sub_items,
        )

    async def get_news_menu_item(self) -> MenuItem:
        return MenuItem(
            id="news",
            title="News",
            sub_items=self.parser.parse_menu(
                await self.requests.get_json_response(Endpoints.NEWS)
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
        latest_items = self.parser.parse_container(
            await self.requests.get_json_response(url=Endpoints.LATEST)
        )
        if not latest_items or type(latest_items) is not list:
            return []
        return [
            item
            for item in latest_items
            if latest_items and isinstance(item, PlayableItem)
        ]

    async def get_latest_menu(self):
        latest_items = await self.get_latest()
        return MenuItem(title="Latest", id="latest", sub_items=latest_items)

    async def get_subscriptions(self):
        subscriptions = self.parser.parse_container(
            await self.requests.get_json_response(url=Endpoints.SUBSCRIBED)
        )
        return subscriptions or []

    async def get_subscriptions_menu(self):
        subscriptions = await self.get_subscriptions()
        return MenuItem(
            title="Subscriptions", id="subscriptions", sub_items=subscriptions
        )

    async def get_bookmarks(self):
        bookmarks = self.parser.parse_container(
            await self.requests.get_json_response(url=Endpoints.BOOKMARKS)
        )
        if not bookmarks or type(bookmarks) is not list:
            return []
        return [item for item in bookmarks if isinstance(item, PlayableItem)]

    async def get_bookmarks_menu(self):
        bookmarks = await self.get_bookmarks()
        return MenuItem(title="Bookmarks", id="bookmarks", sub_items=bookmarks)

    async def get_continue_listening(self) -> list[PlayableItem] | None:
        json_response = await self.requests.get_json_response(url=Endpoints.CONTINUE)
        container = self.parser.parse_container(json_response)
        if isinstance(container, list):
            return [item for item in container if isinstance(item, PlayableItem)]
        return None

    async def get_continue_listening_menu(self) -> MenuItem:
        continue_listening_items = await self.get_continue_listening()
        return MenuItem(
            title="Continue Listening",
            id="continue_listening",
            sub_items=continue_listening_items,
        )
