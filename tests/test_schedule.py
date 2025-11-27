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

class TestScheduleService:
    """Tests for schedule service"""

    @pytest.mark.asyncio
    async def test_get_schedule_invalid_date_format(self, mock_session, mock_logger):
        """Test get_schedule with invalid date format"""
        service = ScheduleService(session=mock_session, logger=mock_logger)

        with pytest.raises(InvalidFormatError):
            await service.get_schedule("bbc_radio_one", date="2025/01/15")

    @pytest.mark.asyncio
    async def test_get_schedule_valid_date_format(self, mock_session, mock_logger):
        """Test get_schedule with valid date format"""
        mock_session.request = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(
            return_value={
                "data": [
                    {
                        "type": "inline_display_module",
                        "id": "schedule_items",
                        "data": [],
                    }
                ]
            }
        )
        mock_session.request.return_value = mock_response

        service = ScheduleService(session=mock_session, logger=mock_logger)

        # This should not raise an exception
        try:
            await service.get_schedule("bbc_radio_one", date="2025-01-15")
        except InvalidFormatError:
            pytest.fail("Valid date format raised InvalidFormatError")
