"""Tests for broadcast ids, segment offsets, polling and the on-air programme."""

import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from auntie_sounds.history import Speech, Track, Unknown
from auntie_sounds.models import (
    Polling,
    RadioShow,
    ScheduleItem,
    Segment,
    SegmentOffset,
)
from auntie_sounds.parser import Parser
from auntie_sounds.schedule import SEGMENT_LIMIT_MAX, ScheduleService, unique_broadcasts

pytestmark = pytest.mark.anyio

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "api"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


class FakeRequests:
    """Answers by URL, remembering what was asked for."""

    def __init__(self, responses: dict[str, dict]):
        self.responses = responses
        self.urls: list[str] = []

    async def get_json_response(self, url, url_args=None, **kwargs):
        key = url if isinstance(url, str) else url.name
        self.urls.append(key)
        return copy.deepcopy(self.responses[key])


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


RECENT_TRACKS_URI = "/v2/services/bbc_radio_fourfm/segments/latest?experience=domestic&offset={offset}&limit={limit}"
RECENT_URL = "https://rms.api.bbc.co.uk" + RECENT_TRACKS_URI.format(offset=0, limit=10)
POLL_URL = (
    "https://rms.api.bbc.co.uk/v2/broadcasts/sub-services/poll/bbc_radio_fourfm"
    "?experience=domestic&offset=0&limit=5"
)
# Moral Maze, 19:00 to 20:00 in the Radio 4 capture
ON_AIR = datetime(2026, 9, 16, 19, 30, tzinfo=UTC)


def experience_with_tracks() -> dict:
    experience = load("LIVE_STATION_DETAILS.json")
    recent = next(m for m in experience["data"] if m["id"] == "recent_tracks")
    recent["uris"] = {"polling": {"uri": RECENT_TRACKS_URI, "wait_before_poll_sec": 30}}
    return experience


def service(clock=None, **extra):
    responses = {"PLAY_EXPERIENCE": experience_with_tracks(), **extra}
    requests = FakeRequests(responses)
    return ScheduleService(requests=requests, clock=clock or Clock()), requests  # type: ignore[arg-type]


class TestBroadcastIds:
    """id for a summary, pid for a single broadcast."""

    def test_single_broadcast_uses_pid(self):
        item = Parser().parse_node(load("BROADCAST.json"))
        assert isinstance(item, ScheduleItem)
        assert item.broadcast_pid == "p0p8ybm1"
        assert item.pid == "m0032244"
        assert item.item_id == "m0032244"
        assert item.vpid is None

    def test_summary_uses_id(self):
        summary = load("LIVE_STATION_DETAILS.json")["data"][0]["data"][0]
        item = Parser().parse_node(summary)
        assert isinstance(item, ScheduleItem)
        assert item.broadcast_pid == "p0p6nq1b"
        assert item.pid == "m0031kr0"

    def test_single_broadcast_and_summary_have_the_same_shape(self):
        single = Parser().parse_node(load("BROADCAST.json"))
        assert isinstance(single, ScheduleItem)
        assert single.titles.primary == "Nick Grimshaw"
        assert single.start == datetime(2026, 10, 6, 6, 0, tzinfo=UTC)
        assert single.end == datetime(2026, 10, 6, 9, 0, tzinfo=UTC)
        assert single.network is not None
        assert single.network.id == "bbc_6music"
        assert single.progress is None  # plain seconds, not the listener's progress

    def test_every_broadcast_in_a_listing_parses(self):
        items = Parser().parse_node(load("BROADCASTS_PID_ONLY.json")["data"])
        assert isinstance(items, list)
        assert len(items) == 30
        assert all(i.broadcast_pid for i in items)
        assert all(i.pid for i in items)

    def test_ended_broadcast_with_a_version_keeps_all_three_ids(self):
        broadcast = load("BROADCASTS_PID_ONLY.json")["data"][0]
        broadcast = copy.deepcopy(broadcast)
        broadcast["on_air"] = False
        broadcast["programme"]["availability"] = {"id": "p0vers01", "duration": 100}
        item = Parser().parse_node(broadcast)
        assert item.broadcast_pid == broadcast["pid"]  # type: ignore[union-attr]
        assert item.vpid == "p0vers01"  # type: ignore[union-attr]
        assert item.pid == broadcast["programme"]["urn"].rsplit(":", 1)[-1]  # type: ignore[union-attr]


class TestSegmentOffset:
    def test_real_segments_have_typed_offsets(self):
        segments = Parser().parse_container(load("SEGMENTS.json"))
        assert isinstance(segments, list)
        first = segments[0]
        assert isinstance(first, Segment)
        assert first.offset == SegmentOffset(
            start=6958, end=7157, label="Now Playing", now_playing=True
        )
        assert segments[1].offset.now_playing is False  # type: ignore[union-attr]

    def test_offset_survives_serialisation(self):
        segment = Parser().parse_container(load("SEGMENTS.json"))[0]  # type: ignore[index]
        assert Segment.from_dict(segment.to_dict()).offset == segment.offset  # type: ignore[union-attr]


class TestPolling:
    async def test_modules_with_polling_are_exposed(self):
        svc, _ = service()
        polling = await svc.polling("bbc_radio_four")
        assert set(polling) == {"live_play_area", "recent_tracks"}
        assert polling["live_play_area"].wait_before_poll_sec == 1800
        assert polling["recent_tracks"] == Polling(
            uri=RECENT_TRACKS_URI, wait_before_poll_sec=30
        )

    async def test_template_is_rendered(self):
        polling = (await service()[0].polling("bbc_radio_four"))["live_play_area"]
        assert "offset=0&limit=5" in polling.render(offset=0, limit=5)

    async def test_experience_is_only_fetched_once(self):
        svc, requests = service()
        await svc.polling("bbc_radio_four")
        await svc.polling("bbc_radio_four")
        assert requests.urls == ["PLAY_EXPERIENCE"]


