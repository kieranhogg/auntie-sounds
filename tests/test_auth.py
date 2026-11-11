import asyncio
import time
from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest
from yarl import URL

from auntie_sounds.auth import AuthService, _get_form_action
from auntie_sounds.cookies import CookieStore
from auntie_sounds.exceptions import (
    CredentialsRejectedError,
    InvalidArgumentsError,
    LoginFailedError,
    MultipleObjectsFound,
    NetworkError,
    NotFoundError,
    SoundsException,
    UnauthorisedError,
)

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
class TestCoreAuth:
    async def test_retry_with_reauth_reaches_api(
        self, auth, bbc, mode, renew_ok, renews, logins
    ):
        bbc.give(*MODES[mode])
        bbc.renew_grants_token = renew_ok

        assert await auth.retry_with_reauth(bbc.api) == "ok"
        assert (bbc.renews, bbc.logins) == (renews, logins)


class TestRetryOn401:
    """A request that 401s escalates: renew if signed in, else log in, then retry."""

    async def test_retry_with_reauth_returns_call_result_without_reauth(
        self, mock_auth_service
    ):
        mock_auth_service.username = "user"
        mock_auth_service.password = "pass"
        call = AsyncMock(return_value="ok")

        result = await mock_auth_service.retry_with_reauth(call)

        assert result == "ok"
        call.assert_awaited_once()

    @pytest.mark.parametrize("credentials", [(None, None), ("", "")])
    async def test_missing_credentials_raise_without_logging_in(
        self, mock_auth_service, monkeypatch, credentials
    ):
        mock_auth_service.username, mock_auth_service.password = credentials
        login = AsyncMock()
        monkeypatch.setattr(mock_auth_service, "login", login)
        call = AsyncMock(side_effect=UnauthorisedError("expired"))

        with pytest.raises(InvalidArgumentsError):
            await mock_auth_service.retry_with_reauth(call)
        login.assert_not_called()

    async def test_retry_with_reauth_renews_session_when_cookie_present(
        self, mock_auth_service, monkeypatch
    ):

        mock_auth_service.username = "user"
        mock_auth_service.password = "pass"
        mock_auth_service.cookie_store = Mock(is_signed_in=True)
        monkeypatch.setattr(
            mock_auth_service, "renew_session", AsyncMock(return_value=True)
        )
        login = AsyncMock()
        monkeypatch.setattr(mock_auth_service, "login", login)
        call = AsyncMock(side_effect=[UnauthorisedError("expired"), "ok"])

        result = await mock_auth_service.retry_with_reauth(call)

        assert result == "ok"
        mock_auth_service.renew_session.assert_awaited_once()
        login.assert_not_called()

    async def test_retry_with_reauth_falls_back_to_full_login_when_renewal_fails(
        self, mock_auth_service, monkeypatch
    ):
        mock_auth_service.username = "user"
        mock_auth_service.password = "pass"
        mock_auth_service.cookie_store = Mock(is_signed_in=True)
        monkeypatch.setattr(
            mock_auth_service, "renew_session", AsyncMock(return_value=False)
        )
        login = AsyncMock()
        monkeypatch.setattr(mock_auth_service, "login", login)
        call = AsyncMock(
            side_effect=[
                UnauthorisedError("expired"),
                "ok",
            ]
        )

        result = await mock_auth_service.retry_with_reauth(call)

        assert result == "ok"
        login.assert_awaited_once_with(username="user", password="pass")

    async def test_retry_with_reauth_logs_in_directly_without_cookie(
        self, mock_auth_service, monkeypatch
    ):
        mock_auth_service.username = "user"
        mock_auth_service.password = "pass"
        mock_auth_service.cookie_store = Mock(is_signed_in=False)
        renew = AsyncMock()
        monkeypatch.setattr(mock_auth_service, "renew_session", renew)
        login = AsyncMock()
        monkeypatch.setattr(mock_auth_service, "login", login)
        call = AsyncMock(side_effect=[UnauthorisedError("expired"), "ok"])

        result = await mock_auth_service.retry_with_reauth(call)

        assert result == "ok"
        renew.assert_not_called()
        login.assert_awaited_once_with(username="user", password="pass")

    async def test_retry_with_reauth_raises_if_still_unauthorised_after_login(
        self, mock_auth_service, monkeypatch
    ):
        mock_auth_service.username = "user"
        mock_auth_service.password = "pass"
        mock_auth_service.cookie_store = Mock(is_signed_in=False)
        monkeypatch.setattr(mock_auth_service, "login", AsyncMock())
        call = AsyncMock(
            side_effect=[UnauthorisedError("expired"), UnauthorisedError("still bad")]
        )
        with pytest.raises(UnauthorisedError):
            await mock_auth_service.retry_with_reauth(call)

        mock_auth_service.login.assert_awaited_once()
        assert call.await_count == 2


