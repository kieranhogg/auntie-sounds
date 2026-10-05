import itertools
import json
import os
import shutil
from contextlib import AsyncExitStack
from logging import DEBUG
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest
from aioresponses import aioresponses
from yarl import URL

from sounds.auth import AuthService
from sounds.client import COOKIE_FILE, SoundsClient
from sounds.content import ContentService
from sounds.cookies import ID_COOKIE, CookieStore
from sounds.endpoints import URLs
from sounds.personal import PersonalService
from sounds.playback import PlaybackService
from sounds.requests import RequestManager
from sounds.schedule import ScheduleService
from sounds.stations import StationService
from sounds.user import UserService

pytestmark = pytest.mark.anyio

FIXTURES_FOLDER = Path(__file__).resolve().parent / "fixtures" / "api"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_FOLDER / name).read_text())


def make_response(status=200, json=None, text="", reason="OK"):
    resp = Mock(
        spec=aiohttp.ClientResponse, status=status, reason=reason, ok=status < 400
    )
    resp.json = AsyncMock(return_value=json)
    resp.text = AsyncMock(return_value=text)
    resp.read = AsyncMock(return_value=text.encode())
    return resp


@pytest.fixture
def mock_api(monkeypatch):
    """Hijacks any json requests and replaces them with the fixture response."""

    async def fake_request(self, url, *args, **kwargs):
        return json.loads((FIXTURES_FOLDER / f"{url.name}.json").read_text())

    monkeypatch.setattr(
        "sounds.requests.RequestManager.get_json_response", fake_request
    )


@pytest.fixture(scope="session")
def anyio_backend():
    # Session scope so session-scoped async fixtures (seed_jar) can run.
    return "asyncio"


@pytest.fixture(name="mock_session")
def _mock_session():
    session = Mock(spec=aiohttp.ClientSession)
    session.cookie_jar = AsyncMock(spec=aiohttp.CookieJar)
    session.request = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture(name="mock_cookie_store")
def _mock_cookie_store(mock_session):
    return CookieStore(session=mock_session, cookie_file_location=Path())


@pytest.fixture(name="mock_schedule")
def _mock_schedule(mock_session, mock_requests):
    return ScheduleService(
        requests=mock_requests,
    )


@pytest.fixture
def mock_auth_service(mock_requests, mock_cookie_store):
    return AuthService(requests=mock_requests, cookie_store=mock_cookie_store)


@pytest.fixture(name="mock_requests")
def _mock_requests(mock_session):
    return RequestManager(
        session=mock_session,
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


@pytest.fixture(name="mock_personal")
def _mock_personal(
    mock_auth_service,
    mock_requests,
):
    return PersonalService(
        auth=mock_auth_service,
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
        user=mock_user,
        requests=mock_requests,
        playback=mock_playback,
    )


@pytest.fixture(name="mock_personal_service")
def _mock_personal_service(
    mock_session,
    mock_auth_service,
    mock_schedule,
    mock_user,
    mock_requests,
    mock_playback,
    mock_content,
):
    return PersonalService(
        auth=mock_auth_service,
        requests=mock_requests,
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
        schedules=mock_schedule,
        requests=mock_requests,
        playback=mock_playback,
    )


@pytest.fixture(name="sounds_client")
async def _sounds_client(mock_session, tmp_path):
    client = SoundsClient(
        session=mock_session,
        cookie_file_location=tmp_path / "sounds_jar",
        log_level=DEBUG,
    )
    await client.start()
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


##### Client fixtures ##################################################################
FAKE_CREDENTIALS = ("fake-user", "fake-password")


@pytest.fixture(autouse=True)
def _forbid_default_jar(monkeypatch):
    """Fail if any test would touch the real user-data cookie jar."""
    for name in ("load", "save"):
        original = getattr(CookieStore, name)

        def guarded(self, _original=original, _name=name):
            if self.path is None or Path(self.path) == COOKIE_FILE:
                pytest.fail(f"CookieStore.{_name}() on default jar {COOKIE_FILE}")
            return _original(self)

        monkeypatch.setattr(CookieStore, name, guarded)


@pytest.fixture(scope="session")
def credentials() -> tuple[str, str]:
    username = os.getenv("SOUNDS_USERNAME")
    password = os.getenv("SOUNDS_PASSWORD")
    if not (username and password):
        pytest.skip("SOUNDS_USERNAME / SOUNDS_PASSWORD not set")
    return username, password


@pytest.fixture(scope="session")
async def seed_jar(credentials, tmp_path_factory) -> Path:
    """Log in once per session. Read-only: clients get copies."""
    path = tmp_path_factory.mktemp("seed") / "sounds_jar"
    username, password = credentials
    async with SoundsClient(
        username=username,
        password=password,
        cookie_file_location=path,
    ) as client:
        await client.login()
    return path


@pytest.fixture
async def fake_jar(tmp_path) -> Path:
    """A jar file holding a syntactically valid but bogus session cookie."""
    path = tmp_path / "fake_seed_jar"
    jar = aiohttp.CookieJar()
    jar.update_cookies(
        {ID_COOKIE: "fake-session"}, response_url=URL(URLs.COOKIE_BASE.value)
    )
    jar.save(path)
    return path


@pytest.fixture
def no_network():
    """Any request escaping the mock layer raises ClientConnectionError."""
    with aioresponses() as mocked:
        yield mocked


@pytest.fixture
async def make_client(tmp_path):
    """Every client gets its own jar path to prevent jar collisions in testing."""
    counter = itertools.count()

    async with AsyncExitStack() as stack:

        async def _make(
            *,
            credentials: tuple[str | None, str | None] = (None, None),
            seed: Path | None = None,
            mock: bool = False,
            session: aiohttp.ClientSession | None = None,
        ) -> SoundsClient:
            path = tmp_path / f"sounds_jar_{next(counter)}"
            if seed is not None:
                shutil.copy(seed, path)
            username, password = credentials
            client = SoundsClient(
                username=username,
                password=password,
                session=session,
                cookie_file_location=path,
            )
            return await stack.enter_async_context(client)

        yield _make


@pytest.fixture(name="real_client")
async def _real_client(make_client, credentials, seed_jar) -> SoundsClient:
    return await make_client(credentials=credentials, seed=seed_jar)


@pytest.fixture(name="real_anonymous_client")
async def _real_anonymous_client(make_client) -> SoundsClient:
    return await make_client()


@pytest.fixture
async def real_client_fake_jar(make_client, fake_jar) -> SoundsClient:
    return await make_client(credentials=FAKE_CREDENTIALS, seed=fake_jar)


@pytest.fixture
async def mock_client(make_client) -> SoundsClient:
    return await make_client(mock=True)


@pytest.fixture
async def mock_client_fake_jar(make_client, fake_jar, no_network) -> SoundsClient:
    return await make_client(credentials=FAKE_CREDENTIALS, seed=fake_jar, mock=True)
