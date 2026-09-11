import os
from datetime import datetime as dt, timedelta

import pytest

from sounds.client import SoundsClient
from sounds.models import LiveStation, Schedule

pytestmark = pytest.mark.anyio


@pytest.fixture
def username():
    return os.getenv("USER")


@pytest.fixture
def password():
    return os.getenv("PASS")


@pytest.fixture
async def logged_in_client(username, password):
    yield SoundsClient(username=username, password=password)


@pytest.mark.api
class TestStationServiceIntegration:
    """Tests for station service against live API."""

    async def test_get_national_stations(self, real_sounds_client: SoundsClient):
        stations = await real_sounds_client.stations.get_stations()
        assert len(stations) == 30
        assert all(type(station) is LiveStation for station in stations)

    async def test_get_all_stations(self, real_sounds_client: SoundsClient):
        stations = await real_sounds_client.stations.get_stations(include_local=True)
        assert len(stations) == 71
        assert all(type(station) is LiveStation for station in stations)

    async def test_get_station(self, real_sounds_client: SoundsClient):
        station = await real_sounds_client.stations.get_station(
            "bbc_radio_four", include_stream=True, include_schedule=True
        )
        assert type(station) is LiveStation

    async def test_get_station_dash_stream(self, logged_in_client: SoundsClient):
        station = await logged_in_client.stations.get_station(
            "bbc_radio_one", include_stream=True
        )
        assert type(station) is LiveStation
        assert type(station.stream) is str
        assert "hls" in station.stream

    async def test_get_station_hls_stream(self, logged_in_client: SoundsClient):
        station = await logged_in_client.stations.get_station(
            "bbc_radio_one", include_stream=True, stream_format="hls"
        )
        assert type(station) is LiveStation
        assert type(station.stream) is str
        assert "hls" in station.stream

    async def test_get_station_schedule_today(self, real_sounds_client: SoundsClient):
        station = await real_sounds_client.stations.get_station(
            "bbc_radio_one", include_schedule=True
        )
        today = dt.now().date().strftime("%Y-%m-%d")
        assert type(station) is LiveStation
        assert type(station.schedule) is Schedule
        assert len(station.schedule.sub_items) > 0
        assert station.schedule.title == today

    async def test_get_station_schedule_date(self, real_sounds_client: SoundsClient):
        yesterday = (dt.now() - timedelta(days=1)).date().strftime("%Y-%m-%d")
        station = await real_sounds_client.stations.get_station(
            "bbc_radio_one", include_schedule=True, date=yesterday
        )
        assert type(station) is LiveStation
        assert type(station.schedule) is Schedule
        assert len(station.schedule.sub_items) > 0
        assert station.schedule.title == yesterday
