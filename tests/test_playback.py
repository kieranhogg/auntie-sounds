import pytest

pytestmark = pytest.mark.anyio


class TestStreamingService:
    """Tests for streaming service."""

    async def test_get_best_stream_hls(self, mock_playback):
        """Test getting the best HLS stream."""

        streams = [
            {"transferFormat": "dash", "href": "https://example.com/dash"},
            {"transferFormat": "hls", "href": "https://example.com/hls"},
        ]

        result = mock_playback.get_best_stream(streams, prefer_type="hls")
        assert result == "https://example.com/hls"

    async def test_get_best_stream_not_found(self, mock_playback):
        """Test getting best stream when format not found."""

        streams = [
            {"transferFormat": "dash", "href": "https://example.com/dash"},
        ]

        result = mock_playback.get_best_stream(streams, prefer_type="hls")
        assert result is None

