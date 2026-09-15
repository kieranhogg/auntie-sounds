from unittest.mock import AsyncMock, Mock

import pytest

from sounds.endpoints import URLs
from sounds.exceptions import APIResponseError
from sounds.models import Menu, MenuItem, RecommendedMenuItem
from sounds.personal import MenuRecommendationOptions, PersonalService
from sounds.requests import RequestManager

pytestmark = pytest.mark.anyio


def _menu_item_node(item_id: str, children: list) -> dict:
    """A minimal inline_display_module node, as produced by model_factory."""
    return {"type": "inline_display_module", "id": item_id, "data": children}


def _playable_child(suffix: str, recommendation: dict | None = None) -> dict:
    """A minimal playable_item node with no container."""
    node = {
        "type": "playable_item",
        "id": f"m{suffix}",
        "urn": f"urn:bbc:radio:episode:m{suffix}",
        "titles": {"primary": "Show"},
    }
    if recommendation is not None:
        node["recommendation"] = recommendation
    return node


async def run(self, call):
    return await call()


@pytest.fixture
def request_manager(mock_session):
    return RequestManager(
        session=mock_session,
        username=None,
        password=None,
    )


@pytest.fixture
def personal_service(mock_session, request_manager, monkeypatch):
    monkeypatch.setattr(RequestManager, "run", run)
    return PersonalService(
        auth=Mock(),
        requests=request_manager,
        session=mock_session,
    )


@pytest.fixture
def mixed_menu_json():
    """One plain menu item and one that should be promoted to 'recommended'."""
    return {
        "data": [
            _menu_item_node("regular", [_playable_child("1")]),
            _menu_item_node(
                "recommended",
                [_playable_child("2", recommendation={"reason": "because"})],
            ),
        ]
    }


class TestPersonalService:
    """Tests for personal service"""

    async def test_get_uk_menu_include_keeps_everything(
        self, request_manager, personal_service, monkeypatch, mixed_menu_json
    ):
        monkeypatch.setattr(
            request_manager,
            "get_json_response",
            AsyncMock(return_value=mixed_menu_json),
        )

        menu = await personal_service.get_uk_menu(
            recommendations=MenuRecommendationOptions.INCLUDE
        )

        assert isinstance(menu, Menu)
        assert len(menu.sub_items) == 2
        assert isinstance(menu.get("recommended"), RecommendedMenuItem)
        assert type(menu.get("regular")) is MenuItem

    async def test_get_uk_menu_exclude_drops_recommendations(
        self, request_manager, personal_service, monkeypatch, mixed_menu_json
    ):
        monkeypatch.setattr(
            request_manager,
            "get_json_response",
            AsyncMock(return_value=mixed_menu_json),
        )

        menu = await personal_service.get_uk_menu(
            recommendations=MenuRecommendationOptions.EXCLUDE
        )

        assert [item.id for item in menu.sub_items] == ["regular"]

    async def test_get_uk_menu_only_keeps_recommendations(
        self, request_manager, personal_service, monkeypatch, mixed_menu_json
    ):
        monkeypatch.setattr(
            request_manager,
            "get_json_response",
            AsyncMock(return_value=mixed_menu_json),
        )

        menu = await personal_service.get_uk_menu(
            recommendations=MenuRecommendationOptions.ONLY
        )

        assert [item.id for item in menu.sub_items] == ["recommended"]

    async def test_get_uk_menu_raises_on_empty_response(
        self, request_manager, personal_service, monkeypatch
    ):
        monkeypatch.setattr(
            request_manager, "get_json_response", AsyncMock(return_value={"data": []})
        )

        with pytest.raises(APIResponseError):
            await personal_service.get_uk_menu()

    async def test_get_explore_all_composes_submenus(
        self, request_manager, personal_service, monkeypatch
    ):
        podcasts_json = {
            "data": [_menu_item_node("podcasts_item", [_playable_child("3")])]
        }
        music_json = {"data": [_menu_item_node("music_item", [_playable_child("4")])]}
        news_json = {"data": [_menu_item_node("news_item", [_playable_child("5")])]}

        responses = {
            URLs.PODCASTS: podcasts_json,
            URLs.MUSIC: music_json,
            URLs.NEWS: news_json,
        }

        async def fake_get_json(url=None):
            return responses[url]

        monkeypatch.setattr(request_manager, "get_json_response", fake_get_json)

        explore_all = await personal_service.get_explore_all()

        assert explore_all.id == "explore"
        assert [item.id for item in explore_all.sub_items] == [
            "podcasts",
            "music",
            "news",
        ]
