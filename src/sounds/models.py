from dataclasses import asdict, dataclass, field
from datetime import datetime as dt
from logging import Logger
from pprint import pformat
from typing import Any, List, Optional, Sequence
from warnings import deprecated
from zoneinfo import ZoneInfo

import pytz

from sounds import models
from sounds.utils import image_from_recipe, network_logo

type SoundsTypes = (
    models.Category
    | models.CategoryItemContainer
    | models.Container
    | models.Collection
    | models.LiveStation
    | models.MenuItem
    | models.Podcast
    | models.PodcastEpisode
    | models.RadioClip
    | models.RadioSeries
    | models.RadioShow
    | models.RecommendedMenuItem
    | models.Segment
    | models.Schedule
    | models.ScheduleItem
    | models.Station
    | models.StationSearchResult
)


def _parse_datetime(value):
    return dt.fromisoformat(value) if isinstance(value, str) else value


class SerializableMixin:
    def to_dict(self):
        return asdict(self)  # ty:ignore[invalid-argument-type]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Segment:
        return cls(**data)  # ty:ignore[invalid-return-type]

    def __str__(self):
        return pformat(self)

    def __repr__(self):
        if hasattr(self, "id"):
            return f"{type(self).__name__}({self.id})"
        return super().__repr__()


class IdentifiableMixin:
    urn: str | None

    @property
    def item_id(self):
        if self.urn:
            return self.urn.rsplit(":", 1)[-1]
        return getattr(self, "pid", None) or getattr(self, "id", None)


class ImageMixin:
    IMAGE_SIZE = 1280

    def __post_init__(self):
        self.process_image()

    def process_image(self):
        if self.image_url:
            self.image_url = image_from_recipe(
                self.image_url,
                size=self.IMAGE_SIZE,
            )


@dataclass(kw_only=True)
class BaseObject(SerializableMixin):
    """Base class for all objects with common functionality."""

    type: str | None = None
    uris: dict = field(default_factory=dict)
    recommendation: dict | None = None

    def __post_init__(self):
        pass


@dataclass(kw_only=True)
class Network(SerializableMixin):
    """Represents a network/brand with basic metadata."""

    id: str
    key: str | None = None
    short_title: str | None = None
    logo_url: str | None = None
    current_programme: LiveProgramme | None = None
    sort: int | None = None
    group: str | None = None
    contacts: str | None = None
    services: str | None = None
    promoted_category_summaries: str | None = None
    active: bool | None = None
    international: bool | None = None

    def __post_init__(self):
        if self.logo_url:
            self.logo_url = network_logo(self.logo_url)

    def __repr__(self):
        # klass = str(type(self)).rsplit(".", 1)[-1].replace("'>", "")
        return f"{type(self).__name__}({self.id})"


@dataclass(kw_only=True)
class Container(BaseObject, IdentifiableMixin):
    """Base container for organizing content - not directly playable."""

    id: str
    title: str | None = None
    description: str | None = None
    image_url: str | None = None
    synopses: dict = field(default_factory=dict)
    titles: dict = field(default_factory=dict)
    urn: str | None = None
    network: Network | None = None
    sub_items: list[SoundsTypes] | None = None


@dataclass(kw_only=True)
class ImageContainer(Container):
    IMAGE_SIZE = 1280

    def __post_init__(self):
        if self.image_url:
            self.image_url = image_from_recipe(
                self.image_url,
                size=self.IMAGE_SIZE,
            )


