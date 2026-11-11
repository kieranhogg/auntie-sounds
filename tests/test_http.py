import pytest

from auntie_sounds.client import SoundsClient
from auntie_sounds.endpoints import Endpoints
from auntie_sounds.exceptions import InvalidArgumentsError
from auntie_sounds.requests import URL_BASE, build_url


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

    async def test_build_url_with_multiple_placeholders(self, client):
        url = build_url(
            url="/{one}{two}{three}",
            url_args={"one": "one", "two": "two", "three": "three"},
        )
        assert url == URL_BASE + "/onetwothree"
