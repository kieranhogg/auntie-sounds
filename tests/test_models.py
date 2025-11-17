import json
from datetime import datetime as dt
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest
import pytz

from sounds.auth import AuthService

from sounds.client import SoundsClient
from sounds.constants import ImageType
from sounds.exceptions import (
    APIResponseError,
    InvalidFormatError,
    LoginFailedError,
    NetworkError,
    NotFoundError,
)
from sounds.models import (
    Container,
    Menu,
    MenuItem,
    PlayableItem,
    Podcast,
    PodcastEpisode,
    ScheduleItem,
    SearchResults,
)
from sounds.parser import parse_menu, parse_node, parse_search
from sounds.personal import PersonalService
from sounds.schedules import ScheduleService
from sounds.stations import StationService
from sounds.streaming import StreamingService
from sounds.utils import image_from_recipe, network_logo


class TestModels:
    """Tests for model classes"""

    def test_schedule_item_datetime_parsing(self):
        """Test ScheduleItem datetime parsing"""
        data = {
            "id": "m001234",
            "start": "2025-01-15T10:00:00Z",
            "end": "2025-01-15T12:00:00Z",
        }
        item = ScheduleItem(**data)
        assert isinstance(item.start, dt)
        assert isinstance(item.end, dt)

    def test_schedule_item_is_live(self):
        """Test ScheduleItem.is_live() method"""
        now = dt.now(tz=pytz.UTC)
        item = ScheduleItem(
            id="test",
            start=now.replace(hour=now.hour - 1),
            end=now.replace(hour=now.hour + 1),
        )
        assert item.is_live(pytz.UTC) is True

    def test_schedule_item_has_aired(self):
        """Test ScheduleItem.has_already_aired() method"""
        now = dt.now(tz=pytz.UTC)
        item = ScheduleItem(
            id="test",
            start=now.replace(hour=now.hour - 2),
            end=now.replace(hour=now.hour - 1),
        )
        assert item.has_already_aired(pytz.UTC) is True

    def test_playable_item_id_from_urn(self):
        """Test PlayableItem.item_id property with URN"""
        item = PlayableItem(
            id="test123", urn="urn:bbc:radio:episode:m001234", pid="p001234"
        )
        assert item.item_id == "m001234"

    def test_playable_item_id_fallback_to_pid(self):
        """Test PlayableItem.item_id property fallback to PID"""
        item = PlayableItem(id="test123", pid="p001234")
        assert item.item_id == "p001234"

    def test_container_item_id(self):
        """Test Container.item_id property"""
        container = Container(id="test123", urn="urn:bbc:radio:brand:b006wkqb")
        assert container.item_id == "b006wkqb"

    def test_menu_get_item(self):
        """Test Menu.get() method"""
        item1 = MenuItem(id="item1", title="Item 1")
        item2 = MenuItem(id="item2", title="Item 2")
        menu = Menu(sub_items=[item1, item2])

        result = menu.get("item1")
        assert result == item1
        assert result.title == "Item 1"

    def test_menu_get_nonexistent(self):
        """Test Menu.get() with non-existent item"""
        menu = Menu(sub_items=[MenuItem(id="item1", title="Item 1")])
        result = menu.get("nonexistent")
        assert result is None
