"""Tests for the segment history and position lookup."""

from datetime import UTC, datetime, timedelta
from typing import ClassVar

import pytest

from auntie_sounds.history import (
    SegmentHistory,
    Speech,
    Track,
    Unknown,
    current_programme_segments,
)
from auntie_sounds.models import Segment, SegmentOffset

START = datetime(2026, 10, 6, 6, 0, tzinfo=UTC)
NOW = START + timedelta(minutes=30)


def seg(id_: str, start: int, end: int) -> Segment:
    return Segment(
        id=id_,
        segment_type="music",
        uris=[],
        image_url=None,
        offset=SegmentOffset(start=start, end=end),
    )


def at(seconds: int) -> datetime:
    return START + timedelta(seconds=seconds)


# Newest first, as the API returns them. a ends and b starts a second early.
WINDOW = [seg("c", 900, 1100), seg("b", 399, 700), seg("a", 100, 400)]


@pytest.fixture
def history() -> SegmentHistory:
    history = SegmentHistory()
    history.merge(WINDOW, START, now=NOW)
    return history


class TestLookup:
    def test_inside_a_track(self, history):
        result = history.lookup(at(200))
        assert isinstance(result, Track)
        assert result.segment.id == "a"

    def test_overlap_picks_the_newer_track(self, history):
        result = history.lookup(at(399))
        assert isinstance(result, Track)
        assert result.segment.id == "b"

    def test_track_end_is_exclusive(self, history):
        assert isinstance(history.lookup(at(1100)), Unknown)
        assert isinstance(history.lookup(at(700)), Speech)

    def test_gap_between_tracks_is_speech(self, history):
        assert isinstance(history.lookup(at(800)), Speech)

    def test_before_the_oldest_track_is_unknown(self, history):
        assert isinstance(history.lookup(at(99)), Unknown)

    def test_after_the_newest_track_is_unknown(self, history):
        assert isinstance(history.lookup(at(1200)), Unknown)

    def test_empty_history_is_unknown(self):
        assert isinstance(SegmentHistory().lookup(at(0)), Unknown)

    def test_delay_moves_the_time_back(self, history):
        # 410s heard is 400s broadcast, which is the second a track ended
        assert history.lookup(at(410), delay=timedelta(seconds=10)).segment.id == "b"  # type: ignore[union-attr]

    def test_speech_and_unknown_are_different_types(self, history):
        assert type(history.lookup(at(800))) is not type(history.lookup(at(99)))


class TestMerge:
    def test_overlapping_polls_do_not_duplicate(self, history):
        newer = [seg("d", 1200, 1400), *WINDOW[:2]]
        assert history.merge(newer, START, now=NOW + timedelta(minutes=5)) == 1
        assert len(history) == 4

    def test_history_outlives_the_window(self, history):
        # Later the API only shows d, but a is still known
        history.merge([seg("d", 1200, 1400)], START, now=NOW + timedelta(minutes=5))
        assert history.lookup(at(200)).segment.id == "a"  # type: ignore[union-attr]

    def test_segments_that_have_not_started_are_ignored(self):
        history = SegmentHistory()
        history.merge([seg("x", 5000, 5200)], START, now=NOW)
        assert len(history) == 0

    def test_segment_without_an_end_is_ignored(self):
        history = SegmentHistory()
        loose = Segment(
            id="n",
            segment_type="music",
            uris=[],
            image_url=None,
            offset=SegmentOffset(start=100),
        )
        history.merge([loose], START, now=NOW)
        assert len(history) == 0

    def test_old_tracks_are_pruned(self):
        history = SegmentHistory(max_age=timedelta(hours=1))
        history.merge(WINDOW, START, now=NOW)
        history.merge([], START, now=NOW + timedelta(hours=2))
        assert len(history) == 0

    def test_oldest_and_newest(self, history):
        assert history.oldest_start == at(100)
        assert history.newest_end == at(1100)


class TestProgrammeBoundary:
    """The API's latest segments run back into the programme before."""

    # Walking newest first, 300 jumps up to 3500 where the last programme begins
    POLL: ClassVar[list[Segment]] = [
        seg("new2", 200, 380),
        seg("new1", 20, 300),
        seg("old2", 3500, 3590),
        seg("old1", 3200, 3500),
    ]

    def test_boundary_is_where_start_jumps_up(self):
        kept = current_programme_segments(self.POLL)
        assert [s.id for s in kept] == ["new2", "new1"]

    def test_earlier_programme_is_not_anchored_to_this_one(self):
        history = SegmentHistory()
        history.merge(self.POLL, START, now=NOW)
        assert len(history) == 2

    def test_earlier_programme_kept_if_seen_while_on_air(self):
        history = SegmentHistory()
        previous_start = START - timedelta(hours=1)
        history.merge(
            [seg("old2", 3500, 3590), seg("old1", 3200, 3500)],
            previous_start,
            now=START - timedelta(seconds=5),
        )
        history.merge(self.POLL, START, now=NOW)
        assert {"old1", "old2", "new1", "new2"} == set(history._entries)
        assert history.lookup(START - timedelta(seconds=30)).segment.id == "old2"  # type: ignore[union-attr]

    def test_no_boundary_keeps_everything(self):
        assert len(current_programme_segments(WINDOW)) == 3

    def test_segment_without_offset_is_skipped(self):
        bare = Segment(
            id="z", segment_type="music", uris=[], image_url=None, offset=None
        )
        assert current_programme_segments([bare, *WINDOW]) == WINDOW

    def test_just_after_the_boundary_nothing_new_has_played(self):
        # Five seconds in, every segment is from the last programme and would
        # land in the future if anchored to this one
        history = SegmentHistory()
        history.merge(
            [seg("old2", 3500, 3590)], START, now=START + timedelta(seconds=5)
        )
        assert len(history) == 0
