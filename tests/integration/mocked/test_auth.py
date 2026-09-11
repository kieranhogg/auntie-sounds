import pytest

from sounds.auth import _get_form_action


@pytest.fixture
def username_form():
    with open("tests/fixtures/auth/login_form.html") as f:
        return f.read()

@pytest.fixture
def password_form():
    with open("tests/fixtures/auth/password_form.html") as f:
        return f.read()

class TestAuthHelpers:
    def test_getting_form_action_from_username_form(self, username_form):
        action = _get_form_action(username_form)
        assert action.startswith("/auth?")
        assert "action=sign-in" in action

    def test_getting_form_action_from_password_form(self, password_form):
        action = _get_form_action(password_form)
        assert action.startswith("/auth/password?")
        assert "action=sign-in" in action

