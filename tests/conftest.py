import json
from logging import DEBUG
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest
import pytz
from yarl import URL

from sounds.auth import AuthService
from sounds.client import SoundsClient
from sounds.content import ContentService
from sounds.cookies import COOKIE_ID, CookieStore
from sounds.endpoints import URLs
from sounds.playback import PlaybackService
from sounds.requests import RequestManager
from sounds.schedule import ScheduleService
from sounds.stations import StationService
from sounds.user import UserService

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(name="cookie_jar")
async def _cookie_jar():
    jar = aiohttp.CookieJar()
    jar.update_cookies(
        {COOKIE_ID: "test"}, response_url=URL(URLs.COOKIE_BASE_I18N.value)
    )
    return jar


@pytest.fixture(name="mock_session")
def _mock_session(cookie_jar):
    session = Mock(spec=aiohttp.ClientSession)
    session.cookie_jar = cookie_jar
    session.request = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture(name="mock_cookie_store")
def _mock_cookie_store(mock_session):
    return CookieStore(session=mock_session, cookie_file_location=Path())


@pytest.fixture(name="mock_schedule")
def _mock_schedule(mock_session, mock_requests):
    return ScheduleService(
        session=mock_session,
        requests=mock_requests,
    )


@pytest.fixture
def mock_auth_service(sounds_client):
    return AuthService(sounds_client)


@pytest.fixture(name="mock_requests")
def _mock_requests(sounds_client):
    return RequestManager(
        sounds_client,
        username="user",
        password="password",
    )


@pytest.fixture(name="mock_user")
def _mock_user(mock_session, mock_requests, monkeypatch):
    user = UserService(
        requests=mock_requests,
        login_details_provided=True,
        session=mock_session,
    )
    monkeypatch.setattr(
        user, "is_uk_account_and_location", AsyncMock(return_value=True)
    )
    return user


@pytest.fixture(name="mock_playback")
def _mock_playback(
    mock_session,
    mock_auth_service,
    mock_schedule,
    mock_user,
    mock_requests,
):
    return PlaybackService(
        session=mock_session,
        auth=mock_auth_service,
        schedules=mock_schedule,
        user=mock_user,
        requests=mock_requests,
    )


@pytest.fixture(name="mock_content")
def _mock_content(
    mock_session,
    mock_auth_service,
    mock_schedule,
    mock_user,
    mock_requests,
    mock_playback,
):
    return ContentService(
        session=mock_session,
        auth=mock_auth_service,
        schedules=mock_schedule,
        user=mock_user,
        requests=mock_requests,
        playback=mock_playback,
    )


@pytest.fixture(name="mock_station")
def _mock_station(
    mock_session,
    mock_auth_service,
    mock_schedule,
    mock_user,
    mock_requests,
    mock_playback,
    mock_content,
):
    return StationService(
        session=mock_session,
        auth=mock_auth_service,
        schedules=mock_schedule,
        user=mock_user,
        requests=mock_requests,
        playback=mock_playback,
        content=mock_content,
    )


@pytest.fixture(name="sounds_client")
async def _sounds_client(mock_session):
    client = SoundsClient(
        session=mock_session, timezone=pytz.timezone("UTC"), log_level=DEBUG
    )
    yield client
    await client.close()


@pytest.fixture
def sample_radio_series_data():
    return json.loads(open("tests/fixtures/api/radio_series.json").read())


@pytest.fixture
def sample_network_data():
    return json.loads(open("tests/fixtures/api/schedule.json").read())


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
    return json.loads(open("tests/fixtures/api/podcast.json").read())


@pytest.fixture
def sample_playable_item():
    return json.loads(open("tests/fixtures/api/pid_playable.json").read())


@pytest.fixture
def sample_menu_data():
    return json.loads(open("tests/fixtures/api/EXPERIENCE_MENU.json").read())
