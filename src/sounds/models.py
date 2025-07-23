from dataclasses import dataclass
from datetime import datetime as dt
from pydantic import BaseModel, ConfigDict, ValidationError
from pprint import pformat
from typing import List, Optional

from pytz import BaseTzInfo


@dataclass
class Stream:
    """
    Represents a station stream.

    Attributes:
        id (str): Unique identifier for the stream.
        start (datetime): Start time of the stream.
        end (datetime): End time of the stream.
        uri (str): URL to access the stream.
        image_url (str): URL to a thumbnail for the current programme.
        network (str): Name of the station.
        network_logo (str): URL to the station's logo image.
        show_title (str): Title of the show being streamed.
        show_description (str): Description of the show.

    Properties:
        can_seek (bool): Indicates if the stream supports seeking. (Always False for now.)
    """

    id: str
    start: dt
    end: dt
    uri: str
    image_url: str
    show_title: str
    show_description: str
    station: "Station"

    def __str__(self):
        return pformat(self)


@dataclass
class Segment:
    """
    Represents a segment within a stream, such as a song or program section.

    Attributes:
        id (str): Unique identifier for the segment.
        primary_title (str): Primary title (e.g., song title or segment name).
        secondary_title (str): Secondary title (e.g., artist or contributor).
        tertiary_title (str): Appears to be unused for most segments.
        entity_title (str): Appears to always be the same as primary_title.
        image_url (str): URL to an image representing the segment.
        start_seconds (int): Start time of the segment in seconds.
        end_seconds (int): End time of the segment in seconds.
        label (str): Text description of either 'Now playing' or e.g. '2 minutes ago'
        now_playing (bool): Indicates whether this segment is currently playing.
    """

    id: str
    primary_title: str
    secondary_title: str
    tertiary_title: str
    entity_title: str
    image_url: str
    start_seconds: int
    end_seconds: int
    label: str
    now_playing: bool

    def __str__(self):
        return pformat(self)


@dataclass
class ScheduleItem:
    id: str
    urn: str
    start: dt
    end: dt
    duration: int
    short_synopsis: str
    medium_synopsis: str
    long_synopsis: str
    image_url: str
    primary_title: str
    secondary_title: str
    tertiary_title: Optional[str]
    episode_id: Optional[str] = None
    container_id: Optional[str] = None
    stream: Optional[str] = None

    @property
    def vpid(self):
        try:
            return self.urn.rsplit(":", 1)[1]
        except KeyError:
            return None

    def is_live(self, timezone: BaseTzInfo):
        return self.start >= dt.now(tz=timezone) < self.end

    def has_already_aired(self, timezone: BaseTzInfo):
        return dt.now(tz=timezone) > self.end

    def __str__(self):
        return pformat(self)


@dataclass
class Schedule:
    date: dt
    schedule_list: list[ScheduleItem]

    def get_current_item(self):
        pass

    def __str__(self):
        return pformat(self)


@dataclass
class Station:
    """
    Represents a radio or media station with its metadata.

    Attributes:
        id (str): Unique identifier for the station.
        name (str): Human-readable name of the station.
        description (str): Description of the station's content or focus.
        logo_url (str): URL to the station's logo image.
        local (bool): Flag indicating whether the station is considered local.
    """

    id: str
    name: str
    description: str
    logo_url: str
    local: bool
    stream: Optional[Stream] = None
    schedule: Optional[List[ScheduleItem]] = None

    def __str__(self):
        return pformat(self)


@dataclass
class Network:
    id: str
    key: str
    short_title: str
    logo_url: str


@dataclass
class PlayableItem:
    id: str
    urn: str
    network: Network | None
    duration: int | None
    progress: int | None
    synopses: dict
    image_url: str
    titles: dict
    start: dt | None = None
    end: dt | None = None


@dataclass
class MenuItem:
    id: str
    title: str
    description: str
    data: list[PlayableItem]


@dataclass
class Menu:
    items: list[MenuItem]
