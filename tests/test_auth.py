import time
from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest
from yarl import URL

from sounds.auth import AuthService, _get_form_action
from sounds.cookies import CookieStore
from sounds.exceptions import MultipleObjectsFound, NotFoundError, UnauthorisedError

ID, SESSION = "ckns_id", "ckns_atkn"
BBC = URL("https://www.bbc.co.uk")


class FakeBBC:
    """Stands in for BBC URLs."""

    def __init__(self, jar: aiohttp.CookieJar):
        self.jar = jar
        self.renew_grants_token = True
        self.login_error: Exception | None = None
        self.api_always_401 = False
        self.renews = self.logins = self.api_calls = 0

    def give(self, *names: str) -> None:
        self.jar.update_cookies({n: "v" for n in names}, response_url=BBC)

    async def renew(self, *args, **kwargs):  # patched in as requests.make_request
        self.renews += 1
        if self.renew_grants_token and any(c.key == ID for c in self.jar):
            self.give(SESSION)
        return Mock(status=200)

    async def login(self, username, password):  # patched in as auth.login
        self.logins += 1
        if self.login_error:
            raise self.login_error
        self.give(ID, SESSION)
        return True

    async def api(self):  # the protected call
        self.api_calls += 1
        if self.api_always_401 or not any(c.key == SESSION for c in self.jar):
            raise UnauthorisedError("401")
        return "ok"


MODES = {
    "signed_out": (),
    "identity_only": (ID,),  # A typical re-auth required situation
    "full_session": (ID, SESSION),
}


@pytest.fixture
async def bbc():
    return FakeBBC(aiohttp.CookieJar())


@pytest.fixture
async def clock():
    return time.monotonic


@pytest.fixture
def auth(bbc, clock, tmp_path):
    store = CookieStore(
        session=Mock(cookie_jar=bbc.jar),
        cookie_file_location=tmp_path / "sounds_jar",
        account_id="user",
    )
    requests = Mock(make_request=AsyncMock(side_effect=bbc.renew))
    service = AuthService(
        requests=requests, cookie_store=store, username="user", password="pass"
    )
    service.login = AsyncMock(side_effect=bbc.login)
    service._clock = clock
    return service


@pytest.mark.parametrize(
    ("mode", "renew_ok", "renews", "logins"),
    [
        ("signed_out", True, 0, 1),
        ("identity_only", True, 1, 0),
        ("identity_only", False, 1, 1),
        ("full_session", True, 0, 0),
    ],
)
async def test_retry_with_reauth_reaches_api(auth, bbc, mode, renew_ok, renews, logins):
    bbc.give(*MODES[mode])
    bbc.renew_grants_token = renew_ok

    assert await auth.retry_with_reauth(bbc.api) == "ok"
    assert (bbc.renews, bbc.logins) == (renews, logins)


class TestAuthHelpers:
    def test_getting_form_action_with_no_forms(self):
        html = ""
        with pytest.raises(NotFoundError):
            _get_form_action(html)

    def test_getting_form_action_with_form_with_no_action(self):
        html = "<form></form>"
        with pytest.raises(NotFoundError):
            _get_form_action(html)

    def test_getting_form_action_with_form_with_blank_action(self):
        html = "<form action=''></form>"
        with pytest.raises(NotFoundError):
            _get_form_action(html)

    def test_getting_form_action_with_single_form(self):
        html = "<form action='test.asp'></form>"
        action = _get_form_action(html)
        assert action == "test.asp"

    def test_getting_form_action_with_multiple_valid_forms(self):
        html = "<form action='test.asp'></form><form action='test2.asp'></form>"
        with pytest.raises(MultipleObjectsFound):
            _get_form_action(html)

    def test_getting_form_action_with_multiple_invalid_forms(self):
        html = "<form></form><form></form>"
        with pytest.raises(NotFoundError):
            _get_form_action(html)
