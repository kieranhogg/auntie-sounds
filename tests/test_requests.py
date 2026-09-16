from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest

from sounds.auth import AuthService
from sounds.client import SoundsClient
from sounds.exceptions import UnauthorisedError
from sounds.requests import RequestManager

pytestmark = pytest.mark.anyio


def _make_manager(has_session_cookie: bool, username="user", password="pass"):
    client = SoundsClient(mock_data=True)
    client.cookie_store = Mock()
    client.cookie_store.has_session_cookie = has_session_cookie
    client.auth = Mock()
    client.auth.renew_session = AsyncMock()
    client.auth.login = AsyncMock()
    manager = RequestManager(
        session=Mock(spec=aiohttp.ClientSession), login_details_provided=True
    )
    manager.set_reauth_handler(AsyncMock(spec=AuthService.retry_with_reauth))
    return manager, client.auth


class TestRequestManager:
    """Tests for RequestManager.run()'s delegation to reauth_handler."""

    async def test_run_delegates_to_reauth_handler_when_set(self):
        manager, _ = _make_manager(has_session_cookie=True)
        call = AsyncMock(return_value="ok")
        manager.reauth_handler = AsyncMock(return_value="ok")

        result = await manager.run(call)

        assert result == "ok"
        manager.reauth_handler.assert_awaited_once_with(call)

        result = await manager.run(call)

    async def test_run_calls_call_directly_when_no_reauth_handler(self):
        manager, _ = _make_manager(has_session_cookie=True)
        manager.reauth_handler = None
        call = AsyncMock(return_value="ok")

        result = await manager.run(call)
        assert result == "ok"
        call.assert_awaited_once()

    async def test_run_propagates_errors_from_reauth_handler(self):
        manager, _ = _make_manager(has_session_cookie=True)
        call = AsyncMock()
        manager.reauth_handler = AsyncMock(side_effect=UnauthorisedError("still bad"))
        with pytest.raises(UnauthorisedError):
            await manager.run(call)

    async def test_run_propagates_errors_without_reauth_handler(self):
        manager, _ = _make_manager(has_session_cookie=True)
        manager.reauth_handler = None
        call = AsyncMock(side_effect=UnauthorisedError("expired"))

        with pytest.raises(UnauthorisedError):
            await manager.run(call)
