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


class TestStreamingService:
    """Tests for streaming service"""

    @pytest.mark.asyncio
    async def test_get_best_stream_hls(self, mock_session, mock_logger):
        """Test getting best HLS stream"""
        mock_auth = AsyncMock()
        mock_schedule = AsyncMock()

        service = StreamingService(
            session=mock_session,
            logger=mock_logger,
            auth_service=mock_auth,
            schedule_service=mock_schedule,
        )

        streams = [
            {"transferFormat": "dash", "href": "https://example.com/dash"},
            {"transferFormat": "hls", "href": "https://example.com/hls"},
        ]

        result = service.get_best_stream(streams, prefer_type="hls")
        assert result == "https://example.com/hls"

    @pytest.mark.asyncio
    async def test_get_best_stream_not_found(self, mock_session, mock_logger):
        """Test getting best stream when format not found"""
        mock_auth = AsyncMock()
        mock_schedule = AsyncMock()

        service = StreamingService(
            session=mock_session,
            logger=mock_logger,
            auth_service=mock_auth,
            schedule_service=mock_schedule,
        )

        streams = [
            {"transferFormat": "dash", "href": "https://example.com/dash"},
        ]

        result = service.get_best_stream(streams, prefer_type="hls")
        assert result is None
