from unittest.mock import AsyncMock

import pytest
import pytz

from sounds.client import SoundsClient
from sounds.user import UserService


class TestClientLifecycle:
    """Integration tests for the client."""

    async def test_client_initialization(self):
        """Test client initialisation"""
        client = SoundsClient(timezone=pytz.UTC)
        assert client.timezone == pytz.UTC
        assert client.auth is not None
        assert client.stations is not None
        assert client.playback is not None
        assert client.content is not None
        assert client.schedules is not None
        assert client.personal is not None
        await client.close()

    async def test_client_context_manager(self):
        """Test context manager."""
        async with SoundsClient(timezone=pytz.UTC) as client:
            assert client is not None

    async def test_client_close(self):
        """Closing an already-closed client shouldn't raise an exception."""
        client = SoundsClient(timezone=pytz.UTC)
        await client.close()
        await client.close()


class TestClientMenu:
    """Test the client construction of the menus."""

    @pytest.fixture(name="uk_user_service", scope="class")
    def _uk_user_service(self):
        user_service = AsyncMock(spec=UserService)
        user_service.login_details_provided = True
        user_service.is_uk_account_and_location = AsyncMock(return_value=True)
        return user_service

    @pytest.fixture(name="international_user_service", scope="class")
    def _i18n_user_service(self):
        user_service = AsyncMock(spec=UserService)
        user_service.login_details_provided = False
        user_service.is_uk_account_and_location = AsyncMock(return_value=False)
        return user_service

    async def test_uk_menu_is_created_for_uk_users(self, mock_client, uk_user_service):
        mock_client.user = uk_user_service
        mock_client.personal.construct_uk_menu = AsyncMock()
        mock_client.personal.construct_international_menu = AsyncMock()

        await mock_client.get_menu()

        mock_client.personal.construct_uk_menu.assert_awaited_once()
        mock_client.personal.construct_international_menu.assert_not_awaited()

    async def test_uk_menu_is_created(self, mock_client, uk_user_service):
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
        mock_client.user = uk_user_service

        menu = await mock_client.get_menu()
        assert menu is not None
        assert len(menu.sub_items) == 14

        # Check the manually-added menu item are present
        menu_ids = [item.id for item in menu.sub_items]
        for id in manual_menu_ids:
            assert id in menu_ids

        # Check the API menu items are present
        for id in api_menu_ids:
            assert id in menu_ids

    async def test_international_menu_is_created_for_international_users(
        self, mock_client, international_user_service
    ):
        mock_client.user = international_user_service
        mock_client.personal.construct_uk_menu = AsyncMock()
        mock_client.personal.construct_international_menu = AsyncMock()

        await mock_client.get_menu()

        mock_client.personal.construct_international_menu.assert_awaited_once()
        mock_client.personal.construct_uk_menu.assert_not_awaited()