@dataclass(kw_only=True, slots=True)
class PlayableItem(BaseObject, IdentifiableMixin):
    """Base class for actual playable content."""

    id: str
    urn: str | None = None
    pid: str | None = None
    type: str | None = None
    duration: dict | None = None
    progress: dict | None = None
    image_url: str | None = None
    titles: dict = field(default_factory=dict)
    synopses: dict = field(default_factory=dict)
    network: Network | None = None
    container: Container | None = None
    start: dt | None = None
    end: dt | None = None
    release: dict | None = None
    availability: dict | None = None
    stream: str | None = None

    def __post_init__(self):
        self.start = _parse_datetime(self.start)
        self.end = _parse_datetime(self.end)
        if self.urn:
            self.pid = self.urn.rsplit(":", 1)[-1]

    def is_live(self, timezone: ZoneInfo | pytz.tzinfo.BaseTzInfo) -> bool:
        if self.start and self.end:
            now = dt.now(tz=timezone)
            return self.start <= now < self.end
        return False

    def has_already_aired(self, timezone: ZoneInfo | pytz.tzinfo.BaseTzInfo) -> bool:
        if self.end:
            return dt.now(tz=timezone) > self.end
        return True


class TimedContent:
    """Mixin for content with timing information."""

    def is_live(self, timezone: ZoneInfo | pytz.tzinfo.BaseTzInfo) -> bool:
        now = dt.now(tz=timezone)
        return self.start <= now < self.end  # type: ignore

    def has_already_aired(self, timezone: ZoneInfo | pytz.tzinfo.BaseTzInfo) -> bool:
        return dt.now(tz=timezone) > self.end  # type: ignore


@dataclass(kw_only=True)
@deprecated("Broadcast has been deprecated in favour of LiveStation and ScheduleItem")
class Broadcast:
    """Represents a broadcast item."""

    type: str
    pid: str
    start: dt
    end: dt
    service_id: str
    duration: int
    progress: int
    live: bool
    blanked: bool
    repeat: bool
    critical: bool
    on_air: bool
    programme: RadioShow

    def __post_init__(self):
        self.start = _parse_datetime(self.start)
        self.end = _parse_datetime(self.end)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.pid})"


@dataclass(kw_only=True)
class ScheduleItem(ImageMixin, PlayableItem):
    """Represents a scheduled program item."""

    def __post_init__(self):
        super().__post_init__()
        self.start = _parse_datetime(self.start)
        self.end = _parse_datetime(self.end)
        self.process_image()


@dataclass(kw_only=True)
class Station(Container):
    """Represents a radio/media station."""

    local: bool = False
    stream: Stream | None = None
    schedule: Schedule | None = None


@dataclass(kw_only=True)
class StationSearchResult(SerializableMixin, IdentifiableMixin):
    """Represents a search result showing a station. Keys are different enough to warrant a separate model"""

    id: str
    type: str
    urn: str
    service_id: str
    episode_image_url: str | None
    station_image_url: str | None
    station_name: str
    title: str
    short_synopsis: str
    progress: dict[int, str]
    duration: dict[int, str]

    def __post_init__(self):
        if self.station_image_url:
            self.station_image_url = network_logo(self.station_image_url)
        if self.episode_image_url:
            self.episode_image_url = image_from_recipe(self.episode_image_url, size=640)


@dataclass(kw_only=True)
class LiveProgramme(PlayableItem, ImageMixin):
    def __post_init__(self):
        super().__post_init__()
        self.process_image()


@dataclass(kw_only=True)
class LiveStation(PlayableItem, IdentifiableMixin, ImageMixin):
    local: bool = False
    schedule: Schedule | None = None

    def __post_init__(self):
        super().__post_init__()
        self.process_image()


@dataclass(kw_only=True)
class Stream(TimedContent, SerializableMixin, ImageMixin):
    """Represents a station stream."""

    id: str
    uri: str
    image_url: str | None
    show_title: str
    show_description: str
    container: Any | None = None

    @property
    def can_seek(self) -> bool:
        """Indicates if the stream supports seeking."""
        return False  # Always False for now

    def __post_init__(self):
        super().__post_init__()
        self.process_image()


@dataclass(kw_only=True)
class Segment(SerializableMixin, ImageMixin):
    """Represents a segment within a stream."""

    id: str
    segment_type: str
    titles: dict
    image_url: str | None
    offset: dict
    uris: list[dict[str, str]]

    @property
    def spotify_url(self):
        spotify = next(
            (uri for uri in self.uris if uri.get("label") == "Spotify"), None
        )
        if spotify:
            return spotify.get("uri")
        return None


