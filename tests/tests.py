import pytest
import pytz

from sounds.client import SoundsClient


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
