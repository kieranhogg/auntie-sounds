from dataclasses import dataclass
from datetime import datetime as dt
from pprint import pformat


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

    def __str__(self):
        return pformat(self)


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
    station: Station

    @property
    def can_seek(self):
        # For future development
        return False


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
