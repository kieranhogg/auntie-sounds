from unittest.mock import AsyncMock

import pytest

from sounds.endpoints import Endpoints
from sounds.exceptions import APIResponseError
from sounds.models import Menu, MenuItem, RecommendedMenuItem


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
        self, mock_personal_service, mock_requests, monkeypatch, mixed_menu_json
    ):
        monkeypatch.setattr(
            mock_requests,
            "get_json_response",
            AsyncMock(return_value=mixed_menu_json),
        )

        menu = await mock_personal_service.construct_uk_menu(
            radio=MenuItem(id="listen_live"),
            catch_up=MenuItem(id="catch_up"),
            schedule=MenuItem(id="schedule"),
        )

        assert isinstance(menu, Menu)
        assert len(menu.sub_items) == 7
        assert isinstance(menu.get("recommended"), RecommendedMenuItem)
        assert type(menu.get("regular")) is MenuItem

    async def test_get_uk_menu_exclude_drops_recommendations(
        self, mock_personal_service, mock_requests, monkeypatch, mixed_menu_json
    ):
        monkeypatch.setattr(
            mock_requests,
            "get_json_response",
            AsyncMock(return_value=mixed_menu_json),
        )

        menu = await mock_personal_service.construct_uk_menu(
            radio=MenuItem(id="listen_live"),
            catch_up=MenuItem(id="catch_up"),
            schedule=MenuItem(id="schedule"),
        )
        assert [item.id for item in menu.sub_items] != ["recommended"]

    async def test_get_uk_menu_only_keeps_recommendations(
        self, mock_personal_service, mock_requests, monkeypatch, mixed_menu_json
    ):
        monkeypatch.setattr(
            mock_requests,
            "get_json_response",
            AsyncMock(return_value=mixed_menu_json),
        )

        folders = await mock_personal_service.get_recommendations()

        assert [item.id for item in folders] == ["recommended"]

    async def test_get_uk_menu_raises_on_empty_response(
        self, mock_personal_service, mock_requests, monkeypatch
    ):
        monkeypatch.setattr(
            mock_requests, "get_json_response", AsyncMock(return_value={"data": []})
        )

        with pytest.raises(APIResponseError):
            await mock_personal_service.construct_uk_menu(
                radio=MenuItem(id="listen_live"),
                catch_up=MenuItem(id="catch_up"),
                schedule=MenuItem(id="schedule"),
            )

    async def test_get_explore_all_composes_submenus(
        self, mock_personal_service, mock_requests, monkeypatch
    ):
        podcasts_json = {
            "data": [_menu_item_node("podcasts_item", [_playable_child("3")])]
        }
        music_json = {"data": [_menu_item_node("music_item", [_playable_child("4")])]}
        news_json = {"data": [_menu_item_node("news_item", [_playable_child("5")])]}

        responses = {
            Endpoints.PODCASTS: podcasts_json,
            Endpoints.MUSIC: music_json,
            Endpoints.NEWS: news_json,
        }

        async def fake_get_json(url=None):
            return responses[url]  # type: ignore[ty:invalid-argument-type]

        monkeypatch.setattr(mock_requests, "get_json_response", fake_get_json)

        explore_all = await mock_personal_service.get_explore_all()

        assert explore_all.id == "explore"
        assert [item.id for item in explore_all.sub_items] == [
            "podcasts",
            "music",
            "news",
        ]
