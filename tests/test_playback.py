from unittest.mock import AsyncMock

import pytest

from auntie_sounds.endpoints import URLs
from auntie_sounds.exceptions import APIResponseError
from auntie_sounds.playback import (
    StreamPreference,
    get_stream_variant,
    get_stream_variants,
)
from tests.conftest import make_response

pytestmark = pytest.mark.anyio


class TestPlaybackService:
    """Tests for playback service."""

    async def test_get_best_stream_hls(self):
        """Test getting the best HLS stream."""

        streams = [
            {"transferFormat": "dash", "href": "https://example.com/dash"},
            {"transferFormat": "hls", "href": "https://example.com/hls"},
        ]

        result = get_stream_variant(
            streams, preferences=StreamPreference(stream_type="hls")
        )
        assert result.get("href") == "https://example.com/hls"

    async def test_get_best_stream_not_found(self):
        """Test getting best stream when format not found."""

        streams = [
            {"transferFormat": "dash", "href": "https://example.com/dash"},
        ]

        result = get_stream_variant(
            streams, preferences=StreamPreference(stream_type="hls")
        )
        assert result is None

    async def test_invalid_pid(self, mock_user, mock_session, mock_content):
        """Test get_pid with an invalid PID."""
        mock_session.request = AsyncMock()
        mock_response = make_response()

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


def _connection(supplier, protocol, priority, transfer_format="hls"):
    return {
        "supplier": supplier,
        "protocol": protocol,
        "priority": str(priority),
        "transferFormat": transfer_format,
        "href": f"{protocol}://{supplier}/{priority}",
    }


MEDIASET_RESPONSE = {
    "media": [
        {"bitrate": "96", "connection": [_connection("akamai_uk", "https", 10)]},
        {
            "bitrate": "320",
            "connection": [
                _connection("akamai_uk", "http", 10),
                _connection("akamai_uk", "https", 10),
                _connection("cloudfront_uk", "http", 20),
                _connection("cloudfront_uk", "https", 20),
            ],
        },
    ]
}


class TestStreamVariants:
    """Tests for ranking mediaselector connections."""

    def test_protocol_beats_supplier_preference(self):
        connections = [
            _connection("akamai_uk", "http", 10),
            _connection("cloudfront_uk", "https", 20),
        ]
        result = get_stream_variant(
            connections, preferences=StreamPreference(supplier="akamai")
        )
        assert result["href"] == "https://cloudfront_uk/20"

    def test_one_variant_per_supplier_best_first(self):
        connections = MEDIASET_RESPONSE["media"][1]["connection"]
        result = get_stream_variants(connections, preferences=StreamPreference())
        assert [variant["href"] for variant in result] == [
            "https://akamai_uk/10",
            "https://cloudfront_uk/20",
        ]

    def test_no_matching_stream_type(self):
        connections = [_connection("akamai_uk", "https", 10, transfer_format="dash")]
        assert get_stream_variants(connections, preferences=StreamPreference()) == []


class TestStreamRequests:
    """Tests for the mediaselector requests made by PlaybackService."""

    async def test_live_streams_send_bearer_token(self, mock_playback):
        mock_playback.requests.get_json_response = AsyncMock(
            side_effect=[{"token": "abc"}, MEDIASET_RESPONSE]
        )

        result = await mock_playback.get_live_streams("bbc_radio_four")

        mediaset_call = mock_playback.requests.get_json_response.call_args_list[1]
        assert mediaset_call.kwargs["url"] is URLs.MEDIASET
        assert mediaset_call.kwargs["url_args"] == {"id": "bbc_radio_fourfm"}
        assert mediaset_call.kwargs["headers"] == {"Authorization": "Bearer abc"}
        assert result == ["https://akamai_uk/10", "https://cloudfront_uk/20"]

    async def test_episode_stream_uses_highest_bitrate_without_token(
        self, mock_playback
    ):
        mock_playback.requests.get_json_response = AsyncMock(
            return_value=MEDIASET_RESPONSE
        )

        result = await mock_playback.get_episode_stream("p0abc123")

        mock_playback.requests.get_json_response.assert_awaited_once_with(
            url=URLs.MEDIASET, url_args={"id": "p0abc123"}, headers=None
        )
        assert result == "https://akamai_uk/10"

    async def test_missing_media_raises(self, mock_playback):
        mock_playback.requests.get_json_response = AsyncMock(return_value={"media": []})

        with pytest.raises(APIResponseError):
            await mock_playback.get_episode_stream("p0abc123")
