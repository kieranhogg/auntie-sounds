import pytest

from sounds.client import SoundsClient
from sounds.endpoints import URLs
from sounds.exceptions import InvalidArgumentsError
from sounds.requests import build_url


@pytest.fixture
async def client():
    return SoundsClient()


class TestHTTP:
    async def test_build_url(self, client):
        url = build_url(url=URLs.STATIONS)
        assert url == URLs.STATIONS.value

    async def test_build_url_template_with_missing_values(self, client):
        with pytest.raises(InvalidArgumentsError, match="station_id is a required parameter for the URL, but it is not in url_args."):
            build_url(url=URLs.LIVE_STATION_DETAILS)

    async def test_build_url_template(self, client):
        url = build_url(url=URLs.LIVE_STATION_DETAILS, url_args={"station_id": "123"})
        assert url == URLs.LIVE_STATION_DETAILS.value.format(station_id="123")