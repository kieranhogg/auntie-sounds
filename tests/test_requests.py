from unittest.mock import AsyncMock, Mock

import pytest

from sounds.exceptions import UnauthorisedError
from sounds.requests import RequestManager

pytestmark = pytest.mark.anyio


def _make_manager(has_session_cookie: bool, username="user", password="pass"):
    cookies = Mock()
    cookies.has_session_cookie = has_session_cookie
    auth = Mock()
    auth.renew_session = AsyncMock()
    auth.login = AsyncMock()
    manager = RequestManager(
        auth=auth,
        cookie_store=cookies,
        logger=Mock(),
        username=username,
        password=password,
    )
    return manager, auth, cookies


class TestRequestManager:
    """Tests for RequestManager.run()'s auth-retry logic."""

    async def test_run_succeeds_first_try(self):
        manager, auth, _ = _make_manager(has_session_cookie=True)
        call = AsyncMock(return_value="ok")

        result = await manager.run(call)

        assert result == "ok"
        call.assert_awaited_once()
        auth.renew_session.assert_not_called()
        auth.login.assert_not_called()

    async def test_run_renews_session_on_401_when_cookie_present(self):
        manager, auth, _ = _make_manager(has_session_cookie=True)
        call = AsyncMock(side_effect=[UnauthorisedError("expired"), "ok"])

        result = await manager.run(call)

        assert result == "ok"
        assert call.await_count == 2
        auth.renew_session.assert_awaited_once()
        auth.login.assert_not_called()

    async def test_run_falls_back_to_full_login_when_renewal_fails(self):
        manager, auth, _ = _make_manager(has_session_cookie=True)
        auth.renew_session = AsyncMock(side_effect=UnauthorisedError("still expired"))
        call = AsyncMock(side_effect=[UnauthorisedError("expired"), "ok"])

        result = await manager.run(call)

        assert result == "ok"
        auth.renew_session.assert_awaited_once()
        auth.login.assert_awaited_once_with(username="user", password="pass")
        assert call.await_count == 2

    async def test_run_skips_renewal_without_existing_cookie(self):
        """No session cookie to renew -> should go straight to full login,
        without ever calling renew_session()."""
        manager, auth, _ = _make_manager(has_session_cookie=False)
        call = AsyncMock(side_effect=[UnauthorisedError("expired"), "ok"])

        result = await manager.run(call)

        assert result == "ok"
        auth.renew_session.assert_not_called()
        auth.login.assert_awaited_once()

    async def test_run_raises_when_no_credentials_available(self):
        manager, auth, _ = _make_manager(
            has_session_cookie=False, username=None, password=None
        )
        call = AsyncMock(side_effect=UnauthorisedError("expired"))

        with pytest.raises(UnauthorisedError):
            await manager.run(call)

        auth.login.assert_not_called()

    async def test_run_raises_after_login(self):
        """If the call still 401s even after a full re-login, that should be raised."""
        manager, auth, _ = _make_manager(has_session_cookie=False)
        call = AsyncMock(
            side_effect=[
                UnauthorisedError("expired"),
                UnauthorisedError("still bad"),
            ]
        )

        with pytest.raises(UnauthorisedError):
            await manager.run(call)

        auth.login.assert_awaited_once()
