from collections.abc import Sequence
from copy import copy
from dataclasses import asdict, dataclass, field
from datetime import datetime as dt
from logging import Logger
from pprint import pformat
from typing import Any, Literal, Self
from warnings import deprecated
from zoneinfo import ZoneInfo

import pytz

from sounds.utils import image_from_recipe, network_logo

NETWORK_LOGO_FORMAT = "https://sounds.files.bbci.co.uk/3.12.0/networks/{network_id}/{type}_{size}.{format}"

type SoundsTypes = (
    CategoryItemContainer
    | CollectionItemContainer
    | Container
    | Collection
    | DisplayItem
    | LiveProgramme
    | LiveStation
    | MenuItem
    | Network
    | PlayableItem
    | PlayableNetwork
    | Podcast
    | PodcastEpisode
    | PromoItem
    | RadioClip
    | RadioSeries
    | RadioShow
    | RecommendedMenuItem
    | SearchResults
    | Segment
    | Schedule
    | ScheduleItem
    | Station
    | StationSearchResult
)
"""Types we expect to find within other SoundsTypes."""
type NestedSoundsTypes = ItemCategory | Titles | Synopses | Duration | Progress


###### Helpers ##################################################################
def _parse_datetime(value):
    return dt.fromisoformat(value) if isinstance(value, str) else value


def station_description(station_id):
    descriptions_dict = {
        "bbc_radio_one": "The biggest new pop & all day vibes.",
        "bbc_radio_one_anthems": "All day anthems from the 00s to now.",
        "bbc_radio_one_dance": "The biggest current, future and classic dance vibes.",
        "bbc_1xtra": "Amplifying black music & culture.",
        "bbc_radio_two": "Lift your day with the best tunes from your favourite DJs.",
        "bbc_radio_three": "Adventures in classical.",
        "bbc_radio_three_unwind": "Music to unwind your mind.",
        "bbc_radio_four": "Inquisitive speech radio to make sense of your world.",
        "bbc_radio_fourfm": "Inquisitive speech radio to make sense of your world.",
        "bbc_radio_four_extra": "Journey into the Radio 4 archive.",
        "bbc_radio_five_live": "The voice of the UK - breaking news & live sport.",
        "bbc_radio_five_live_sports_extra": "Extended live sports coverage from Radio 5 Live.",
        "bbc_radio_five_sports_extra_2": "Extended live sports coverage",
        "bbc_radio_five_sports_extra_3": "Extended live sports coverage",
        "bbc_6music": "Music beyond the mainstream.",
        "bbc_radio_six_indie_forever": "Proper indie music… All day, every day.",
        "bbc_asian_network": "Celebrating British Asian identity.",
        "bbc_world_service": "News & views from the BBC's international radio station.",
        "bbc_sounds_news": "Follow the latest developments.",
        "bbc_radio_scotland_fm": "The sound of Scotland's news, sport, music and culture.",
        "bbc_radio_scotland_mw": "",
        "bbc_radio_orkney": "The sound of where you live.",
        "bbc_radio_shetland": "The sound of where you live.",
        "bbc_radio_nan_gaidheal": "Guthan nan Gaidheal gach là as gach ceàrnaidh.",
        "bbc_radio_ulster": "Local news, sport, music and chat.",
        "bbc_radio_foyle": "Local news, sport, music and chat.",
        "bbc_radio_wales_fm": "News, sport, music and entertainment for Wales.",
        "bbc_radio_wales_am": "",
        "bbc_radio_cymru": "Newyddion, cerddoriaeth a chwmni da.",
        "bbc_radio_cymru_2": "Tiwns trwy'r dydd.",
        "cbeebies_radio": "Songs, stories, and fun. It's CBeebies for your ears.",
        "local": "The sound of where you live.",
    }
    return descriptions_dict.get(station_id, None)


###### Mixins ##################################################################
class SerializableMixin:
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)  # type: ignore

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(**data)  # type: ignore

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

    def post_processing(self, logger: Logger) -> None:
        self.process_image()

    def process_image(self):
        if self.image_url:
            self.image_url = image_from_recipe(
                self.image_url,
                size=self.IMAGE_SIZE,
            )