class TestReauthConcurrency:
    @pytest.mark.parametrize("renew_ok", [False, True])
    async def test_concurrent_401s_share_one_reauth(
        self, mock_auth_service, monkeypatch, renew_ok
    ):
        """renew_ok=True covers renewal reporting success while the session is dead."""
        mock_auth_service.username = "user"
        mock_auth_service.password = "pass"
        mock_auth_service.cookie_store = Mock(is_signed_in=True)
        state = {"valid": False}

        async def renew():
            await asyncio.sleep(0.01)
            return renew_ok

        async def login(username, password):
            await asyncio.sleep(0.02)
            state["valid"] = True

        renew_mock = AsyncMock(side_effect=renew)
        login_mock = AsyncMock(side_effect=login)
        monkeypatch.setattr(mock_auth_service, "renew_session", renew_mock)
        monkeypatch.setattr(mock_auth_service, "login", login_mock)

        async def call():
            await asyncio.sleep(0)
            if not state["valid"]:
                raise UnauthorisedError("401")
            return "ok"

        results = await asyncio.gather(
            *[mock_auth_service.retry_with_reauth(call) for _ in range(4)]
        )
        assert results == ["ok"] * 4
        assert renew_mock.await_count == 1
        assert login_mock.await_count == 1

    async def test_concurrent_failed_login_is_attempted_once(
        self, mock_auth_service, monkeypatch
    ):
        mock_auth_service.username = "user"
        mock_auth_service.password = "wrong"
        mock_auth_service.cookie_store = Mock(is_signed_in=False)

        async def login(username, password):
            await asyncio.sleep(0.01)
            raise LoginFailedError("That password isn't right")

        login_mock = AsyncMock(side_effect=login)
        monkeypatch.setattr(mock_auth_service, "login", login_mock)
        call = AsyncMock(side_effect=UnauthorisedError("401"))

        results = await asyncio.gather(
            *[mock_auth_service.retry_with_reauth(call) for _ in range(4)],
            return_exceptions=True,
        )

        assert all(isinstance(r, LoginFailedError) for r in results)
        assert login_mock.await_count == 1
        # waiters chain to the original failure
        chained = [r for r in results if r.__cause__ is not None]
        assert len(chained) == 3
        assert all("password" in str(r.__cause__) for r in chained)

    async def test_later_request_retries_after_backoff(
        self, mock_auth_service, monkeypatch
    ):
        now = [0.0]
        mock_auth_service._clock = lambda: now[0]
        mock_auth_service.username = "user"
        mock_auth_service.password = "pass"
        mock_auth_service.cookie_store = Mock(is_signed_in=False)
        login = AsyncMock(side_effect=[NetworkError("down"), None])
        monkeypatch.setattr(mock_auth_service, "login", login)

        with pytest.raises(NetworkError):
            await mock_auth_service.retry_with_reauth(
                AsyncMock(side_effect=UnauthorisedError("401"))
            )
        now[0] += mock_auth_service.FAILURE_BACKOFF_INITIAL
        result = await mock_auth_service.retry_with_reauth(
            AsyncMock(side_effect=[UnauthorisedError("401"), "ok"])
        )

        assert result == "ok"
        assert login.await_count == 2


class TestRenewSession:
    @pytest.mark.parametrize(
        "error",
        [
            UnauthorisedError("401"),
            SoundsException("Request failed: 403"),
            NetworkError("Connection failed"),
            TimeoutError(),
            aiohttp.ClientPayloadError("truncated"),
        ],
    )
    async def test_renewal_failure_returns_false(
        self, mock_auth_service, monkeypatch, error
    ):
        monkeypatch.setattr(
            mock_auth_service.requests, "make_request", AsyncMock(side_effect=error)
        )
        assert await mock_auth_service.renew_session() is False

    async def test_non_401_renewal_failure_falls_back_to_login(
        self, mock_auth_service, monkeypatch
    ):
        mock_auth_service.username = "user"
        mock_auth_service.password = "pass"
        mock_auth_service.cookie_store = Mock(is_signed_in=True)
        monkeypatch.setattr(
            mock_auth_service.requests,
            "make_request",
            AsyncMock(side_effect=SoundsException("Request failed: 403")),
        )
        login = AsyncMock()
        monkeypatch.setattr(mock_auth_service, "login", login)
        call = AsyncMock(side_effect=[UnauthorisedError("401"), "ok"])

        assert await mock_auth_service.retry_with_reauth(call) == "ok"
        login.assert_awaited_once_with(username="user", password="pass")


