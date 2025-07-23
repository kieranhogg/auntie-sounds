from .base import Base
from .constants import SignedInURLs, URLs
from .models import Menu, MenuItem, Network, PlayableItem


class PersonalService(Base):

    async def get_experience_menu(self):
        """Gets the main Sounds menu."""
        resp = await self._get_json(URLs.EXPERIENCE_MENU)

        # TODO There are easier ways to do this but I got bored wrangling with libraries
        menu_items = [
            MenuItem(
                id=item["id"],
                title=item["title"],
                description=item["description"],
                data=[
                    PlayableItem(
                        id=playable_item["id"],
                        urn=playable_item["urn"],
                        network=(
                            Network(
                                id=playable_item["network"]["id"],
                                key=playable_item["network"]["key"],
                                short_title=playable_item["network"]["short_title"],
                                logo_url=playable_item["network"]["logo_url"],
                            )
                            if playable_item.get("network") is not None
                            else None
                        ),
                        # start=playable_item["start"],
                        # end=playable_item["end"],
                        duration=(
                            playable_item["duration"]["value"]
                            if playable_item.get("duration") is not None
                            else None
                        ),
                        progress=(
                            playable_item["progress"]["value"]
                            if playable_item.get("progress") is not None
                            else None
                        ),
                        synopses=(
                            playable_item["synopses"]
                            if playable_item.get("synopses") is not None
                            else {}
                        ),
                        image_url=playable_item["image_url"],
                        titles=(
                            playable_item["titles"]
                            if playable_item.get("titles") is not None
                            else {}
                        ),
                    )
                    for playable_item in item["data"]
                ],
            )
            for item in resp["data"]
        ]
        menu = Menu(items=menu_items)
        return menu
