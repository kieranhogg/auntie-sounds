import aiohttp
import pytest
from yarl import URL

from sounds.client import SoundsClient, _default_cookie_file
from sounds.cookies import ID_COOKIE


class TestClientLogin:
    def test_login_with_no_credentials(self):
        pass


class TestClientCookieFileScoping:
    """Regression test: two accounts shouldn't write to the same default
    cookie file, and a client for one account must never end up
    authenticated as another by reading an old cookie file."""

    def test_default_cookie_file_differs_per_username(self):
        assert _default_cookie_file("alice") != _default_cookie_file("bob")

    def test_default_cookie_file_stable_for_same_username(self):
        assert _default_cookie_file("alice") == _default_cookie_file("alice")

    def test_anonymous_default_cookie_file_unchanged(self):
        from sounds.client import COOKIE_FILE

        assert _default_cookie_file(None) == COOKIE_FILE
        assert _default_cookie_file("") == COOKIE_FILE

    @pytest.mark.anyio
    async def test_second_account_does_not_inherit_first_accounts_session(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr("sounds.client._get_data_dir", lambda: tmp_path)
        monkeypatch.setattr("sounds.client.COOKIE_FILE", tmp_path / "sounds_jar")

        session_a = aiohttp.ClientSession()
        client_a = SoundsClient(
            username="account-a", password="pw-a", session=session_a
        )
        await client_a.start()
        client_a._session.cookie_jar.update_cookies(
            {ID_COOKIE: "a-session"}, response_url=URL("https://bbc.co.uk")
        )
        client_a.cookie_store.save()
        await session_a.close()

        session_b = aiohttp.ClientSession()
        client_b = SoundsClient(
            username="account-b", password="pw-b", session=session_b
        )
        await client_b.start()
        try:
            assert client_a.username == "account-a"
            assert client_a.cookie_store.account_id == "account-a"
            assert _default_cookie_file("account-a") != _default_cookie_file(
                "account-b"
            )
            assert client_a.cookie_store.path != client_b.cookie_store.path
            assert client_b.cookie_store.is_signed_in is False
        finally:
            await session_b.close()


class TestClientMenus:
    async def test_get_international_menu(self, mock_api, real_anonymous_client):
        menu = await real_anonymous_client.get_menu()
        assert len(menu.sub_items) == 4
        for id in ["radio", "catch_up", "schedule", "explore"]:
            assert menu.get(id) is not None
