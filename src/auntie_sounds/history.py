"""The tracks a station has played, with the times they were on air.

The API only lists a station's last few tracks. A SegmentHistory keeps every track from
each poll, so a listener who is behind live, for example after restarting a programme,
can be told which track they are hearing. This only works for tracks that the API listed
while the history was being polled.

The API gives each track's start and end as seconds from when its programme really
started. That can be several minutes after the scheduled start, for example after a news
bulletin, so the real start is estimated from the tracks' labels (see StartEstimate).
The history stores each track's start and end as UTC times. All times are when the audio
was broadcast, before any delay in reaching the listener.
"""

import logging
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import chain

from auntie_sounds.models import Segment

logger = logging.getLogger(__name__)

# Tracks that ended longer ago than this are removed, so a process that runs for
# days doesn't keep every track it has seen
DEFAULT_MAX_AGE = timedelta(hours=12)
# A track whose start works out more than this after the poll is from the previous
# programme. A smaller gap comes from our clock differing from the BBC's.
FUTURE_SLACK = timedelta(minutes=1)
# The furthest a programme's real start is assumed to be from its scheduled start.
# The largest seen was about 5 minutes, on Radio 2 after a news bulletin. A label
# that puts the start further away belongs to a track from the previous programme.
MAX_START_SHIFT = timedelta(minutes=10)

_MINUTES_AGO_LABEL = re.compile(r"(\d+) Minutes? Ago")


@dataclass(frozen=True, slots=True)
class TimedSegment:
    """A segment with the UTC times it started and ended."""

    segment: Segment
    start: datetime
    end: datetime


@dataclass(frozen=True, slots=True)
class Track:
    """A track was on air at the time asked about."""

    timed: TimedSegment

    @property
    def segment(self) -> Segment:
        return self.timed.segment


@dataclass(frozen=True, slots=True)
class Speech:
    """
    No track was playing at the time, but known tracks played before and after it.

    Usually the presenter is talking.
    """


@dataclass(frozen=True, slots=True)
class Unknown:
    """
    The time is before the earliest known track started, or after the latest one
    ended.
    """


type Lookup = Track | Speech | Unknown


def minutes_ago(label: str | None) -> int | None:
    """
    Return the whole minutes since a track ended, read from its label.

    The API labels a finished track "Less Than a Minute Ago", "1 Minute Ago" or
    "N Minutes Ago". Returns None for "Now Playing" and any other label.
    """
    if label == "Less Than a Minute Ago":
        return 0
    match = _MINUTES_AGO_LABEL.fullmatch(label or "")
    return int(match[1]) if match else None


class StartEstimate:
    """
    An estimate of how long after its scheduled start a programme really started.

    The API labels each finished track with the whole minutes since it ended,
    rounded down. Taking the track's end offset and the labelled minutes away from
    the poll time puts the programme's real start within a one-minute window. Up to
    about one label in ten is a minute off from the rest. The estimate is the middle
    of the range covered by the most windows, so those labels have no effect.
    """

    def __init__(self) -> None:
        # Each window is the earliest and latest real start, in seconds after the
        # scheduled start
        self._windows: list[tuple[float, float]] = []

    @property
    def shift(self) -> timedelta | None:
        """
        How long after its scheduled start the programme began, or None before any
        window is added.
        """
        # A window's start adds 1 to `overlapping`, and that window's end is sorted
        # after it, so events[index + 1] exists. The next event is where `overlapping`
        # changes again, so it ends the range.
        events = sorted(
            chain.from_iterable(
                ((earliest, 1), (latest, -1)) for earliest, latest in self._windows
            ),
            key=lambda event: (event[0], -event[1]),
        )
        most_overlapping, overlapping = 0, 0
        best_range_start = best_range_end = 0.0
        for index, (seconds, change) in enumerate(events):
            overlapping += change
            if overlapping > most_overlapping:
                # The count only rises at a window's start, and every start has a
                # later end, so events[index + 1] exists
                most_overlapping = overlapping
                best_range_start, best_range_end = seconds, events[index + 1][0]
        if not most_overlapping:
            return None
        return timedelta(seconds=(best_range_start + best_range_end) / 2)

    def add(self, earliest: float, latest: float) -> None:
        """Add the window one track's label gives."""
        self._windows.append((earliest, latest))


