import pytest

from sounds.client import SoundsClient
from sounds.endpoints import Endpoints
from sounds.exceptions import InvalidArgumentsError
from sounds.requests import URL_BASE, build_url


@pytest.fixture
async def client():
    return SoundsClient()


class TestHTTP:
    async def test_build_url(self, client):
        url = build_url(url=Endpoints.STATIONS)
        assert url == URL_BASE + Endpoints.STATIONS.value

    async def test_build_url_template_with_missing_values(self, client):
        with pytest.raises(
            InvalidArgumentsError,
            match="network_id is a required parameter for the URL, but it is not in url_args.",
        ):
            build_url(url=Endpoints.NETWORK_DETAILS)

    async def test_build_url_template(self, client):
        url = build_url(url=Endpoints.NETWORK_DETAILS, url_args={"network_id": "123"})
        assert url == URL_BASE + Endpoints.NETWORK_DETAILS.value.format(
            network_id="123"
        )
