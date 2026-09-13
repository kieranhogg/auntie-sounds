from unittest.mock import AsyncMock, Mock

import pytest

from sounds.client import SoundsClient
from sounds.exceptions import UnauthorisedError
from sounds.requests import RequestManager

pytestmark = pytest.mark.anyio


def _make_manager(has_session_cookie: bool, username="user", password="pass"):
    client = SoundsClient(mock_session=True)
    client.cookie_store = Mock()
    client.cookie_store.has_session_cookie = has_session_cookie
    client.auth = Mock()
    client.auth.renew_session = AsyncMock()
    client.auth.login = AsyncMock()
    manager = RequestManager(
        client,
        username=username,
        password=password,
    )
    return manager


class TestRequestManager:
    """Tests for RequestManager.run()'s auth-retry logic."""

    async def test_run_succeeds_first_try(self):
        manager = _make_manager(has_session_cookie=True)
        call = AsyncMock(return_value="ok")

        result = await manager.run(call)

        assert result == "ok"
        call.assert_awaited_once()
        manager._client.auth.renew_session.assert_not_called()
        manager._client.auth.login.assert_not_called()

    async def test_run_renews_session_on_401_when_cookie_present(self):
        manager = _make_manager(has_session_cookie=True)
        call = AsyncMock(side_effect=[UnauthorisedError("expired"), "ok"])

        result = await manager.run(call)

        assert result == "ok"
        assert call.await_count == 2
        manager._client.auth.renew_session.assert_awaited_once()
        manager._client.auth.login.assert_not_called()

    async def test_run_falls_back_to_full_login_when_renewal_fails(self):
        manager = _make_manager(has_session_cookie=True)
        manager._client.auth.renew_session = AsyncMock(
            side_effect=UnauthorisedError("still expired")
        )
        call = AsyncMock(side_effect=[UnauthorisedError("expired"), "ok"])

        result = await manager.run(call)

        assert result == "ok"
        manager._client.auth.renew_session.assert_awaited_once()
        manager._client.auth.login.assert_awaited_once_with(
            username="user", password="pass"
        )
        assert call.await_count == 2

    async def test_run_skips_renewal_without_existing_cookie(self):
        """No session cookie to renew -> should go straight to full login,
        without ever calling renew_session()."""
        manager = _make_manager(has_session_cookie=False)
        call = AsyncMock(side_effect=[UnauthorisedError("expired"), "ok"])

        result = await manager.run(call)

        assert result == "ok"
        manager._client.auth.renew_session.assert_not_called()
        manager._client.auth.login.assert_awaited_once()

    async def test_run_raises_when_no_credentials_available(self):
        manager = _make_manager(has_session_cookie=False, username=None, password=None)
        call = AsyncMock(side_effect=UnauthorisedError("expired"))

        with pytest.raises(UnauthorisedError):
            await manager.run(call)

        manager._client.auth.login.assert_not_called()

    async def test_run_raises_after_login(self):
        """If the call still 401s even after a full re-login, that should be raised."""
        manager = _make_manager(has_session_cookie=False)
        call = AsyncMock(
            side_effect=[
                UnauthorisedError("expired"),
                UnauthorisedError("still bad"),
            ]
        )

        with pytest.raises(UnauthorisedError):
            await manager.run(call)

        manager._client.auth.login.assert_awaited_once()
