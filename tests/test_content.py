import copy
import json
from pathlib import Path

import pytest

from sounds import parse
from sounds.content import assign_seasons
from sounds.endpoints import Endpoints
from sounds.exceptions import InvalidFormatError, NotFoundError
from sounds.models import Podcast, PodcastEpisode, Season

pytestmark = pytest.mark.anyio

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "api"


class TestContentService:
    """Tests for contents service."""


class TestSeasons:
    def test_flat_podcast(self):
        podcast = Podcast(id="podcast", seasons=None)
        episodes = [
            PodcastEpisode(id="orphan1"),
            PodcastEpisode(id="orphan2"),
            PodcastEpisode(id="orphan3"),
        ]
        podcast.sub_items = episodes
        assert len(podcast.sub_items) == 3
        assert podcast.seasons is None

        # Should leave untouched
        assign_seasons(podcast, episodes)
        assert len(podcast.sub_items) == 3
        assert podcast.seasons is None

    def test_podcast_with_seasons(self):
        podcast = Podcast(
            id="podcast", seasons=[Season(pid="urn1"), Season(pid="urn2")]
        )
        episodes = [
            PodcastEpisode(id="season1", series_pid="urn1"),
            PodcastEpisode(id="season2", series_pid="urn2"),
        ]
        assign_seasons(podcast, episodes)
        assert podcast.sub_items is None
        assert len(podcast.seasons[0].sub_items) == 1
        assert len(podcast.seasons[1].sub_items) == 1
        assert podcast.seasons[0].sub_items[0].id == "season1"
        assert podcast.seasons[1].sub_items[0].id == "season2"

    def test_orphan_episodes_with_no_seasons_dont_get_dropped(self):
        podcast = Podcast(id="podcast", seasons=[Season(pid="urn")])
        episodes = [
            PodcastEpisode(id="season1", series_pid="urn"),
            PodcastEpisode(id="orphan", series_pid=None),
        ]
        assign_seasons(podcast, episodes)
        assert len(podcast.sub_items) == 1
        assert len(podcast.seasons[0].sub_items) == 1
        assert podcast.sub_items[0].id == "orphan"
        assert podcast.seasons[0].sub_items[0].id == "season1"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _with_items(payload: dict, items: list[dict]) -> dict:
    return {**payload, "total": len(items), "data": items}


def _series_payload(brand: dict, series_pids: list[str]) -> dict:
    """Synthesised from the brand payload; no real type=series response yet."""
    item = brand["data"][0]
    items = []
    for sid in series_pids:
        series = copy.deepcopy(item)
        series["id"] = sid
        series["urn"] = f"urn:bbc:radio:series:{sid}"
        items.append(series)
    return _with_items(brand, items)


def _episode(base: dict, pid: str, series_pid: str, date: str) -> dict:
    episode = copy.deepcopy(base)
    episode["id"] = pid
    episode["urn"] = f"urn:bbc:radio:episode:{pid}"
    episode["container"] = {
        **episode["container"],
        "id": "p0jtptvc",
        "urn": "urn:bbc:radio:brand:p0jtptvc",
    }
    episode["uris"][0]["uri"] = f"/v2/programmes/playable?container={series_pid}"
    episode["release"] = {"date": date, "label": date}
    return episode


def _fake_api(responses: dict[Endpoints, dict]):
    calls: list = []

    async def fake(url, *args, **kwargs):
        calls.append((url, kwargs))
        return responses[url]

    return fake, calls