@dataclass(kw_only=True)
class Schedule(Container):
    """Represents a schedule for a given date."""

    id: str
    # title is the date of the schedule
    sub_items: list[ScheduleItem] | None

    def get_current_item(
        self,
        timezone: ZoneInfo | pytz.tzinfo.BaseTzInfo | None,
    ) -> ScheduleItem | None:
        """Get the currently airing schedule item."""
        if not timezone:
            timezone = pytz.timezone("UTC")
        if self.sub_items and isinstance(self.sub_items, list):
            for item in self.sub_items:
                if isinstance(item, ScheduleItem) and item.is_live(timezone):
                    return item
        return None


# Specific content types
@dataclass(kw_only=True)
class RadioShow(PlayableItem, TimedContent, ImageMixin, IdentifiableMixin):
    """Represents a playable radio show."""

    @property
    def item_id(self):
        return self.pid

    def __post_init__(self):
        super().__post_init__()
        self.process_image()


# Specific content types
@dataclass(kw_only=True)
class RadioClip(PlayableItem, TimedContent, ImageMixin, IdentifiableMixin):
    """Represents a playable radio clip."""

    def __post_init__(self):
        super().__post_init__()
        self.process_image()


@dataclass(kw_only=True)
class PodcastEpisode(PlayableItem, ImageMixin, IdentifiableMixin):
    """Represents a playable podcast episode."""

    def __post_init__(self):
        super().__post_init__()
        self.process_image()


@dataclass(kw_only=True)
class Podcast(ImageContainer):
    """Represents a podcast container (holds episodes)."""


@dataclass(kw_only=True)
class RadioSeries(ImageContainer):
    """Represents a radio series container (holds episodes)."""


@dataclass(kw_only=True)
class Collection(ImageContainer):
    """Represents a collection container."""


@dataclass(kw_only=True)
class Category(ImageContainer):
    """Represents a content category."""


@dataclass(kw_only=True)
class CategoryItemContainer(SerializableMixin):
    """Represents a content category container."""

    id: str | None = None
    total: int
    limit: int
    offset: int
    sub_items: list[SoundsTypes] | None = None


@dataclass(kw_only=True)
class Playlist(ImageContainer):
    """Represents a playlist container."""


@dataclass(kw_only=True)
class CollectionItemContainer(CategoryItemContainer):
    """Represents a content collection container."""


@dataclass(kw_only=True)
class MenuItem(ImageContainer):
    """Represents a menu item container."""

    def get(
        self, key: str
    ) -> (
        CategoryItemContainer
        | Container
        | LiveStation
        | PodcastEpisode
        | RadioClip
        | RadioShow
        | Segment
        | ScheduleItem
        | StationSearchResult
        | None
    ):
        """Get a sub-menu item by ID."""
        if self.sub_items:
            for item in self.sub_items:
                if hasattr(item, "id") and item.id == key:
                    return item
        return None


@dataclass(kw_only=True)
class RecommendedMenuItem(MenuItem):
    """Represents a recommended menu item."""


@dataclass(kw_only=True)
class Menu(SerializableMixin):
    """Represents a menu container with items."""

    sub_items: list[MenuItem] | Sequence[MenuItem] | None

    def get(self, key: str) -> MenuItem | RecommendedMenuItem | None:
        """Get a menu item by ID."""
        if self.sub_items:
            for item in self.sub_items:
                if hasattr(item, "id") and item.id == key:
                    return item
        return None


@dataclass(kw_only=True)
class DisplayItem(Container):
    item: PlayableItem | None = None


@dataclass(kw_only=True)
class PromoItem(Container):
    item: PlayableItem


@dataclass(kw_only=True)
class SearchResults(SerializableMixin):
    stations: list[LiveStation | StationSearchResult]
    shows: list[Podcast | RadioShow]
    episodes: list[PodcastEpisode | RadioClip | RadioShow]


@dataclass(kw_only=True)
class Header(BaseObject):
    pass