class TestAuthenticate:
    async def test_stale_cookie_falls_back_to_login(
        self, mock_auth_service, monkeypatch
    ):
        mock_auth_service.username = "user"
        mock_auth_service.password = "pass"
        mock_auth_service.cookie_store = Mock(is_signed_in=True, has_access_token=False)
        monkeypatch.setattr(
            mock_auth_service, "renew_session", AsyncMock(return_value=False)
        )
        login = AsyncMock()
        monkeypatch.setattr(mock_auth_service, "login", login)

        await mock_auth_service.authenticate()
        mock_auth_service.renew_session.assert_awaited_once()
        login.assert_awaited_once_with(username="user", password="pass")

    async def test_shares_in_flight_reauth(self, mock_auth_service, monkeypatch):
        mock_auth_service.username = "user"
        mock_auth_service.password = "pass"
        mock_auth_service.cookie_store = Mock(is_signed_in=False)

        async def login(username, password):
            await asyncio.sleep(0.01)

        login_mock = AsyncMock(side_effect=login)
        monkeypatch.setattr(mock_auth_service, "login", login_mock)
        call = AsyncMock(side_effect=[UnauthorisedError("401"), "ok"])

        await asyncio.gather(
            mock_auth_service.retry_with_reauth(call),
            mock_auth_service.authenticate(),
        )

        assert login_mock.await_count == 1


def _always_401():
    return AsyncMock(side_effect=UnauthorisedError("401"))


@pytest.fixture
def fake_clock(mock_auth_service):
    now = [0.0]
    mock_auth_service._clock = lambda: now[0]
    return now


@pytest.fixture
def mocked_auth(mock_auth_service, fake_clock):
    mock_auth_service.username = "user"
    mock_auth_service.password = "pass"
    mock_auth_service.cookie_store = Mock(is_signed_in=False, has_access_token=False)
    mock_auth_service.renew_session = AsyncMock(return_value=True)
    mock_auth_service.login = AsyncMock()
    return mock_auth_service