def _start_window(
    segment: Segment, scheduled_start: datetime, now: datetime
) -> tuple[float, float] | None:
    """
    Return the earliest and latest real start of the programme that a track's label
    allows, in seconds after the scheduled start.

    Returns None for the track that is playing, for a label that isn't a time, and
    for a window more than MAX_START_SHIFT from the scheduled start.
    """
    offset = segment.offset
    if offset is None or offset.end is None or offset.now_playing:
        return None
    minutes_since_end = minutes_ago(offset.label)
    if minutes_since_end is None:
        return None
    # The track ended between `minutes_since_end` and one minute more before the
    # poll. Taking that and the track's end offset away from the poll gives the
    # window.
    latest = (now - scheduled_start).total_seconds() - offset.end - 60 * minutes_since_end
    earliest = latest - 60
    max_shift_seconds = MAX_START_SHIFT.total_seconds()
    if latest < -max_shift_seconds or earliest > max_shift_seconds:
        return None
    return earliest, latest


def _timed_segment(segment: Segment, real_start: datetime) -> TimedSegment | None:
    """
    Return the segment with its UTC start and end, given when its programme really
    started.

    Returns None if the segment has no start or end offset.
    """
    offset = segment.offset
    if offset is None or offset.end is None:
        return None
    return TimedSegment(
        segment=segment,
        start=real_start + timedelta(seconds=offset.start),
        end=real_start + timedelta(seconds=offset.end),
    )


def current_programme_segments(segments: Iterable[Segment]) -> list[Segment]:
    """
    Return the segments from the programme on air, newest first.

    Just after a change of programme, the API's latest segments include the end of
    the previous one. Its offsets count from its own start, so they are larger than
    the current programme's. Going from newest to oldest, the offsets get smaller,
    then jump up at the first segment of the previous programme.

    :param segments: Segments as the API returned them, newest first.
    """
    programme_segments: list[Segment] = []
    previous_offset_start: int | None = None
    for segment in segments:
        if segment.offset is None:
            continue
        if (
            previous_offset_start is not None
            and segment.offset.start > previous_offset_start
        ):
            break
        programme_segments.append(segment)
        previous_offset_start = segment.offset.start
    return programme_segments