class TimedContent:
    """Mixin for content with timing information."""

    def is_live(self, timezone: ZoneInfo | pytz.tzinfo.BaseTzInfo) -> bool:
        now = dt.now(tz=timezone)
        return self.start <= now < self.end  # type: ignore

    def has_already_aired(self, timezone: ZoneInfo | pytz.tzinfo.BaseTzInfo) -> bool:
        return dt.now(tz=timezone) > self.end  # type: ignore


###### Sub-types ###############################################################
@dataclass(kw_only=True)
class Titles:
    primary: str | None = None
    secondary: str | None = None
    tertiary: str | None = None
    entity_title: str | None = None


@dataclass(kw_only=True)
class Synopses:
    short: str | None = None
    medium: str | None = None
    long: str | None = None


@dataclass(kw_only=True)
class Progress:
    label: str
    value: int


@dataclass(kw_only=True)
class Duration:
    label: str
    value: int


@dataclass(kw_only=True)
class ItemCategory:
    id: str
    key: str | None = None
    title: str | None = None
    type: int


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

    def post_processing(self, logger: Logger) -> None:
        super().post_processing(logger)
        self.process_image()


@dataclass(kw_only=True)
class Segment(SerializableMixin, ImageMixin):
    """Represents a segment within a stream."""

    id: str
    segment_type: str
    titles: Titles = field(
        default_factory=lambda: Titles(
            primary=None, secondary=None, tertiary=None, entity_title=None
        )
    )
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


""":param

        "id": "bbc_radio_one",
          "title": "BBC Radio 1",
          "type": "service",
          "region": "All Regions",
          "coverage": "national",
          "active": true,
          "short_title": "Radio 1",
          "date_ranges": [
            {
              "start": "1967-09-30T05:30:00Z",
              "end": null
            }
          ],
          "default_language": "en",
          "default": true
"""


@dataclass(kw_only=True)
class Service:
    id: str
    title: str | None = None  # present in NETWORKS_DETAILED
    pid: str | None = None  # present in NETWORK_SERVICES
    short_title: str
    type: str
    region: str | None = None  # present in NETWORKS_DETAILED
    coverage: Literal["local", "regional", "national"] = (
        "national"  # present in NETWORKS_DETAILED
    )
    active: str | None = None  # present in NETWORKS_DETAILED
    date_ranges: dict = field(default_factory=dict)  # present in NETWORKS_DETAILED
    default_language: Literal["en", "gd", "ga", "cy"] = (
        "en"  # present in NETWORKS_DETAILED
    )
    default: bool | None = None  # present in NETWORKS_DETAILED


###### Base types ##############################################################
@dataclass(kw_only=True)
class BaseObject(SerializableMixin):
    """Base class for all objects with common functionality."""

    type: str | None = None
    uris: dict = field(default_factory=dict)
    recommendation: dict | None = None

    def post_processing(self, logger: Logger) -> None:
        pass


@dataclass(kw_only=True)
class Network(SerializableMixin):
    """Represents a network/brand with basic metadata.

    Parameters
        id: e.g. bbc_radio_four
    """

    type: Literal["network"] = "network"
    id: str
    key: str | None = None
    short_title: str | None = None
    sort: int | None = None
    description: str | None = None
    # current_programme: LiveProgramme | None = None
    services: list[Station] | None = None
    service: Station | None = None
    default_service_id: str | None = None
    active: bool = True
    coverage: Literal["national", "regional", "local"] | None = None
    international: bool = True
    promoted_category_summaries: dict = field(default_factory=dict)
    date_ranges: dict = field(default_factory=dict)
    logo_url: str | None = None

    def post_processing(self, logger: Logger) -> None:
        # Set default Service
        if self.services and len(self.services) == 1:
            self.service = self.services[0]
        elif self.services:
            self.service = next(
                (service for service in self.services if service.default),
                None,
            )

        if self.service:
            self.default_service_id = self.service.id

        self.logo_url = network_logo(NETWORK_LOGO_FORMAT, network_id=self.id)

        self.description = station_description(self.id)