class TestOnAir:
    async def test_first_programme_of_the_experience(self):
        svc, requests = service()
        item = await svc.on_air("bbc_radio_four", now=ON_AIR)
        assert item is not None
        assert item.broadcast_pid == "p0p6nq1b"
        assert requests.urls == ["PLAY_EXPERIENCE"]

    async def test_later_programmes_come_from_the_same_list(self):
        svc, requests = service()
        item = await svc.on_air("bbc_radio_four", now=ON_AIR + timedelta(minutes=45))
        assert item is not None
        assert item.broadcast_pid == "p0p6nq1d"
        assert requests.urls == ["PLAY_EXPERIENCE"]

    async def test_wait_is_respected_then_the_poll_is_used(self):
        clock = Clock()
        poll = {"data": load("LIVE_STATION_DETAILS.json")["data"][0]["data"][1:]}
        svc, requests = service(clock, **{POLL_URL: poll})
        await svc.on_air("bbc_radio_four", now=ON_AIR)
        clock.now += 1799
        await svc.on_air("bbc_radio_four", now=ON_AIR)
        assert requests.urls == ["PLAY_EXPERIENCE"]
        clock.now += 2
        item = await svc.on_air("bbc_radio_four", now=ON_AIR + timedelta(minutes=45))
        assert requests.urls == ["PLAY_EXPERIENCE", POLL_URL]
        assert item is not None
        assert item.broadcast_pid == "p0p6nq1d"

    async def test_nothing_current_polls_early(self):
        poll = {"data": load("LIVE_STATION_DETAILS.json")["data"][0]["data"][1:]}
        svc, requests = service(**{POLL_URL: poll, "SCHEDULE": load("SCHEDULE.json")})
        await svc.on_air("bbc_radio_four", now=ON_AIR)
        # Past everything the experience listed, well inside the wait
        item = await svc.on_air("bbc_radio_four", now=ON_AIR + timedelta(hours=4))
        assert POLL_URL in requests.urls
        assert item is None


class TestRefreshHistory:
    @staticmethod
    def segments_responses():
        # The real segments capture, whose newest offset is 7157s in
        return {RECENT_URL: load("SEGMENTS.json")}

    async def test_merges_real_segments_against_the_programme_start(self):
        svc, _ = service(**self.segments_responses())
        # Programme "started" 7300s before the poll so the offsets are in the past
        now = ON_AIR
        item = await svc.on_air("bbc_radio_four", now=now)
        assert item is not None
        item.start = now - timedelta(seconds=7300)
        history = await svc.refresh_history("bbc_radio_four", now=now)
        assert len(history) == 4
        result = history.lookup(now - timedelta(seconds=7300 - 7000))
        assert isinstance(result, Track)
        assert result.segment.id == "p0pbhqfh"
        assert isinstance(history.lookup(now - timedelta(seconds=7300 - 6950)), Speech)
        assert isinstance(history.lookup(now - timedelta(days=1)), Unknown)

    async def test_polls_no_faster_than_the_wait(self):
        clock = Clock()
        svc, requests = service(clock, **self.segments_responses())
        item = await svc.on_air("bbc_radio_four", now=ON_AIR)
        assert item is not None
        item.start = ON_AIR - timedelta(seconds=7300)
        for _ in range(3):
            await svc.refresh_history("bbc_radio_four", now=ON_AIR)
        assert requests.urls.count(RECENT_URL) == 1
        clock.now += 30
        await svc.refresh_history("bbc_radio_four", now=ON_AIR)
        assert requests.urls.count(RECENT_URL) == 2

    async def test_station_without_recent_tracks_polling_stays_empty(self):
        requests = FakeRequests({"PLAY_EXPERIENCE": load("LIVE_STATION_DETAILS.json")})
        svc = ScheduleService(requests=requests)  # type: ignore[arg-type]
        history = await svc.refresh_history("bbc_radio_four")
        assert len(history) == 0
        assert requests.urls == ["PLAY_EXPERIENCE"]


class TestSegmentLimit:
    async def test_limit_is_clamped_to_what_the_api_accepts(self):
        calls = []

        class Requests:
            async def get_json_response(self, url, url_args=None, **kwargs):
                calls.append(kwargs["params"]["limit"])
                return {"data": []}

        svc = ScheduleService(requests=Requests())  # type: ignore[arg-type]
        await svc.recently_played_items("bbc_6music", results=100)
        await svc.recently_played_items("bbc_6music", results=0)
        assert calls == [SEGMENT_LIMIT_MAX, 1]


class TestUniqueBroadcasts:
    def test_25_hour_schedule_day_overlap_is_deduped(self):
        """A real schedule day's items repeated from the next day."""
        day = Parser().parse_schedule(load("SCHEDULE_DATE.json"))
        items = list(day.sub_items)
        # The 25 hour day overlaps the next day's schedule by its last hour
        next_day = items[-3:] + items[:2]
        merged = unique_broadcasts([*items, *next_day])
        assert [i.id for i in merged] == [
            *(i.id for i in items),
        ] or len(merged) == len(items)
        assert len({i.id for i in merged}) == len(merged)

    def test_same_episode_repeated_in_two_broadcasts_is_kept(self):
        a = Parser().parse_node(load("BROADCAST.json"))
        b = copy.deepcopy(a)
        b.id = "p0otherbc"  # type: ignore[union-attr]
        assert len(unique_broadcasts([a, b])) == 2  # type: ignore[list-item]
        assert isinstance(a, ScheduleItem) and not isinstance(a, RadioShow)