class SegmentHistory:
    """The tracks one station has played, with the UTC times each was on air."""

    def __init__(self, max_age: timedelta = DEFAULT_MAX_AGE) -> None:
        self.max_age = max_age
        self._timed_segments: dict[str, TimedSegment] = {}
        # The scheduled start of the programme each track was played in, by
        # segment id
        self._scheduled_start_by_segment: dict[str, datetime] = {}
        # Start estimates, by the programme's scheduled start
        self._start_estimates: dict[datetime, StartEstimate] = {}

    @property
    def oldest_start(self) -> datetime | None:
        """
        When the first track in the history started, or None if the history is empty.
        """
        first_track_start = min(
            (timed.start for timed in self._timed_segments.values()), default=None
        )
        logger.debug("First track in history started at: %s", first_track_start)
        return first_track_start

    @property
    def newest_end(self) -> datetime | None:
        """When the latest known track ended."""
        latest_known_end = max(
            (timed.end for timed in self._timed_segments.values()), default=None
        )
        logger.debug("Latest known end time: %s", latest_known_end)
        return latest_known_end

    def programme_start(self, scheduled_start: datetime) -> datetime:
        """
        Return when a programme really started, estimated from its tracks' labels.

        Returns the scheduled start until a poll has listed one of its finished
        tracks.

        :param scheduled_start: The programme's scheduled start, in UTC.
        """
        estimate = self._start_estimates.get(scheduled_start)
        shift = estimate.shift if estimate is not None else None
        shift_display = f"{shift.total_seconds():+.1f}s" if shift is not None else None
        logger.debug("Current esimated start time shift: %s", shift_display)
        return scheduled_start + (shift or timedelta(0))

    def merge(
        self,
        segments: Sequence[Segment],
        programme_start: datetime,
        now: datetime | None = None,
    ) -> int:
        """
        Add a poll's tracks to the history, returning how many were added or moved.

        The API doesn't say which programme a track was played in. Only tracks from
        the programme on air can be given times, from its start. Tracks from the
        previous programme are left out, unless an earlier poll stored them while
        that programme was on air.

        Each poll's labels improve the estimate of when the programme on air really
        started. Its tracks from earlier polls are moved to match the new estimate.

        :param segments: Segments as the API returned them, newest first.
        :param programme_start: When the programme on air was scheduled to start, in
            UTC.
        :param now: The time of the poll, in UTC. Defaults to the current time.
        """
        now = now or datetime.now(UTC)
        current_segments = [
            segment
            for segment in current_programme_segments(segments)
            # Skip a track already stored under another programme. An earlier poll
            # stored it while that programme was on air.
            if self._scheduled_start_by_segment.get(segment.id, programme_start)
            == programme_start
        ]
        start_estimate = self._start_estimates.setdefault(
            programme_start, StartEstimate()
        )
        for segment in current_segments:
            if (window := _start_window(segment, programme_start, now)) is not None:
                start_estimate.add(*window)
        estimated_start = self.programme_start(programme_start)

        # Start with this programme's tracks from earlier polls, so they move to the
        # new estimate too
        segments_to_place = {
            segment_id: self._timed_segments[segment_id].segment
            for segment_id, scheduled_start in self._scheduled_start_by_segment.items()
            if scheduled_start == programme_start
        }
        for segment in current_segments:
            timed = _timed_segment(segment, estimated_start)
            if timed is None:
                continue
            if timed.start > now + FUTURE_SLACK:
                # A start this far after the poll means the track is from the
                # previous programme
                logger.debug("Segment %s starts in the future, ignoring", segment.id)
                continue
            segments_to_place[segment.id] = segment

        merged = 0
        for segment_id, segment in segments_to_place.items():
            timed = _timed_segment(segment, estimated_start)
            if timed is not None and self._timed_segments.get(segment_id) != timed:
                self._timed_segments[segment_id] = timed
                self._scheduled_start_by_segment[segment_id] = programme_start
                merged += 1
        self._drop_old_tracks(now)
        return merged

    def lookup(self, at: datetime, delay: timedelta = timedelta(0)) -> Lookup:
        """
        Return what was playing on the station at a time.

        Where two tracks overlap, the one that started later is returned. Times
        before the earliest known track started, or after the latest one ended, are
        Unknown.

        :param at: The time in UTC.
        :param delay: How far behind broadcast the listener is. The lookup is for at
            minus delay. Leave it at zero if at is already a broadcast time.
        """
        at -= delay
        newest_first = sorted(
            self._timed_segments.values(), key=lambda timed: timed.start, reverse=True
        )
        if not newest_first or at < newest_first[-1].start:
            return Unknown()
        for timed in newest_first:
            if timed.start <= at < timed.end:
                return Track(timed)
        if at >= max(timed.end for timed in newest_first):
            return Unknown()
        return Speech()

    def _drop_old_tracks(self, now: datetime) -> None:
        """
        Remove tracks that finished playing more than max_age ago.

        For each removed track, the record of which programme it was played in is
        removed too. A programme's estimated start is removed once none of its tracks
        are left and it was scheduled to start more than max_age ago. A programme
        scheduled to start less than max_age ago keeps its estimate whether or not it
        has tracks. The programme on air often has none stored for its first few
        minutes.
        """
        cutoff = now - self.max_age
        self._timed_segments = {
            segment_id: timed
            for segment_id, timed in self._timed_segments.items()
            if timed.end >= cutoff
        }
        self._scheduled_start_by_segment = {
            segment_id: scheduled_start
            for segment_id, scheduled_start in self._scheduled_start_by_segment.items()
            if segment_id in self._timed_segments
        }
        programmes_with_tracks = set(self._scheduled_start_by_segment.values())
        self._start_estimates = {
            scheduled_start: estimate
            for scheduled_start, estimate in self._start_estimates.items()
            if scheduled_start in programmes_with_tracks or scheduled_start >= cutoff
        }

    def __len__(self) -> int:
        return len(self._timed_segments)
