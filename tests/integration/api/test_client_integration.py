import os

import pytest

from sounds.client import SoundsClient


@pytest.mark.local_only
@pytest.mark.api
class TestClientMenu:
    """Test the SoundsClient menu construction against the live API.

    Note: can't be run in CI as will fail the API's geolocation checks"""

    async def test_uk_menu_is_created(self):
        username = os.getenv("SOUNDS_USERNAME")
        password = os.getenv("SOUNDS_PASSWORD")
        client = SoundsClient(username=username, password=password)

        manual_menu_ids = ["listen_live", "schedule", "catch_up"]
        api_menu_ids = [
            "continue_listening",
            "unmissable_speech",
            "unmissable_music",
            "editorial_collection",
            "recommendations",
            "local_rail",
            "collections",
            "categories",
            "explore",
        ]

        menu = await client.get_menu()
        assert menu is not None
        assert len(menu.sub_items) == 14

        # Check the manually-added menu item are present
        menu_ids = [item.id for item in menu.sub_items]
        for id in manual_menu_ids:
            assert id in menu_ids

        # Check the API menu items are present
        for id in api_menu_ids:
            assert id in menu_ids

    async def test_news_prefix(self):
        """Checks the format of the news playlist hasn't changed."""
        username = os.getenv("SOUNDS_USERNAME")
        password = os.getenv("SOUNDS_PASSWORD")
        client = SoundsClient(username=username, password=password)

        news_prefix = "latest_playables_for_curation-"

        menu = await client.get_menu()
        assert menu is not None
        assert len(menu.sub_items) == 14

        menu_ids = [item.id for item in menu.sub_items]
        assert sum(id.startswith(news_prefix) for id in menu_ids) == 1
