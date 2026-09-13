import logging

import pytest

from sounds.client import SoundsClient
from sounds.endpoints import URLs
from sounds.exceptions import UnauthorisedError
from sounds.requests import build_url

logger = logging.getLogger(__name__)


@pytest.fixture
async def client():
    return SoundsClient()


class TestHTTP:
    async def test_make_request_non_authenticated_endpoint(self, client):
        resp = await client.requests.make_request(
            method="GET",
            url=build_url(
                URLs.LIVE_STATION_DETAILS, url_args={"station_id": "bbc_radio_one"}
            ),
        )
        assert resp.status == 200

    async def test_make_request_authenticated_endpoint_without_credentials(
        self, client
    ):
        with pytest.raises(UnauthorisedError):
            await client.requests.make_request(
                method="GET",
                url=build_url(URLs.EXPERIENCE_MENU),
            )
