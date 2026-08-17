import json
import logging
from logging import DEBUG
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest
import pytz
from yarl import URL

from sounds import URLs
from sounds.auth import AuthService
from sounds.client import SoundsClient
from sounds.constants import COOKIE_ID
from sounds.cookies import CookieStore
from sounds.requests import RequestManager
from sounds.schedule import ScheduleService
from sounds.streaming import StreamingService
from sounds.user import UserService

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def cookie_jar():
    jar = aiohttp.CookieJar()
    jar.update_cookies(
        {COOKIE_ID: "test"}, response_url=URL(URLs.COOKIE_BASE_I18N.value)
    )
    return jar


@pytest.fixture
def mock_session(cookie_jar):
    session = Mock(spec=aiohttp.ClientSession)

    session.cookie_jar = cookie_jar

    session.request = AsyncMock()
    session.close = AsyncMock()

    return session


@pytest.fixture
def mock_logger():
    logger = Mock(spec=logging.Logger)
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.log = Mock()
    logger.setLevel = Mock()
    return logger


@pytest.fixture
def logger():
    logger = logging.getLogger("testing")
    return logger


@pytest.fixture
def mock_cookie_store(mock_session, mock_logger):
    return CookieStore(
        session=mock_session, logger=mock_logger, cookie_file_location=Path()
    )


@pytest.fixture
def mock_schedule(mock_logger, mock_session):
    return ScheduleService(
        logger=mock_logger,
        session=mock_session,
    )


@pytest.fixture
def mock_auth_service(mock_session, mock_logger, mock_cookie_store):
    return AuthService(
        cookie_store=mock_cookie_store, session=mock_session, logger=mock_logger
    )


@pytest.fixture
def mock_requests(mock_logger, mock_auth_service, mock_cookie_store):
    return RequestManager(
        auth=mock_auth_service,
        cookie_store=mock_cookie_store,
        logger=mock_logger,
        username="user",
        password="password",
    )


@pytest.fixture
def mock_user(mock_session, mock_logger, monkeypatch):
    user = UserService(
        login_details_provided=True,
        session=mock_session,
        logger=mock_logger,
    )
    monkeypatch.setattr(user, "is_uk_listener", AsyncMock(return_value=True))
    return user


@pytest.fixture
def mock_streaming_service(
    mock_logger,
    mock_session,
    mock_auth_service,
    mock_schedule,
    mock_user,
    mock_requests,
):
    return StreamingService(
        session=mock_session,
        logger=mock_logger,
        auth=mock_auth_service,
        schedules=mock_schedule,
        user=mock_user,
        requests=mock_requests,
    )


@pytest.fixture
async def sounds_client(mock_session):
    client = SoundsClient(
        session=mock_session, timezone=pytz.timezone("UTC"), log_level=DEBUG
    )
    yield client
    await client.close()


@pytest.fixture
def sample_radio_series_data():
    return json.loads(open("tests/json/radio_series.json").read())


@pytest.fixture
def sample_network_data():
    return json.loads(open("tests/json/schedule.json").read())


@pytest.fixture
def sample_schedule_item_data():
    return {
        "type": "playable_item",
        "id": "m001234",
        "pid": "m001234",
        "urn": "urn:bbc:radio:episode:m001234",
        "titles": {"primary": "Test Show"},
        "synopses": {"short": "A test show"},
        "start": "2025-01-15T10:00:00Z",
        "end": "2025-01-15T12:00:00Z",
        "image_url": "https://example.com/{recipe}.{format}",
        "network": {"id": "bbc_radio_one", "short_title": "Radio 1"},
    }


@pytest.fixture
def sample_podcast_episode_data():
    return json.loads(open("tests/json/podcast.json").read())


@pytest.fixture
def sample_playable_item():
    return json.loads(open("tests/json/pid_playable.json").read())


@pytest.fixture
def sample_menu_data():
    return json.loads(open("tests/json/menu.json").read())
