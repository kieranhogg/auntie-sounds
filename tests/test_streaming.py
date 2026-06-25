from unittest.mock import AsyncMock

import pytest

from sounds.exceptions import APIResponseError

pytestmark = pytest.mark.anyio


class TestStreamingService:
    """Tests for streaming service"""

    async def test_get_best_stream_hls(self, mock_streaming_service):
        """Test getting best HLS stream"""

        streams = [
            {"transferFormat": "dash", "href": "https://example.com/dash"},
            {"transferFormat": "hls", "href": "https://example.com/hls"},
        ]

        result = mock_streaming_service.get_best_stream(streams, prefer_type="hls")
        assert result == "https://example.com/hls"

    async def test_get_best_stream_not_found(self, mock_streaming_service):
        """Test getting best stream when format not found"""

        streams = [
            {"transferFormat": "dash", "href": "https://example.com/dash"},
        ]

        result = mock_streaming_service.get_best_stream(streams, prefer_type="hls")
        assert result is None

    async def test_invalid_pid(
        self, mock_user, mock_logger, mock_session, mock_streaming_service
    ):
        """Test get_pid with an invalid PID"""
        mock_session.request = AsyncMock()
        mock_session.logger = mock_logger
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
        mock_user.is_uk_listener.return_value = True
        with pytest.raises(APIResponseError):
            await mock_streaming_service.get_by_pid("invalid pid")
