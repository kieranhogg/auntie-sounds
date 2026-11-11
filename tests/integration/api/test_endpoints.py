import logging
from asyncio import sleep
from datetime import datetime as dt

import pytest

from auntie_sounds import SCHEDULE_TIMEZONE
from auntie_sounds.endpoints import Endpoints

TODAY = dt.now(SCHEDULE_TIMEZONE).strftime("%Y-%m-%d")

logger = logging.getLogger(__name__)

ENDPOINT_ARGS = {
    Endpoints.PLAY_EXPERIENCE: {"service_id": "bbc_radio_one"},
    Endpoints.SCHEDULE: {"service_id": "bbc_radio_one"},
    Endpoints.SCHEDULE_DATE: {"service_id": "bbc_radio_one", "date": TODAY},
    Endpoints.SEGMENTS: {"vpid": "m000lm9y"},
    Endpoints.LATEST_TRACKS: {"station_id": "bbc_radio_one"},
    Endpoints.NOW_PLAYING: {"service_id": "bbc_radio_one"},
    Endpoints.NETWORK_DETAILS: {"network_id": "bbc_radio_one"},
    Endpoints.NETWORK_PROMOS: {"network_id": "bbc_radio_one"},
    Endpoints.NETWORK_PROMOS_PLAYABLE: {"network_id": "bbc_radio_one"},
    Endpoints.NETWORK_PLAYABLE_DETAILS: {"network_id": "bbc_radio_one"},
    Endpoints.BROADCASTS: {"service_id": "bbc_radio_one"},
    Endpoints.BROADCAST_SCHEDULE: {"service_id": "bbc_radio_one", "date": TODAY},
    Endpoints.STATION_DETAILS: {"station_id": "bbc_radio_one"},
    Endpoints.STATION_PLAYABLE_DETAILS: {"station_id": "bbc_radio_one"},
    Endpoints.CONTAINER_FROM_PIDS: {"pids": "m000lm9z"},
    Endpoints.SERIES_EPISODES: {"pids": "m000lm9z"},
    Endpoints.BROADCAST: {"pid": "m000lm9z"},
    Endpoints.PROGRAMME_FROM_PID: {"pid": "m000lm9y"},
    Endpoints.PROGRAMME_FROM_PID_PLAYABLE: {"pid": "m000lm9y"},
    Endpoints.URN_CONTAINER: {"urn": "urn:bbc:radio:brand:p0jtptvc"},
    Endpoints.PID_DETAILS: {"pid": "m000lm9y"},
    Endpoints.CURATIONS: {"pid": "m000lm9y"},
    Endpoints.TAGGED: {"tag": "focus"},
}

PUBLIC_ENDPOINTS = [url for url in Endpoints if not url.login_required]


@pytest.mark.api
@pytest.mark.slow
class TestEndpoints:
    @pytest.mark.parametrize("url", PUBLIC_ENDPOINTS, ids=lambda url: url.name)
    async def test_public_endpoint(self, real_anonymous_client, url):
        args = ENDPOINT_ARGS.get(url, {})
        await real_anonymous_client.requests.get_json_response(url, url_args=args)
        await sleep(1)
