from unittest.mock import AsyncMock

import pytest

from sounds.exceptions import APIResponseError
from sounds.playback import get_best_stream

pytestmark = pytest.mark.anyio


class TestPlaybackService:
    """Tests for playback service."""

    async def test_get_best_stream_hls(self):
        """Test getting the best HLS stream."""

        streams = [
            {"transferFormat": "dash", "href": "https://example.com/dash"},
            {"transferFormat": "hls", "href": "https://example.com/hls"},
        ]

        result = get_best_stream(streams, prefer_type="hls")
        assert result == "https://example.com/hls"

    async def test_get_best_stream_not_found(self):
        """Test getting best stream when format not found."""

        streams = [
            {"transferFormat": "dash", "href": "https://example.com/dash"},
        ]

        result = get_best_stream(streams, prefer_type="hls")
        assert result is None



    async def test_invalid_pid(
        self, mock_user, mock_session, mock_content
    ):
        """Test get_pid with an invalid PID."""
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
        mock_user.is_uk_account_and_location.return_value = True
        with pytest.raises(APIResponseError):
            await mock_content.get_by_pid("invalid pid")
