import os
from datetime import datetime as dt
from datetime import timedelta

import pytest

from sounds.client import SoundsClient
from sounds.exceptions import ConfigurationError, NotFoundError
from sounds.models import LiveStation, Schedule

pytestmark = pytest.mark.anyio


@pytest.fixture
def username():
    username = os.getenv("USER")
    if not username:
        raise ConfigurationError("No username environment variable found.")
    return username


@pytest.fixture
def password():
    password = os.getenv("PASS")
    if not password:
        raise ConfigurationError("No password environment variable found.")
    return password


@pytest.fixture
async def logged_in_client(username, password):
    client = SoundsClient(username=username, password=password)
    await client.start()
    yield client


@pytest.fixture
async def anonymous_client(username, password):
    client = SoundsClient()
    await client.start()
    yield client


@pytest.mark.api
class TestStationServiceIntegration:
    """Tests for station service against live API."""

    async def test_get_national_stations(self, real_sounds_client: SoundsClient):
        stations = await real_sounds_client.stations.get_stations()
        assert len(stations) == 30
        assert all(type(station) is LiveStation for station in stations)

    async def test_get_all_stations(self, real_sounds_client: SoundsClient):
        stations = await real_sounds_client.stations.get_stations(
            include_local_stations=True
        )
        assert len(stations) == 71
        assert all(type(station) is LiveStation for station in stations)

    async def test_get_station(self, real_sounds_client: SoundsClient):
        station = await real_sounds_client.stations.get_station(
            "bbc_radio_one", include_stream=True, include_schedule=True
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
        today = dt.now(tz=real_sounds_client.timezone).date().strftime("%Y-%m-%d")
        assert type(station) is LiveStation
        assert type(station.schedule) is Schedule
        assert station.schedule.sub_items and len(station.schedule.sub_items) > 0
        assert station.schedule.title == today

    async def test_get_station_schedule_date(self, real_sounds_client: SoundsClient):
        yesterday = (
            (dt.now(tz=real_sounds_client.timezone) - timedelta(days=1))
            .date()
            .strftime("%Y-%m-%d")
        )
        station = await real_sounds_client.stations.get_station(
            "bbc_radio_one", include_schedule=True, date=yesterday
        )
        assert type(station) is LiveStation
        assert type(station.schedule) is Schedule
        assert station.schedule.sub_items and len(station.schedule.sub_items) > 0
        assert station.schedule.title == yesterday


class TestRadioFourIDConsistency:
    async def test_id_integration(self, anonymous_client, logged_in_client):
        """Test the flow of BBC Radio Four's IDs across the endpoints.

        Sounds API has the concept of Networks and Services/Stations. For almost all
        stations, these are the same. Radio Four is a notable exception, so this tests
        the flow of those IDs across the various endpoints to ensure we are expecting
        the rights ones.
        """
        stations = await anonymous_client.stations.get_stations()
        radio_four_from_stations = next(
            (station for station in stations if "bbc_radio_four" in station.id), None
        )
        assert radio_four_from_stations is not None
        assert radio_four_from_stations.id == "bbc_radio_fourfm"

        try:
            radio_four = await anonymous_client.stations.get_station(
                radio_four_from_stations.id, include_stream=True
            )
        except NotFoundError:
            pytest.fail()

        try:
            stream = await logged_in_client.playback.get_live_stream(
                station_id=radio_four.id
            )
        except NotFoundError:
            pytest.fail()

        assert stream is not None
        assert "m3u8" in stream
