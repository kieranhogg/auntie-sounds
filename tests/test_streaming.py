from unittest.mock import AsyncMock

import pytest

from sounds.exceptions import APIResponseError
from sounds.streaming import StreamingService


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
            auth=mock_auth,
            schedules=mock_schedule,
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
            auth=mock_auth,
            schedules=mock_schedule,
        )

        streams = [
            {"transferFormat": "dash", "href": "https://example.com/dash"},
        ]

        result = service.get_best_stream(streams, prefer_type="hls")
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_pid(self, mock_session, mock_logger):
        """Test get_pid with an invalid PID"""
        mock_session.request = AsyncMock()
        mock_response = AsyncMock()
        mock_auth = AsyncMock()
        mock_schedule = AsyncMock()

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

        service = StreamingService(
            session=mock_session,
            logger=mock_logger,
            auth=mock_auth,
            schedules=mock_schedule,
        )

        with pytest.raises(APIResponseError):
            await service.get_by_pid("invalid pid")
