from unittest.mock import AsyncMock, Mock

import pytest

from sounds.auth import _get_form_action
from sounds.exceptions import MultipleObjectsFound, NotFoundError, UnauthorisedError


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


class TestAuthBehaviour:
    async def test_retry_with_reauth_returns_call_result_without_reauth(
        self, mock_auth_service
    ):
        mock_auth_service.username = "user"
        mock_auth_service.password = "pass"
        call = AsyncMock(return_value="ok")

        result = await mock_auth_service.retry_with_reauth(call)

        assert result == "ok"
        call.assert_awaited_once()

    async def test_retry_with_reauth_raises_without_credentials(
        self, mock_auth_service
    ):
        mock_auth_service.username = None
        mock_auth_service.password = None
        call = AsyncMock(side_effect=UnauthorisedError("expired"))

        with pytest.raises(UnauthorisedError):
            await mock_auth_service.retry_with_reauth(call)

    async def test_retry_with_reauth_renews_session_when_cookie_present(
        self, mock_auth_service, monkeypatch
    ):
        mock_auth_service.username = "user"
        mock_auth_service.password = "pass"
        mock_auth_service.cookie_store = Mock(has_session_cookie=True)
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
        mock_auth_service.cookie_store = Mock(has_session_cookie=True)
        monkeypatch.setattr(
            mock_auth_service, "renew_session", AsyncMock(return_value=False)
        )
        login = AsyncMock()
        monkeypatch.setattr(mock_auth_service, "login", login)
        call = AsyncMock(
            side_effect=[
                UnauthorisedError("expired"),
                UnauthorisedError("still expired"),
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
        mock_auth_service.cookie_store = Mock(has_session_cookie=False)
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
        mock_auth_service.cookie_store = Mock(has_session_cookie=False)
        monkeypatch.setattr(mock_auth_service, "login", AsyncMock())
        call = AsyncMock(
            side_effect=[UnauthorisedError("expired"), UnauthorisedError("still bad")]
        )

        with pytest.raises(UnauthorisedError):
            await mock_auth_service.retry_with_reauth(call)
