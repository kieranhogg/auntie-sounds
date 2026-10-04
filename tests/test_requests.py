from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest

from sounds.auth import AuthService
from sounds.client import SoundsClient
from sounds.endpoints import Endpoints
from sounds.exceptions import NetworkError, NotFoundError, UnauthorisedError
from sounds.requests import RequestManager

pytestmark = pytest.mark.anyio


def _make_manager(is_signed_in: bool, username="user", password="pass"):
    client = SoundsClient()
    client.cookie_store = Mock()
    client.cookie_store.is_signed_in = is_signed_in
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
        manager, _ = _make_manager(is_signed_in=True)
        call = AsyncMock(return_value="ok")
        manager.reauth_handler = AsyncMock(return_value="ok")

        result = await manager.run(call)

        assert result == "ok"
        manager.reauth_handler.assert_awaited_once_with(call)

        result = await manager.run(call)

    async def test_run_calls_call_directly_when_no_reauth_handler(self):
        manager, _ = _make_manager(is_signed_in=True)
        manager.reauth_handler = None
        call = AsyncMock(return_value="ok")

        result = await manager.run(call)
        assert result == "ok"
        call.assert_awaited_once()

    async def test_run_propagates_errors_from_reauth_handler(self):
        manager, _ = _make_manager(is_signed_in=True)
        call = AsyncMock()
        manager.reauth_handler = AsyncMock(side_effect=UnauthorisedError("still bad"))
        with pytest.raises(UnauthorisedError):
            await manager.run(call)

    async def test_run_propagates_errors_without_reauth_handler(self):
        manager, _ = _make_manager(is_signed_in=True)
        manager.reauth_handler = None
        call = AsyncMock(side_effect=UnauthorisedError("expired"))

        with pytest.raises(UnauthorisedError):
            await manager.run(call)


class TestMakeRequestErrors:
    async def test_total_timeout_is_wrapped_as_network_error(self):
        session = Mock(spec=aiohttp.ClientSession)
        session.request = AsyncMock(side_effect=TimeoutError)
        manager = RequestManager(session=session)

        with pytest.raises(NetworkError):
            await manager.make_request("GET", "https://example.com/")

    async def test_401_response_is_released(self):
        resp = Mock(status=401, reason="Unauthorized")
        session = Mock(spec=aiohttp.ClientSession)
        session.request = AsyncMock(return_value=resp)
        manager = RequestManager(session=session)

        with pytest.raises(UnauthorisedError):
            await manager.make_request("GET", "https://example.com/")
        resp.release.assert_called_once()

    async def test_404_response_is_raised_correctly(self):
        resp = AsyncMock(status=404, reason="Not Found")
        session = Mock(spec=aiohttp.ClientSession)
        session.request = AsyncMock(return_value=resp)
        manager = RequestManager(session=session)

        with pytest.raises(NotFoundError):
            await manager.make_request("GET", "https://example.com/")


def _json_response(body: dict):
    resp = Mock(status=200, reason="OK")
    resp.json = AsyncMock(return_value=body)
    return resp


class TestGetJsonResponseParams:
    """limit/offset should only be sent when the caller asks for paging."""

    async def test_no_limit_sent_when_not_paging(self):
        session = Mock(spec=aiohttp.ClientSession)
        session.request = AsyncMock(return_value=_json_response({"data": []}))
        manager = RequestManager(session=session)

        await manager.get_json_response(url=Endpoints.NETWORKS)

        assert "params" not in session.request.await_args.kwargs

    async def test_caller_limit_is_not_overridden(self):
        session = Mock(spec=aiohttp.ClientSession)
        session.request = AsyncMock(return_value=_json_response({"data": []}))
        manager = RequestManager(session=session)

        await manager.get_json_response(url=Endpoints.NETWORKS, params={"limit": 5})

        assert session.request.await_args.kwargs["params"] == {"limit": 5}

    async def test_fetch_all_items_pages_until_total(self):
        pages = [
            {"total": 3, "offset": 0, "limit": 2, "data": [1, 2]},
            {"total": 3, "offset": 2, "limit": 2, "data": [3]},
        ]
        session = Mock(spec=aiohttp.ClientSession)
        session.request = AsyncMock(side_effect=[_json_response(p) for p in pages])
        manager = RequestManager(session=session)

        result = await manager.get_json_response(
            url=Endpoints.NETWORKS, fetch_all_items=True, page_size=2
        )

        assert result["data"] == [1, 2, 3]
        sent = [c.kwargs["params"] for c in session.request.await_args_list]
        assert sent == [{"limit": 2}, {"offset": 2, "limit": 2}]

    async def test_max_items_caps_results(self):
        session = Mock(spec=aiohttp.ClientSession)
        session.request = AsyncMock(
            return_value=_json_response(
                {"total": 10, "offset": 0, "limit": 2, "data": [1, 2]}
            )
        )
        manager = RequestManager(session=session)

        result = await manager.get_json_response(url=Endpoints.NETWORKS, max_items=2)

        assert result["data"] == [1, 2]
        session.request.assert_awaited_once()
        assert session.request.await_args.kwargs["params"] == {"limit": 2}