@dataclass(kw_only=True)
class PlayableNetwork(Network):
    """A more detailed version of `Network` with enough information to play it.

    The `Network` itself is held in the network attribute.

    Parameters
        id: this is the service_id, e.g. bbc_radio_fourfm
        urn: the network's urn, e.g. urn:bbc:radio:network:bbc_radio_four
    """

    type: Literal["network"] = "network"
    id: str
    service_id: str | None = None
    urn: str | None = None
    key: str | None = None
    short_title: str | None = None
    description: str | None = None
    logo_url: str | None = None
    image_url: str | None = None
    duration: str | None = None
    progress: Progress | None = None
    titles: Titles | None = None
    synopses: Synopses | None = None
    release: dict | None = None
    availability: dict | None = None
    stream: str | None = None
    network: Network | None = None

    def post_processing(self, logger: Logger) -> None:

        # Flatten the nested network object
        if self.network:
            self.service_id = copy(self.id)
            self.id = copy(self.network.id)
            for var in vars(self.network):
                if hasattr(self, var) and not getattr(self, var):
                    setattr(self, var, getattr(self.network, var))
            self.network = None

        if self.logo_url:
            self.logo_url = network_logo(self.logo_url)
        if self.image_url:
            self.image_url = image_from_recipe(self.image_url)

        self.description = station_description(self.id)


@dataclass(kw_only=True)
class BasicContainer:
    """Just a bare wrapper for items, e.g. PlayableItemsResponse."""

    sub_items: Sequence[SoundsTypes] | None = None


@dataclass(kw_only=True)
class Container(BaseObject, IdentifiableMixin):
    """Base container for organising content and not directly playable."""

    id: str | None = None
    pid: str | None = None
    title: str | None = None
    description: str | None = None
    image_url: str | None = None
    synopses: Synopses | None = None
    titles: Titles = field(
        default_factory=lambda: Titles(
            primary=None, secondary=None, tertiary=None, entity_title=None
        )
    )
    urn: str | None = None
    network: Network | None = None
    sub_items: Sequence[SoundsTypes] | None = None


@dataclass(kw_only=True)
class ImageContainer(Container):
    IMAGE_SIZE = 1280

    def post_processing(self, logger: Logger) -> None:
        if self.image_url:
            self.image_url = image_from_recipe(
                self.image_url,
                size=self.IMAGE_SIZE,
            )


@dataclass(kw_only=True, slots=True)
class PlayableItem(BaseObject, IdentifiableMixin):
    """Base class for actual playable content.

    Parameters
        id:
        urn:
        pid:
        type:
        duration:
        progress:
        image_url:
        titles:
        synopses:
        network:
        container:
        start:
        end:
        release:
        availability:
        stream:
    """

    id: str
    urn: str | None = None
    pid: str | None = None
    type: str | None = None
    duration: Duration | None = None
    progress: Progress | None = None
    image_url: str | None = None
    titles: Titles = field(
        default_factory=lambda: Titles(
            primary=None, secondary=None, tertiary=None, entity_title=None
        )
    )
    synopses: Synopses | None = None
    network: Network | None = None
    container: Container | None = None
    ancestors: list[Container] | None = None
    categories: list[ItemCategory] | None = None
    start: dt | None = None
    end: dt | None = None
    release: dict | None = None
    availability: dict | None = None
    stream: str | None = None

    def post_processing(self, logger: Logger) -> None:
        self.start = _parse_datetime(self.start)
        self.end = _parse_datetime(self.end)
        if self.urn:
            self.pid = self.urn.rsplit(":", 1)[-1]

        if not self.container and self.ancestors:
            if len(self.ancestors) > 1:
                logger.warning(
                    "%s contains more than one ancestor, so not able to choose: %s",
                    self,
                    self.ancestors,
                )
                return
            self.container = self.ancestors[0]

    def is_live(self, timezone: ZoneInfo | pytz.tzinfo.BaseTzInfo) -> bool:
        if self.start and self.end:
            now = dt.now(tz=timezone)
            return self.start <= now < self.end
        return False

    def has_already_aired(self, timezone: ZoneInfo | pytz.tzinfo.BaseTzInfo) -> bool:
        if self.end:
            return dt.now(tz=timezone) > self.end
        return True


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

    def post_processing(self, logger: Logger) -> None:
        self.start = _parse_datetime(self.start)
        self.end = _parse_datetime(self.end)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.pid})"


