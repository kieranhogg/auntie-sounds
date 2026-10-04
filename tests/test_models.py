import copy
import logging
from datetime import datetime as dt
from datetime import timedelta

import pytest
import pytz
from pytest import MarkDecorator

from sounds import parse
from sounds.models import (
    Container,
    Duration,
    Menu,
    MenuItem,
    PlayableItem,
    ScheduleItem,
)
from tests.conftest import load_fixture

pytestmark: MarkDecorator = pytest.mark.anyio


class TestModels:
    """Tests for model classes."""

    def test_schedule_item_datetime_parsing(self):
        """Test ScheduleItem datetime parsing."""
        data = {
            "id": "m001234",
            "start": "2025-01-15T10:00:00Z",
            "end": "2025-01-15T12:00:00Z",
        }
        item = ScheduleItem(**data)  # type: ignore[ty:invalid-argument-type]
        item.post_processing(logging.getLogger())
        assert isinstance(item.start, dt)
        assert isinstance(item.end, dt)

    def test_schedule_item_is_live(self):
        """Test ScheduleItem.is_live() method."""
        now = dt.now(tz=pytz.UTC)
        item = ScheduleItem(
            id="test",
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=1),
        )
        assert item.is_live(pytz.UTC) is True

    def test_schedule_item_is_not_live_before_start(self):
        """Test ScheduleItem.is_live() returns False before the item starts."""
        now = dt.now(tz=pytz.UTC)
        item = ScheduleItem(
            id="test",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
        )
        assert item.is_live(pytz.UTC) is False

    def test_schedule_item_has_aired(self):
        """Test ScheduleItem.has_already_aired() method."""
        now = dt.now(tz=pytz.UTC)
        item = ScheduleItem(
            id="test",
            start=now - timedelta(hours=2),
            end=now - timedelta(hours=1),
        )
        assert item.has_already_aired(pytz.UTC) is True

    def test_schedule_item_has_not_aired(self):
        """Test ScheduleItem.has_already_aired() returns False for a future item."""
        now = dt.now(tz=pytz.UTC)
        item = ScheduleItem(
            id="test",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
        )
        assert item.has_already_aired(pytz.UTC) is False

    def test_playable_item_id_from_urn(self):
        """Test PlayableItem.item_id property with URN."""
        item = PlayableItem(
            id="test123", urn="urn:bbc:radio:episode:m001234", pid="p001234"
        )
        assert item.item_id == "m001234"

    def test_playable_item_id_fallback_to_pid(self):
        """Test PlayableItem.item_id property fallback to PID."""
        item = PlayableItem(id="test123", pid="p001234")
        assert item.item_id == "p001234"

    def test_container_item_id(self):
        """Test Container.item_id property."""
        container = Container(id="test123", urn="urn:bbc:radio:brand:b006wkqb")
        assert container.item_id == "b006wkqb"

    def test_menu_get_item(self):
        """Test Menu.get() method."""
        item1 = MenuItem(id="item1", title="Item 1")
        item2 = MenuItem(id="item2", title="Item 2")
        menu = Menu(sub_items=[item1, item2])

        result = menu.get("item1")
        assert result == item1
        assert result.title == "Item 1"

    def test_menu_get_nonexistent(self):
        """Test Menu.get() with non-existent item."""
        menu = Menu(sub_items=[MenuItem(id="item1", title="Item 1")])
        result = menu.get("nonexistent")
        assert result is None


class TestSegmentMusicServices:
    """Segment uris are parsed into URI objects and matched on id.

    NOTE: the uri entries below are hand-written, not captured from the API.
    Replace with a real /segments payload containing music-service links.
    """

    @staticmethod
    def _segment(uris):
        from sounds.models import Segment
        from sounds.parser import Parser

        data = {
            "type": "segment_item",
            "id": "p0pbhqfh",
            "urn": "urn:bbc:radio:segment:music:n9pdgz",
            "segment_type": "music",
            "titles": {"primary": "Artist", "secondary": "Track"},
            "image_url": None,
            "offset": {"start": 0, "end": 180, "now_playing": True},
            "uris": uris,
        }
        segment = Parser().parse_container({"data": [data]})
        assert isinstance(segment, list)
        assert isinstance(segment[0], Segment)
        return segment[0]

    def test_spotify_and_apple_urls(self):
        segment = self._segment(
            [
                {
                    "type": "commercial-music-service",
                    "id": "commercial-music-service-spotify",
                    "label": "Spotify",
                    "uri": "https://open.spotify.com/track/abc",
                },
                {
                    "type": "commercial-music-service",
                    "id": "commercial-music-service-apple",
                    "label": "Apple Music",
                    "uri": "https://music.apple.com/gb/album/xyz",
                },
            ]
        )
        assert segment.spotify_url == "https://open.spotify.com/track/abc"
        assert segment.apple_music_url == "https://music.apple.com/gb/album/xyz"
        assert segment.record_id == "n9pdgz"

    def test_no_music_services(self):
        segment = self._segment([])
        assert segment.spotify_url is None
        assert segment.apple_music_url is None


class TestPlayableItemDuration:
    """Programmes responses (e.g. get_by_pid) only carry the length under availability."""

    @staticmethod
    def _programme() -> dict:
        # Return a copy so we can manipulate the json between tests
        return copy.deepcopy(load_fixture("PROGRAMME_FROM_PID.json")["data"][0])

    def test_duration_falls_back_to_availability(self):
        data = self._programme()
        assert "duration" not in data

        item = parse(data)

        assert isinstance(item.duration, Duration)
        assert item.duration.value == data["availability"]["duration"]

    def test_top_level_duration_wins(self):
        data = self._programme()
        data["duration"] = {"label": "1 min", "value": 60}

        item = parse(data)

        assert item.duration.value == 60

    def test_no_duration_anywhere_stays_none(self):
        data = self._programme()
        del data["availability"]["duration"]

        item = parse(data)

        assert item.duration is None
