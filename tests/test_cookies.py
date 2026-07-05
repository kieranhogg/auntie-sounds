from unittest.mock import Mock

import aiohttp
import pytest
from yarl import URL

from sounds.constants import COOKIE_ID, URLs
from sounds.cookies import CookieStore

pytestmark = pytest.mark.anyio


def _jar_with_session_cookie() -> aiohttp.CookieJar:
    jar = aiohttp.CookieJar()
    jar.update_cookies({COOKIE_ID: "abc123"}, response_url=URL(URLs.COOKIE_BASE.value))
    return jar


class TestCookieStore:
    """Tests for CookieStore."""

    async def test_has_session_cookie_true_when_present(self, tmp_path, mock_logger):
        store = CookieStore(
            session=Mock(cookie_jar=_jar_with_session_cookie()),
            logger=mock_logger,
            cookie_file_location=tmp_path / "cookies",
        )
        assert store.has_session_cookie is True

    async def test_has_session_cookie_false_when_empty(self, tmp_path, mock_logger):
        store = CookieStore(
            session=Mock(cookie_jar=aiohttp.CookieJar()),
            logger=mock_logger,
            cookie_file_location=tmp_path / "cookies",
        )
        assert store.has_session_cookie is False

    async def test_clear_removes_session_cookie(self, tmp_path, mock_logger):
        store = CookieStore(
            session=Mock(cookie_jar=_jar_with_session_cookie()),
            logger=mock_logger,
            cookie_file_location=tmp_path / "cookies",
        )
        assert store.has_session_cookie is True

        store.clear()

        assert store.has_session_cookie is False

    async def test_load_warns_but_does_not_raise_when_file_missing(
        self, tmp_path, mock_logger
    ):
        store = CookieStore(
            session=Mock(cookie_jar=aiohttp.CookieJar()),
            logger=mock_logger,
            cookie_file_location=tmp_path / "does_not_exist",
        )
        store.load()  # must not raise
        mock_logger.warning.assert_called_once()

    async def test_save_then_load_round_trip(self, tmp_path, mock_logger):
        """save() should persist cookies that a fresh load() into an empty jar can restore."""
        cookie_path = tmp_path / "cookies.pickle"
        store_a = CookieStore(
            session=Mock(cookie_jar=_jar_with_session_cookie()),
            logger=mock_logger,
            cookie_file_location=cookie_path,
        )
        store_a.save()
        assert cookie_path.exists()

        store_b = CookieStore(
            session=Mock(cookie_jar=aiohttp.CookieJar()),
            logger=mock_logger,
            cookie_file_location=cookie_path,
        )
        store_b.load()

        assert store_b.has_session_cookie is True

    async def test_load_skips_when_jar_already_populated(self, tmp_path, mock_logger):
        """If the in-memory jar already has cookies, load() should not overwrite them from disk."""
        cookie_path = tmp_path / "cookies.pickle"
        # Persist an empty jar to disk.
        CookieStore(
            session=Mock(cookie_jar=aiohttp.CookieJar()),
            logger=mock_logger,
            cookie_file_location=cookie_path,
        ).save()

        store = CookieStore(
            session=Mock(cookie_jar=_jar_with_session_cookie()),
            logger=mock_logger,
            cookie_file_location=cookie_path,
        )
        store.load()

        # Should still have the in-memory cookie, not the empty on-disk one.
        assert store.has_session_cookie is True
