from dataclasses import dataclass
from datetime import datetime as dt
from pprint import pformat


@dataclass
class Stream:
    """A container for holding attributes related to a stream"""

    id: str
    start: dt
    end: dt
    uri: str
    image_url: str
    network: str
    network_logo: str
    show_title: str
    show_description: str

    @property
    def can_seek(self):
        # For future development
        return False


@dataclass
class Station:
    """A container for holding attributes related to a station"""

    id: str
    name: str
    description: str
    logo_url: str

    def __str__(self):
        return pformat(self)


@dataclass
class Segment:
    """A container for holding attributes related to a segment item (usually a song)"""

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
