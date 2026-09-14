import logging
import os

import dotenv
import pytest

from sounds.client import SoundsClient
from sounds.endpoints import URLs
from sounds.exceptions import UnauthorisedError
from sounds.requests import build_url

logger = logging.getLogger(__name__)

dotenv.load_dotenv()


@pytest.fixture
async def client():
    return SoundsClient()


class TestHTTP:
    async def test_make_request_non_authenticated_endpoint(self, client):
        resp = await client.requests.make_request(
            method="GET",
            url=URLs.LIVE_STATION_DETAILS,
            url_args={"station_id": "bbc_radio_one"},
        )
        assert resp.status == 200

    async def test_make_request_authenticated_endpoint_without_credentials(
        self, client
    ):
        with pytest.raises(UnauthorisedError):
            await client.requests.make_request(method="GET", url=URLs.EXPERIENCE_MENU)

    async def test_make_request_authenticated_endpoint_with_credentials(self):
        client = SoundsClient(
            username=os.getenv("SOUNDS_USERNAME"), password=os.getenv("SOUNDS_PASSWORD")
        )

        try:
            await client.requests.make_request(method="GET", url=URLs.EXPERIENCE_MENU)
        except UnauthorisedError as e:
            pytest.fail(f"make_request() raised an UnauthorisedError unexpectedly: {e}")
