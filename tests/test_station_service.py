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

    async def test_get_stations_exclude_local(
        self, mock_session, mock_station
    ):
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

        result = await mock_station.get_stations(include_local=False)
        assert isinstance(result, list)
        assert [s.id for s in result] == ["national1"]

    async def test_get_stations_include_local(
        self, mock_session, mock_station
    ):
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

        result = await mock_station.get_stations(include_local=True)
        assert {s.id for s in result} == {"national1", "local1"}
        assert next(s for s in result if s.id == "national1").local is False
        assert next(s for s in result if s.id == "local1").local is True

    async def test_get_stations_respects_include_local_after_cache_populated(
        self, mock_session, mock_station
    ):
        """Once get_stations() has been called (and cached the result) with
        include_local=False, a subsequent call with include_local=True must
        still return local stations — not the stale cached national-only list.
        """

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

        first = await mock_station.get_stations(include_local=False)
        assert [s.id for s in first] == ["national1"]

        second = await mock_station.get_stations(include_local=True)
        assert {s.id for s in second} == {"national1", "local1"}