class TestGetPodcast:
    @pytest.fixture
    def brand(self):
        return _load("SERIES_CONTAINER.json")

    @pytest.fixture
    def playable(self):
        return _load("container_playable.json")

    async def test_requires_urn_or_pid(self, mock_content):
        with pytest.raises(InvalidFormatError):
            await mock_content.get_podcast()

    async def test_not_found(self, mock_content, monkeypatch, brand):
        fake, _ = _fake_api(
            {
                Endpoints.SERIES_CONTAINER: _with_items(brand, []),
                Endpoints.CONTAINER_FROM_PIDS: _with_items(brand, []),
            }
        )
        monkeypatch.setattr(mock_content.requests, "get_json_response", fake)
        with pytest.raises(NotFoundError):
            await mock_content.get_podcast(pid="p0nope")

    async def test_urn_is_reduced_to_pid(self, mock_content, monkeypatch, brand):
        fake, calls = _fake_api(
            {
                Endpoints.SERIES_CONTAINER: _with_items(brand, []),
                Endpoints.CONTAINER_FROM_PIDS: brand,
            }
        )
        monkeypatch.setattr(mock_content.requests, "get_json_response", fake)

        podcast = await mock_content.get_podcast(urn="urn:bbc:radio:brand:p0jtptvc")

        assert isinstance(podcast, Podcast)
        assert podcast.sub_items is None
        sent = dict(calls)
        assert sent[Endpoints.SERIES_CONTAINER]["params"]["parent"] == "p0jtptvc"
        assert sent[Endpoints.CONTAINER_FROM_PIDS]["url_args"] == {"pids": "p0jtptvc"}

    async def test_flat_brand_gets_all_episodes(
        self, mock_content, monkeypatch, brand, playable
    ):
        fake, calls = _fake_api(
            {
                Endpoints.SERIES_CONTAINER: _with_items(brand, []),
                Endpoints.CONTAINER_FROM_PIDS: brand,
                Endpoints.PLAYABLE_ITEMS_CONTAINER: playable,
            }
        )
        monkeypatch.setattr(mock_content.requests, "get_json_response", fake)

        podcast = await mock_content.get_podcast(pid="p0jtptvc", include_episodes=True)

        assert podcast.seasons is None
        assert len(podcast.sub_items) == len(playable["data"])
        assert dict(calls)[Endpoints.PLAYABLE_ITEMS_CONTAINER]["fetch_all_items"]

    async def test_single_episode_podcast(
        self, mock_content, monkeypatch, brand, playable
    ):
        """Regression: single-episode podcasts used to raise NotFoundError."""
        fake, _ = _fake_api(
            {
                Endpoints.SERIES_CONTAINER: _with_items(brand, []),
                Endpoints.CONTAINER_FROM_PIDS: brand,
                Endpoints.PLAYABLE_ITEMS_CONTAINER: _with_items(
                    playable, playable["data"][:1]
                ),
            }
        )
        monkeypatch.setattr(mock_content.requests, "get_json_response", fake)

        podcast = await mock_content.get_podcast(pid="p0jtptvc", include_episodes=True)

        assert len(podcast.sub_items) == 1

    async def test_multi_season_brand(self, mock_content, monkeypatch, brand, playable):
        base = playable["data"][0]
        episodes = [
            _episode(base, "e2", "p0s2", "2025-01-01T00:00:00Z"),
            _episode(base, "e1", "p0s1", "2024-01-01T00:00:00Z"),
            _episode(base, "loose", "p0jtptvc", "2023-01-01T00:00:00Z"),
        ]
        fake, _ = _fake_api(
            {
                # API order deliberately not release order
                Endpoints.SERIES_CONTAINER: _series_payload(brand, ["p0s2", "p0s1"]),
                Endpoints.CONTAINER_FROM_PIDS: brand,
                Endpoints.PLAYABLE_ITEMS_CONTAINER: _with_items(playable, episodes),
            }
        )
        monkeypatch.setattr(mock_content.requests, "get_json_response", fake)

        podcast = await mock_content.get_podcast(pid="p0jtptvc", include_episodes=True)

        assert [s.item_id for s in podcast.seasons] == ["p0s1", "p0s2"]
        assert [e.id for e in podcast.seasons[0].sub_items] == ["e1"]
        assert [e.id for e in podcast.seasons[1].sub_items] == ["e2"]
        # series_pid == brand pid is a "loose" episode, not a season
        assert podcast.sub_items[0].series_pid is None
        assert [e.id for e in podcast.sub_items] == ["loose"]


class TestEpisodeContainer:
    def test_container_is_brand_and_series_pid_from_ancestors(self):
        data = _load("PROGRAMME_FROM_PID.json")["data"][0]
        brand, series = (a["id"] for a in data["ancestors"])
        item = parse(data)
        assert item.container.id == brand
        assert item.series_pid == series

    def test_flat_brand_has_no_series_pid(self):
        item = parse(_load("container_playable.json")["data"][0])
        assert item.container.id == "p0h0q056"
        assert item.series_pid is None
