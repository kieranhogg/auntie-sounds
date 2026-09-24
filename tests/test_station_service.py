from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.anyio


class TestStationService:
    """Tests for station service"""

    @staticmethod
    def _station_payload(station_id: str, urn: str) -> dict:
        """Build a minimal station node that parses as a LiveStation."""
        return {
            "type": "playable_item",
            "id": station_id,
            "urn": urn,
            "synopses": {"short": "A station"},
            "titles": {"primary": station_id},
        }

    async def test_get_stations_exclude_local(self, mock_session, mock_station):
        """Test getting stations excluding local stations."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(
            return_value={
                "data": [
                    {
                        "data": [
                            self._station_payload(
                                "national1", "urn:bbc:radio:network:radio1"
                            )
                        ]
                    },
                    {
                        "data": [
                            self._station_payload(
                                "local1", "urn:bbc:radio:network:local1"
                            )
                        ]
                    },
                ]
            }
        )
        mock_session.request = AsyncMock(return_value=mock_response)

        result = await mock_station.get_stations(include_local_stations=False)
        assert isinstance(result, list)
        assert [s.id for s in result] == ["national1"]
        assert len(result) == 1

    async def test_get_stations_include_local(self, mock_session, mock_station):
        """Test getting stations including local stations."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(
            return_value={
                "data": [
                    {
                        "data": [
                            self._station_payload(
                                "national1", "urn:bbc:radio:network:radio1"
                            )
                        ]
                    },
                    {
                        "data": [
                            self._station_payload(
                                "local1", "urn:bbc:radio:network:local1"
                            )
                        ]
                    },
                ]
            }
        )
        mock_session.request = AsyncMock(return_value=mock_response)

        result = await mock_station.get_stations(include_local_stations=True)
        assert {s.id for s in result} == {"national1", "local1"}
