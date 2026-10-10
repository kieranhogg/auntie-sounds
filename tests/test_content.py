import copy
import json
from unittest.mock import AsyncMock

import pytest

from auntie_sounds import parse
from auntie_sounds.content import MAX_PODCAST_EPISODES, assign_seasons
from auntie_sounds.endpoints import Endpoints
from auntie_sounds.exceptions import InvalidFormatError, NotFoundError
from auntie_sounds.models import (
    Podcast,
    PodcastEpisode,
    RadioSeries,
    RadioShow,
    Season,
)
from tests.conftest import FIXTURES_FOLDER

pytestmark = pytest.mark.anyio


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

    def test_seasons_beyond_a_partial_fetch_are_kept(self):
        """With only some episodes, an empty season may just not be fetched yet."""
        podcast = Podcast(
            id="podcast", seasons=[Season(pid="urn1"), Season(pid="older")]
        )
        episodes = [PodcastEpisode(id="season1", series_pid="urn1")]
        assign_seasons(podcast, episodes, complete=False)
        assert [s.pid for s in podcast.seasons] == ["urn1", "older"]

    def test_seasons_with_no_episodes_are_dropped(self):
        """The API lists unavailable seasons too, e.g. omnibus editions."""
        podcast = Podcast(
            id="podcast", seasons=[Season(pid="urn1"), Season(pid="omnibus")]
        )
        episodes = [PodcastEpisode(id="season1", series_pid="urn1")]
        assign_seasons(podcast, episodes)
        assert [s.pid for s in podcast.seasons] == ["urn1"]

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
    return json.loads((FIXTURES_FOLDER / name).read_text())


def _with_items(payload: dict, items: list[dict]) -> dict:
    return {**payload, "total": len(items), "data": items}


def _series_payload(brand: dict, series_pids: list[str]) -> dict:
    """Synthesised from the brand payload, so the season pids can be chosen."""
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
    # OwnerService fetches the station list whenever it sees a brand or series
    responses = {Endpoints.NETWORKS: _load("NETWORKS.json"), **responses}
    calls: list = []

    async def fake(url, *args, **kwargs):
        calls.append((url, kwargs))
        return responses[url]

    return fake, calls


