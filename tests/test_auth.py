from unittest.mock import AsyncMock

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
    async def test_retry_with_reauth_falls_back_to_full_login_when_renewal_fails(
        self, mock_auth_service, mock_requests
    ):
        pass
