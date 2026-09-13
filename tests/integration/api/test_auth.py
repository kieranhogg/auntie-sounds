import os

import pytest
from dotenv import load_dotenv

from sounds.client import SoundsClient
from sounds.exceptions import LoginFailedError

load_dotenv()


@pytest.mark.api
class TestAuth:
    async def test_correct_login(self):
        username = os.getenv("SOUNDS_USERNAME")
        password = os.getenv("SOUNDS_PASSWORD")
        client = SoundsClient(username=username, password=password)
        client.clear_cookies()
        assert not client.cookie_store.has_session_cookie
        await client.login()
        assert client.cookie_store.has_session_cookie

    async def test_incorrect_login(self):
        client = SoundsClient(username="example@example.com", password="snfmseio374n")
        client.clear_cookies()
        with pytest.raises(LoginFailedError, match=client.auth.PASSWORD_ERROR_MSG):
            await client.login()

    async def test_incorrect_login_bad_password_format(self):
        client = SoundsClient(username="example@example.com", password="password")
        client.clear_cookies()
        with pytest.raises(
            LoginFailedError, match=client.auth.PASSWORD_NUMBER_SYMBOL_ERROR_MSG
        ):
            await client.login()

    async def test_incorrect_login_bad_password(self):
        client = SoundsClient(username="example@example.com", password="password1")
        client.clear_cookies()
        with pytest.raises(
            LoginFailedError, match=client.auth.PASSWORD_TOO_EASY_ERROR_MSG
        ):
            await client.login()