class TestLoginPolicy:
    async def test_permanent_401_logs_in_at_most_once_per_interval(
        self, mocked_auth, fake_clock
    ):
        mocked_auth.cookie_store = Mock(is_signed_in=True)

        for _ in range(3):
            with pytest.raises(UnauthorisedError):
                await mocked_auth.retry_with_reauth(_always_401())
        assert mocked_auth.renew_session.await_count == 1
        assert mocked_auth.login.await_count == 1

        fake_clock[0] += mocked_auth.MIN_LOGIN_INTERVAL
        with pytest.raises(UnauthorisedError):
            await mocked_auth.retry_with_reauth(_always_401())
        assert mocked_auth.login.await_count == 2

    async def test_rejected_credentials_are_sticky(self, mocked_auth, fake_clock):
        mocked_auth.login.side_effect = CredentialsRejectedError(
            "That password isn't right"
        )

        for _ in range(5):
            with pytest.raises(CredentialsRejectedError):
                await mocked_auth.retry_with_reauth(_always_401())
            fake_clock[0] += 3600
        assert mocked_auth.login.await_count == 1

    async def test_changed_credentials_clear_rejection(self, mocked_auth):
        mocked_auth.login.side_effect = [CredentialsRejectedError("bad"), None]
        with pytest.raises(CredentialsRejectedError):
            await mocked_auth.retry_with_reauth(_always_401())

        mocked_auth.password = "new"
        call = AsyncMock(side_effect=[UnauthorisedError("401"), "ok"])
        assert await mocked_auth.retry_with_reauth(call) == "ok"
        mocked_auth.login.assert_awaited_with(username="user", password="new")

    async def test_explicit_authenticate_bypasses_rejection(self, mocked_auth):
        mocked_auth.cookie_store = Mock(
            spec=CookieStore, is_signed_in=False, has_access_token=False
        )
        mocked_auth.login.side_effect = [CredentialsRejectedError("bad"), None]
        with pytest.raises(CredentialsRejectedError):
            await mocked_auth.retry_with_reauth(_always_401())

        await mocked_auth.authenticate()
        assert mocked_auth.login.await_count == 2

    async def test_explicit_authenticate_bypasses_login_interval(self, mocked_auth):
        await mocked_auth.authenticate()
        await mocked_auth.authenticate()
        assert mocked_auth.login.await_count == 2

    async def test_transient_failure_backs_off_exponentially(
        self, mocked_auth, fake_clock
    ):
        mocked_auth.login.side_effect = [
            NetworkError("down"),
            NetworkError("down"),
            None,
        ]
        initial = mocked_auth.FAILURE_BACKOFF_INITIAL

        with pytest.raises(NetworkError):
            await mocked_auth.retry_with_reauth(_always_401())
        with pytest.raises(NetworkError):  # blocked, no attempt
            await mocked_auth.retry_with_reauth(_always_401())
        assert mocked_auth.login.await_count == 1

        fake_clock[0] += initial
        with pytest.raises(NetworkError):  # second attempt fails, backoff doubles
            await mocked_auth.retry_with_reauth(_always_401())
        fake_clock[0] += initial
        with pytest.raises(NetworkError):  # still blocked
            await mocked_auth.retry_with_reauth(_always_401())
        assert mocked_auth.login.await_count == 2

        fake_clock[0] += initial
        call = AsyncMock(side_effect=[UnauthorisedError("401"), "ok"])
        assert await mocked_auth.retry_with_reauth(call) == "ok"
        assert mocked_auth.login.await_count == 3
        assert mocked_auth._backoff == initial

    async def test_login_timeout_is_normalised_and_shared(self, mocked_auth):
        async def login(username, password):
            await asyncio.sleep(0.01)
            raise TimeoutError

        mocked_auth.login.side_effect = login
        results = await asyncio.gather(
            *[mocked_auth.retry_with_reauth(_always_401()) for _ in range(4)],
            return_exceptions=True,
        )

        assert all(isinstance(r, NetworkError) for r in results)
        assert mocked_auth.login.await_count == 1

    async def test_renewal_timeout_falls_back_to_login(self, mocked_auth, monkeypatch):
        mocked_auth.cookie_store = Mock(is_signed_in=True)
        del mocked_auth.renew_session  # use the real method
        monkeypatch.setattr(
            mocked_auth.requests, "make_request", AsyncMock(side_effect=TimeoutError)
        )
        call = AsyncMock(side_effect=[UnauthorisedError("401"), "ok"])

        assert await mocked_auth.retry_with_reauth(call) == "ok"
        mocked_auth.login.assert_awaited_once()


class TestLoginInternals:
    async def test_callback_failure_does_not_fail_login(
        self, mock_auth_service, monkeypatch
    ):
        mock_auth_service.cookie_store = Mock(is_signed_in=True)
        mock_auth_service._on_login_success = Mock(side_effect=OSError("read-only"))
        monkeypatch.setattr(
            mock_auth_service, "_get_login_form", AsyncMock(return_value="a")
        )
        monkeypatch.setattr(
            mock_auth_service, "_submit_username", AsyncMock(return_value="b")
        )
        monkeypatch.setattr(
            mock_auth_service, "_do_login", AsyncMock(return_value=True)
        )

        assert await mock_auth_service.login("user", "pass") is True

    @pytest.mark.parametrize(
        ("origin", "location", "expected"),
        [
            (
                "https://session.bbc.co.uk/session",
                "/auth/start?x=1",
                "https://session.bbc.co.uk/auth/start?x=1",
            ),
            (
                "https://account.bbc.com/auth/identifier/signin?a=1",
                "/auth/identifier/signin?x=1",
                "https://account.bbc.com/auth?x=1",
            ),
            (
                "https://session.bbc.co.uk/session",
                "https://account.bbc.com/auth?x=1",
                "https://account.bbc.com/auth?x=1",
            ),
        ],
    )
    async def test_login_form_redirects_resolve_relative_locations(
        self, mock_auth_service, monkeypatch, origin, location, expected
    ):
        redirect = Mock(status=302, headers={"Location": location}, url=URL(origin))
        page = Mock(status=200, ok=True, headers={}, url=URL(expected))
        page.text = AsyncMock(return_value="<form action='/do'></form>")
        make_request = AsyncMock(side_effect=[redirect, page])
        monkeypatch.setattr(mock_auth_service.requests, "make_request", make_request)

        await mock_auth_service._get_login_form()

        assert make_request.await_args_list[1].kwargs["url"] == expected


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