class TestGetPodcast:
    @pytest.fixture(autouse=True)
    def anonymous(self, mock_content, monkeypatch):
        monkeypatch.setattr(
            mock_content, "_personalised", AsyncMock(return_value=False)
        )

    @pytest.fixture
    def brand(self):
        return _load("CONTAINER_FROM_PIDS.json")

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
        sent = dict(calls)[Endpoints.PLAYABLE_ITEMS_CONTAINER]
        assert sent["max_items"] == MAX_PODCAST_EPISODES
        assert not sent["fetch_all_items"]

    async def test_all_episodes_on_request(
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

        await mock_content.get_podcast(
            pid="p0jtptvc", include_episodes=True, max_episodes=None
        )

        sent = dict(calls)[Endpoints.PLAYABLE_ITEMS_CONTAINER]
        assert sent["fetch_all_items"]
        assert sent["max_items"] is None

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

    async def test_real_brand_with_seasons(self, mock_content, monkeypatch, brand):
        """I'm Not A Monster: three seasons, every episode in one of them."""
        fake, _ = _fake_api(
            {
                Endpoints.CONTAINER_FROM_PIDS: brand,
                Endpoints.SERIES_CONTAINER: _load("SERIES_CONTAINER.json"),
                Endpoints.PLAYABLE_ITEMS_CONTAINER: _load(
                    "PLAYABLE_ITEMS_CONTAINER.json"
                ),
            }
        )
        monkeypatch.setattr(mock_content.requests, "get_json_response", fake)

        podcast = await mock_content.get_podcast(pid="p08yblkf", include_episodes=True)

        assert podcast.image_url
        # Oldest first, not the API's pid order
        assert [(s.titles.secondary, len(s.sub_items)) for s in podcast.seasons] == [
            ("I'm Not A Monster", 14),
            ("The Shamima Begum Story", 14),
            ("Where Is Austin Tice?", 9),
        ]
        assert all(s.image_url for s in podcast.seasons)
        assert podcast.sub_items is None
        # 9 of these went out on Radio 4, but the brand is a podcast
        episodes = [e for s in podcast.seasons for e in s.sub_items]
        assert {type(e) for e in episodes} == {PodcastEpisode}


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


def _owned_by(network_id: str) -> dict:
    """A CONTAINER_FROM_PIDS response whose brand belongs to the given network."""
    brand = _load("CONTAINER_FROM_PIDS.json")
    item = {
        **brand["data"][0],
        "network": {**brand["data"][0]["network"], "id": network_id},
    }
    return {**brand, "data": [item]}


class TestGetPodcastEpisodes:
    @pytest.mark.parametrize(
        ("personalised", "endpoint"),
        [
            (False, Endpoints.PLAYABLE_ITEMS_CONTAINER),
            (True, Endpoints.MY_PLAYABLE_ITEMS_CONTAINER),
        ],
    )
    async def test_endpoint(self, mock_content, monkeypatch, personalised, endpoint):
        monkeypatch.setattr(
            mock_content, "_personalised", AsyncMock(return_value=personalised)
        )
        fake, calls = _fake_api(
            {
                endpoint: _load(f"{endpoint.name}.json"),
                Endpoints.CONTAINER_FROM_PIDS: _load("CONTAINER_FROM_PIDS.json"),
            }
        )
        monkeypatch.setattr(mock_content.requests, "get_json_response", fake)

        episodes = await mock_content.get_podcast_episodes("p08yblkf")

        assert endpoint in [url for url, _ in calls]
        assert episodes

    @pytest.mark.parametrize(
        ("owner", "episode_type", "container_type"),
        [
            ("bbc_sounds_podcasts", PodcastEpisode, Podcast),
            ("bbc_radio_four", RadioShow, RadioSeries),
        ],
    )
    async def test_types_follow_the_owner(
        self, mock_content, monkeypatch, owner, episode_type, container_type
    ):
        """I'm Not A Monster has episodes on two networks, but one owner."""
        monkeypatch.setattr(
            mock_content, "_personalised", AsyncMock(return_value=False)
        )
        listing = _load("PLAYABLE_ITEMS_CONTAINER.json")
        networks = {item["network"]["id"] for item in listing["data"]}
        assert networks == {"bbc_sounds_podcasts", "bbc_radio_four"}
        fake, _ = _fake_api(
            {
                Endpoints.PLAYABLE_ITEMS_CONTAINER: listing,
                Endpoints.CONTAINER_FROM_PIDS: _owned_by(owner),
            }
        )
        monkeypatch.setattr(mock_content.requests, "get_json_response", fake)

        episodes = await mock_content.get_podcast_episodes("p08yblkf")

        assert {type(e) for e in episodes} == {episode_type}
        assert {type(e.container) for e in episodes} == {container_type}

    async def test_owner_is_looked_up_once(self, mock_content, monkeypatch):
        monkeypatch.setattr(
            mock_content, "_personalised", AsyncMock(return_value=False)
        )
        fake, calls = _fake_api(
            {
                Endpoints.PLAYABLE_ITEMS_CONTAINER: _load(
                    "PLAYABLE_ITEMS_CONTAINER.json"
                ),
                Endpoints.CONTAINER_FROM_PIDS: _load("CONTAINER_FROM_PIDS.json"),
            }
        )
        monkeypatch.setattr(mock_content.requests, "get_json_response", fake)

        await mock_content.get_podcast_episodes("p08yblkf")
        await mock_content.get_podcast_episodes("p08yblkf")

        assert [url for url, _ in calls].count(Endpoints.CONTAINER_FROM_PIDS) == 1

    async def test_personalised_episodes_have_progress(self, mock_content, monkeypatch):
        monkeypatch.setattr(mock_content, "_personalised", AsyncMock(return_value=True))
        fake, _ = _fake_api(
            {
                Endpoints.MY_PLAYABLE_ITEMS_CONTAINER: _load(
                    "MY_PLAYABLE_ITEMS_CONTAINER.json"
                ),
                Endpoints.CONTAINER_FROM_PIDS: _load("CONTAINER_FROM_PIDS.json"),
            }
        )
        monkeypatch.setattr(mock_content.requests, "get_json_response", fake)

        episodes = await mock_content.get_podcast_episodes("m001zlz0")

        assert [e.progress.value for e in episodes if e.progress] == [41]


class TestGetByPid:
    @pytest.mark.parametrize(
        ("personalised", "endpoint"),
        [
            (False, Endpoints.PROGRAMME_FROM_PID_PLAYABLE),
            (True, Endpoints.PID_PLAYABLE),
        ],
    )
    async def test_endpoint(self, mock_content, monkeypatch, personalised, endpoint):
        monkeypatch.setattr(
            mock_content, "_personalised", AsyncMock(return_value=personalised)
        )
        fake, calls = _fake_api(
            {
                endpoint: _load(f"{endpoint.name}.json"),
                Endpoints.CONTAINER_FROM_PIDS: _load("CONTAINER_FROM_PIDS.json"),
            }
        )
        monkeypatch.setattr(mock_content.requests, "get_json_response", fake)

        await mock_content.get_by_pid("m003169g")

        assert endpoint in [url for url, _ in calls]

    async def test_podcast_episode_on_a_radio_network(self, mock_content, monkeypatch):
        """m003169g went out on Radio 4, but its brand is a podcast.

        Regression: the container was a bare Container, which MA can't convert.
        """
        monkeypatch.setattr(
            mock_content, "_personalised", AsyncMock(return_value=False)
        )
        fake, calls = _fake_api(
            {
                Endpoints.PROGRAMME_FROM_PID_PLAYABLE: _load(
                    "PROGRAMME_FROM_PID_PLAYABLE.json"
                ),
                Endpoints.CONTAINER_FROM_PIDS: _load("CONTAINER_FROM_PIDS.json"),
            }
        )
        monkeypatch.setattr(mock_content.requests, "get_json_response", fake)

        item = await mock_content.get_by_pid("m003169g")

        assert item.network.id == "bbc_radio_four"
        assert isinstance(item, PodcastEpisode)
        assert isinstance(item.container, Podcast)
        assert item.container.item_id == "p08yblkf"
        assert dict(calls)[Endpoints.CONTAINER_FROM_PIDS]["url_args"] == {
            "pids": "p08yblkf"
        }
        assert item.series_pid == "m0031689"
        assert item.version_pid == "p0p78bd4"
        assert item.image_url

    async def test_personalised_has_progress(self, mock_content, monkeypatch):
        monkeypatch.setattr(mock_content, "_personalised", AsyncMock(return_value=True))
        fake, _ = _fake_api(
            {
                Endpoints.PID_PLAYABLE: _load("PID_PLAYABLE.json"),
                Endpoints.CONTAINER_FROM_PIDS: _owned_by("bbc_radio_four"),
            }
        )
        monkeypatch.setattr(mock_content.requests, "get_json_response", fake)

        item = await mock_content.get_by_pid("m002wx92")

        assert item.progress.value == 41