@dataclass(kw_only=True)
class ScheduleItem(ImageMixin, PlayableItem):
    """Represents a scheduled program item."""

    # overrides the parent version of Duration
    duration: int | None = None  # type: ignore[assignment]

    def post_processing(self, logger: Logger) -> None:
        super().post_processing(logger)
        self.start = _parse_datetime(self.start)
        self.end = _parse_datetime(self.end)
        self.process_image()


@dataclass(kw_only=True)
class Station(Container, IdentifiableMixin):
    """Represents a radio/media station."""

    id: str
    pid: str | None = None
    default: bool = True  # Whether this is default for its parent Network
    local: bool = False
    international: bool = False
    stream: str | None = None
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

    def post_processing(self, logger: Logger) -> None:
        if self.station_image_url:
            self.station_image_url = network_logo(self.station_image_url)
        if self.episode_image_url:
            self.episode_image_url = image_from_recipe(self.episode_image_url, size=640)


@dataclass(kw_only=True)
class LiveProgramme(PlayableItem, ImageMixin):
    def post_processing(self, logger: Logger) -> None:
        super().post_processing(logger)
        self.process_image()


@dataclass(kw_only=True)
class LiveStation(PlayableItem, IdentifiableMixin, ImageMixin):
    """Represents a radio station which is also playable.

    Attributes:
        local: e.g. True
        schedule: e.g. Schedule()
    """

    id: str
    local: bool = False
    schedule: Schedule | None = None
    description: str | None = None

    def post_processing(self, logger: Logger) -> None:
        super().post_processing(logger)
        self.process_image()
        self.description = station_description(self.pid)


@dataclass(kw_only=True)
class Schedule(Container):
    """Represents a schedule for a given date."""

    id: str
    # title is the date of the schedule
    sub_items: Sequence[ScheduleItem] | None = None

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

    def post_processing(self, logger: Logger) -> None:
        super().post_processing(logger)
        self.process_image()


# Specific content types
@dataclass(kw_only=True)
class RadioClip(PlayableItem, TimedContent, ImageMixin, IdentifiableMixin):
    """Represents a playable radio clip."""

    def post_processing(self, logger: Logger) -> None:
        super().post_processing(logger)
        self.process_image()


@dataclass(kw_only=True)
class PodcastEpisode(PlayableItem, ImageMixin, IdentifiableMixin):
    """Represents a playable podcast episode."""

    def post_processing(self, logger: Logger) -> None:
        super().post_processing(logger)
        self.process_image()


@dataclass(kw_only=True)
class AudiobookEpisode(PodcastEpisode):
    """Represents a playable podcast episode."""

    def post_processing(self, logger: Logger) -> None:
        super().post_processing(logger)
        self.process_image()
        if type(self.container) is not Audiobook:
            self.container = Audiobook(**vars(self.container))


@dataclass(kw_only=True)
class Podcast(ImageContainer):
    """Represents a podcast container (holds episodes)."""


@dataclass(kw_only=True)
class Audiobook(Podcast):
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
    sub_items: Sequence[SoundsTypes] | None = None


@dataclass(kw_only=True)
class Playlist(ImageContainer):
    """Represents a playlist container."""


@dataclass(kw_only=True)
class CollectionItemContainer(CategoryItemContainer):
    """Represents a content collection container."""


@dataclass(kw_only=True)
class MenuItem(ImageContainer):
    """Represents a menu item container."""

    def get(self, key: str) -> SoundsTypes | None:
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

    sub_items: list[MenuItem]

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
