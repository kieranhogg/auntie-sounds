import logging
from unittest.mock import Mock

import aiohttp
import pytest
from yarl import URL

from auntie_sounds.cookies import ID_COOKIE, CookieStore
from auntie_sounds.endpoints import URLs

pytestmark = pytest.mark.anyio


def _jar_with_session_cookie() -> aiohttp.CookieJar:
    jar = aiohttp.CookieJar()
    jar.update_cookies({ID_COOKIE: "abc123"}, response_url=URL(URLs.COOKIE_BASE.value))
    return jar


class TestCookieStore:
    """Tests for CookieStore."""

    async def test_is_signed_in_true_when_present(self, tmp_path):
        store = CookieStore(
            session=Mock(cookie_jar=_jar_with_session_cookie()),
            cookie_file_location=tmp_path / "cookies",
        )
        assert store.is_signed_in is True

    async def test_is_signed_in_false_when_empty(self, tmp_path):
        store = CookieStore(
            session=Mock(cookie_jar=aiohttp.CookieJar()),
            cookie_file_location=tmp_path / "cookies",
        )
        assert store.is_signed_in is False

    async def test_clear_removes_session_cookie(self, tmp_path):
        store = CookieStore(
            session=Mock(cookie_jar=_jar_with_session_cookie()),
            cookie_file_location=tmp_path / "cookies",
        )
        assert store.is_signed_in is True

        store.clear()

        assert store.is_signed_in is False

    async def test_load_warns_but_does_not_raise_when_file_missing(
        self, tmp_path, caplog
    ):
        caplog.set_level(logging.WARNING, logger="auntie_sounds.cookies")
        store = CookieStore(
            session=Mock(cookie_jar=aiohttp.CookieJar()),
            cookie_file_location=tmp_path / "does_not_exist",
        )
        store.load()  # must not raise
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert [r.getMessage() for r in warnings] == ["Cookie location does not exist."]

    async def test_save_then_load_round_trip(self, tmp_path):
        """save() should persist cookies that a fresh load() into an empty jar can restore."""
        cookie_path = tmp_path / "cookies.pickle"
        store_a = CookieStore(
            session=Mock(cookie_jar=_jar_with_session_cookie()),
            cookie_file_location=cookie_path,
        )
        store_a.save()
        assert cookie_path.exists()

        store_b = CookieStore(
            session=Mock(cookie_jar=aiohttp.CookieJar()),
            cookie_file_location=cookie_path,
        )
        store_b.load()

        assert store_b.is_signed_in is True

    async def test_load_skips_when_jar_already_populated(self, tmp_path):
        """If the in-memory jar already has cookies, load() should not overwrite them from disk."""
        cookie_path = tmp_path / "cookies.pickle"
        # Persist an empty jar to disk.
        CookieStore(
            session=Mock(cookie_jar=aiohttp.CookieJar()),
            cookie_file_location=cookie_path,
        ).save()

        store = CookieStore(
            session=Mock(cookie_jar=_jar_with_session_cookie()),
            cookie_file_location=cookie_path,
        )
        store.load()

        # Should still have the in-memory cookie, not the empty on-disk one.
        assert store.is_signed_in is True

    async def test_load_refuses_foreign_account_session(self, tmp_path):
        """A cookie file saved for one account_id must not be loaded by a
        CookieStore configured for a different account_id, even if they
        share the same cookie_file_location."""
        cookie_path = tmp_path / "sounds_jar"
        CookieStore(
            session=Mock(cookie_jar=_jar_with_session_cookie()),
            cookie_file_location=cookie_path,
            account_id="account-a",
        ).save()

        store_b = CookieStore(
            session=Mock(cookie_jar=aiohttp.CookieJar()),
            cookie_file_location=cookie_path,
            account_id="account-b",
        )
        store_b.load()

        assert store_b.is_signed_in is False

    async def test_load_accepts_matching_account_session(self, tmp_path):
        """The same account_id loading its own saved cookies should still work."""
        cookie_path = tmp_path / "sounds_jar"
        CookieStore(
            session=Mock(cookie_jar=_jar_with_session_cookie()),
            cookie_file_location=cookie_path,
            account_id="account-a",
        ).save()

        store_again = CookieStore(
            session=Mock(cookie_jar=aiohttp.CookieJar()),
            cookie_file_location=cookie_path,
            account_id="account-a",
        )
        store_again.load()

        assert store_again.is_signed_in is True

    async def test_load_populates_owner_for_legacy_file_without_marker(self, tmp_path):
        """A cookie file saved before per-account existed is still
        trusted once, matching prior behaviour, but a marker is
        written to protect future loads."""
        cookie_path = tmp_path / "sounds_jar"
        # Simulate a legacy save: persist cookies with no CookieStore
        # involved in the write, so no .owner marker is created.
        legacy_jar = _jar_with_session_cookie()
        legacy_jar.save(str(cookie_path))
        assert not (tmp_path / "sounds_jar.owner").exists()

        store = CookieStore(
            session=Mock(cookie_jar=aiohttp.CookieJar()),
            cookie_file_location=cookie_path,
            account_id="account-a",
        )
        store.load()

        assert store.is_signed_in is True
        assert (tmp_path / "sounds_jar.owner").read_text() == "account-a"

        # A different account must now be refused against this same path.
        store_b = CookieStore(
            session=Mock(cookie_jar=aiohttp.CookieJar()),
            cookie_file_location=cookie_path,
            account_id="account-b",
        )
        store_b.load()
        assert store_b.is_signed_in is False
