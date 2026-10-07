"""What a station played and when, built up from its recent tracks.

The API only ever shows a short window of recent tracks. Merging each poll
into a SegmentHistory keeps the older ones, so a listener who is behind the
live edge (for example after restarting a show) can still be told which track
they are hearing, as long as that track was seen while it was in the window.

Segment offsets count from the start of the broadcast they belong to, so each
one is stored as an absolute UTC time. All times here are broadcast time.
"""

import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sounds.models import Segment

logger = logging.getLogger(__name__)

# Older tracks than this are dropped, so a long-running process doesn't keep growing
DEFAULT_MAX_AGE = timedelta(hours=12)
# A track can't have started later than now, but the clocks involved are loose
FUTURE_SLACK = timedelta(minutes=1)


@dataclass(frozen=True, slots=True)
class TimedSegment:
    """A segment with the absolute times it was on air."""

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
    """The time is inside the known history but no track covers it."""


@dataclass(frozen=True, slots=True)
class Unknown:
    """The time is outside the known history, so nothing can be said about it."""


type Lookup = Track | Speech | Unknown


def current_programme_segments(segments: Iterable[Segment]) -> list[Segment]:
    """
    Keep the segments that belong to the programme on air, newest first.

    The API's latest segments can run back into the programme before, whose
    offsets count from its own start. Walking newest first the offsets fall
    within a programme and jump up where the programme before begins.

    :param segments: Segments as the API returned them, newest first.
    """
    current: list[Segment] = []
    previous_start: int | None = None
    for segment in segments:
        if segment.offset is None:
            continue
        if previous_start is not None and segment.offset.start > previous_start:
            break
        current.append(segment)
        previous_start = segment.offset.start
    return current


class SegmentHistory:
    """The tracks a station has played, by segment id."""

    def __init__(self, max_age: timedelta = DEFAULT_MAX_AGE) -> None:
        self.max_age = max_age
        self._entries: dict[str, TimedSegment] = {}

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def oldest_start(self) -> datetime | None:
        """When the earliest known track started."""
        return min((e.start for e in self._entries.values()), default=None)

    @property
    def newest_end(self) -> datetime | None:
        """When the latest known track ended."""
        return max((e.end for e in self._entries.values()), default=None)

    def merge(
        self,
        segments: Sequence[Segment],
        programme_start: datetime,
        now: datetime | None = None,
    ) -> int:
        """
        Add a poll's segments to the history, returning how many were added or moved.

        Only segments from the programme on air can be placed in time, as the
        API doesn't say which programme a segment belongs to. Earlier ones are
        left out, unless they were seen before while their programme was on air.

        :param segments: Segments as the API returned them, newest first.
        :param programme_start: When the programme on air began, in UTC.
        :param now: The time of the poll, in UTC. Defaults to the current time.
        """
        now = now or datetime.now(UTC)
        merged = 0
        for segment in current_programme_segments(segments):
            offset = segment.offset
            if offset is None or offset.end is None:
                continue
            start = programme_start + timedelta(seconds=offset.start)
            if start > now + FUTURE_SLACK:
                # Only the programme before can have offsets that haven't happened yet
                logger.debug("Segment %s starts in the future, ignoring", segment.id)
                continue
            timed = TimedSegment(
                segment=segment,
                start=start,
                end=programme_start + timedelta(seconds=offset.end),
            )
            if self._entries.get(segment.id) != timed:
                self._entries[segment.id] = timed
                merged += 1
        self._prune(now)
        return merged

    def _prune(self, now: datetime) -> None:
        cutoff = now - self.max_age
        self._entries = {
            id_: entry for id_, entry in self._entries.items() if entry.end >= cutoff
        }

    def lookup(self, at: datetime, delay: timedelta = timedelta(0)) -> Lookup:
        """
        Say what was on air at a time.

        Where two tracks overlap the newer one wins. Times before the oldest
        known track, or after the end of the newest, are Unknown.

        :param at: The time in UTC.
        :param delay: How long after broadcast the audio being asked about
            reached the listener. Leave it as zero for a time that is already
            in broadcast time.
        """
        at -= delay
        newest_first = sorted(
            self._entries.values(), key=lambda entry: entry.start, reverse=True
        )
        if not newest_first or at < newest_first[-1].start:
            return Unknown()
        for entry in newest_first:
            if entry.start <= at < entry.end:
                return Track(entry)
        if at >= max(entry.end for entry in newest_first):
            return Unknown()
        return Speech()
