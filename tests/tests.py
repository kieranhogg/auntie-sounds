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


class TestIntegration:
    """Integration tests for the client"""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test SoundsClient initialization"""
        client = SoundsClient(timezone=pytz.UTC)
        assert client.timezone == pytz.UTC
        assert client.auth is not None
        assert client.stations is not None
        assert client.streaming is not None
        assert client.schedules is not None
        assert client.personal is not None
        await client.close()

    @pytest.mark.asyncio
    async def test_client_context_manager(self):
        """Test SoundsClient as context manager"""
        async with SoundsClient(timezone=pytz.UTC) as client:
            assert client is not None
        # Should be closed after context
