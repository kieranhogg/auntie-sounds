from unittest.mock import AsyncMock

import pytest

from sounds.stations import StationService

pytestmark = pytest.mark.anyio


class TestStationService:
    """Tests for station service"""

    async def test_get_stations_exclude_local(self, mock_session, mock_logger):
        """Test getting stations excluding local stations"""
        mock_streaming = AsyncMock()
        mock_schedule = AsyncMock()

        service = StationService(
            session=mock_session,
            logger=mock_logger,
            streaming=mock_streaming,
            schedules=mock_schedule,
        )

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(
            return_value={
                "data": [
                    {
                        "data": [
                            {
                                "type": "playable_item",
                                "id": "national1",
                                "urn": "urn:bbc:radio:network:radio1",
                            }
                        ]
                    },
                    {
                        "data": [
                            {
                                "type": "playable_item",
                                "id": "local1",
                                "urn": "urn:bbc:radio:network:local1",
                            }
                        ]
                    },
                ]
            }
        )
        mock_session.request = AsyncMock(return_value=mock_response)

        result = await service.get_stations(include_local=False)
        assert isinstance(result, list)
