from dataclasses import dataclass, fields
from datetime import datetime as dt
from pprint import pformat
from typing import TYPE_CHECKING, Any, List, Optional, Sequence
from zoneinfo import ZoneInfo

import pytz

from . import models
from .constants import BaseSoundsTypes
from .utils import image_from_recipe, network_logo

if TYPE_CHECKING:
    from .constants import PlayableSoundsTypes


type SoundsTypes = (
    models.Category
    | models.Collection
    | models.LiveStation
    | models.MenuItem
    | models.Podcast
    | models.PodcastEpisode
    | models.RadioClip
    | models.RadioSeries
    | models.RadioShow
    | models.RecommendedMenuItem
    | models.Schedule
    | models.ScheduleItem
    | models.Station
    | models.StationSearchResult
)

def _parse_datetime(value):
    return dt.fromisoformat(value) if isinstance(value, str) else value

@dataclass(kw_only=True)
class BaseObject:
    """Base class for all objects with common functionality."""

    type: Optional[str] = None
    uris: Optional[dict] = None
    recommendation: Optional[dict] = None

    def __str__(self):
        return pformat(self)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.id})"


@dataclass(kw_only=True)
class Network:
    """Represents a network/brand with basic metadata."""

    id: str
    key: Optional[str] = None
    short_title: Optional[str] = None
    logo_url: Optional[str] = None
    current_programme: Optional["LiveProgramme"] = None
    sort: Optional[int] = None
    group: Optional[str] = None
    contacts: Optional[dict] = None
    services: Optional[dict] = None
    promoted_category_summaries: Optional[dict] = None
    active: Optional[bool] = None
    international: Optional[bool] = None

    def __post_init__(self):
        if self.logo_url:
            self.logo_url = network_logo(self.logo_url)

    def __str__(self):
        return pformat(self)

    def __repr__(self):
        # klass = str(type(self)).rsplit(".", 1)[-1].replace("'>", "")
        return f"{type(self).__name__}({self.id})"


@dataclass(kw_only=True)
class Container(BaseObject):
    """Base container for organizing content - not directly playable."""

    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    synopses: Optional[dict] = None
    titles: Optional[dict] = None
    urn: Optional[str] = None
    network: Optional[Network] = None
    sub_items: Optional[List[SoundsTypes]] = None

    @property
    def item_id(self):
        if self.urn is not None:
            return self.urn.rsplit(":", 1)[1]
        else:
            return self.id


@dataclass(kw_only=True)
class PlayableItem(BaseObject):
    """Base class for actual playable content."""

    id: str
    urn: Optional[str] = None
    pid: Optional[str] = None
    type: Optional[str] = None
    duration: Optional[dict] = None
    progress: Optional[dict] = None
    image_url: Optional[str] = None
    titles: Optional[dict] = None
    synopses: Optional[dict] = None
    network: Optional[Network] = None
    container: Optional[Container] = None
    start: Optional[dt] = None
    end: Optional[dt] = None
    release: Optional[dict] = None
    availability: Optional[dict] = None
    stream: Optional[str] = None

    def __repr__(self):
        return f"{self.__class__.__name__}({self.id})"

    def __post_init__(self):
        self.start = _parse_datetime(self.start)
        self.end = _parse_datetime(self.end)
       

    @property
    def item_id(self):
        if self.urn is not None:
            return self.urn.rsplit(":", 1)[1]
        else:
            return self.pid
  

@dataclass(kw_only=True)
class TimedContent:
    """Mixin for content with timing information."""

    def is_live(self, timezone: ZoneInfo | pytz.tzinfo.BaseTzInfo) -> bool:
        now = dt.now(tz=timezone)
        return self.start <= now < self.end # type: ignore

    def has_already_aired(self, timezone: ZoneInfo | pytz.tzinfo.BaseTzInfo ) -> bool:
        return dt.now(tz=timezone) > self.end # type: ignore


@dataclass(kw_only=True)
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
    programme: "RadioShow"

    def __post_init__(self):
        self.start = _parse_datetime(self.start)
        self.end = _parse_datetime(self.end)

    def __str__(self):
        return pformat(self)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.pid})"


@dataclass(kw_only=True)
class ScheduleItem(PlayableItem):
    """Represents a scheduled program item."""

    container: Optional[Container] = None
    stream: Optional[str] = None

    def __post_init__(self):
        if self.image_url:
            self.image_url = image_from_recipe(self.image_url, size=640)
        if hasattr(self, "urn") and self.urn is not None:
            self.pid = self.urn.rsplit(":", 1)[-1]
        self.start = _parse_datetime(self.start)
        self.end = _parse_datetime(self.end)


    def is_live(self, timezone: ZoneInfo | pytz.tzinfo.BaseTzInfo) -> bool:
        if self.start and self.end:
            now = dt.now(tz=timezone)
            return self.start <= now < self.end
        return False

    def has_already_aired(self, timezone: ZoneInfo | pytz.tzinfo.BaseTzInfo ) -> bool:
        if self.end:
            return dt.now(tz=timezone) > self.end
        return True


@dataclass(kw_only=True)
class Station(Container):
    """Represents a radio/media station."""

    local: bool = False
    stream: Optional["Stream"] = None
    schedule: Optional["Schedule"] = None


@dataclass(kw_only=True)
class StationSearchResult:
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

    @property
    def item_id(self):
        if self.urn is not None:
            return self.urn.rsplit(":", 1)[1]
        else:
            return self.id

@dataclass(kw_only=True)
class LiveProgramme(PlayableItem):

    def __post_init__(self):
        if self.image_url:
            self.image_url = image_from_recipe(self.image_url, size=640)


@dataclass(kw_only=True)
class LiveStation(PlayableItem):
    local: bool = False
    schedule: Optional["Schedule"] = None

    def __post_init__(self):
        if self.image_url:
            self.image_url = image_from_recipe(self.image_url, size=640)
       

    @property
    def item_id(self):
        if self.urn is not None:
            return self.urn.rsplit(":", 1)[1]
        else:
            return self.pid


@dataclass(kw_only=True)
class Stream(TimedContent):
    """Represents a station stream."""

    id: str
    uri: str
    image_url: str | None
    show_title: str
    show_description: str
    container: Any | None = None

    def __post_init__(self):
        if self.image_url:
            self.image_url = network_logo(self.image_url)

    @property
    def can_seek(self) -> bool:
        """Indicates if the stream supports seeking."""
        return False  # Always False for now



@dataclass(kw_only=True)
class Segment:
    """Represents a segment within a stream."""

    id: str
    segment_type: str
    titles: dict
    image_url: str | None
    offset: dict

    def __post_init__(self):
        if self.image_url:
            self.image_url = image_from_recipe(self.image_url, size=1280)


@dataclass(kw_only=True)
class Schedule(Container):
    """Represents a schedule for a given date."""

    id: str
    # title is the date of the schedule
    # sub_items: Optional[List[ScheduleItem]] = None

    def get_current_item(
        self,
        timezone: ZoneInfo | pytz.tzinfo.BaseTzInfo = pytz.timezone("UTC"),
    ) -> Optional[ScheduleItem]:
        """Get the currently airing schedule item."""
        if self.sub_items and isinstance(self.sub_items, list):
            for item in self.sub_items:
                if isinstance(item, ScheduleItem):
                    if item.is_live(timezone):
                        return item
        return None


# Specific content types
@dataclass(kw_only=True)
class RadioShow(PlayableItem, TimedContent):
    """Represents a playable radio show."""

    def __post_init__(self):
        super().__post_init__()
        if self.image_url:
            self.image_url = image_from_recipe(self.image_url, size=1280)
        if hasattr(self, "urn") and self.urn is not None:
            self.pid = self.urn.rsplit(":", 1)[-1]

    def __str__(self):
        return pformat(self)
    
    @property
    def item_id(self):
        return self.pid


# Specific content types
@dataclass(kw_only=True)
class RadioClip(PlayableItem, TimedContent):
    """Represents a playable radio clip."""

    def __post_init__(self):
        if self.image_url:
            self.image_url = image_from_recipe(self.image_url, size=1280)
        if hasattr(self, "urn") and self.urn is not None:
            self.pid = self.urn.rsplit(":", 1)[-1]


@dataclass(kw_only=True)
class PodcastEpisode(PlayableItem):
    """Represents a playable podcast episode."""

    def __post_init__(self):
        if self.image_url:
            self.image_url = image_from_recipe(self.image_url, size=1280)
        if hasattr(self, "urn") and self.urn is not None:
            self.pid = self.urn.rsplit(":", 1)[-1]


@dataclass(kw_only=True)
class Podcast(Container):
    """Represents a podcast container (holds episodes)."""

    def __post_init__(self):
        if self.image_url:
            self.image_url = image_from_recipe(self.image_url, size=1280)

    def __str__(self):
        return pformat(self)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.id})"


@dataclass(kw_only=True)
class RadioSeries(Podcast):
    """Represents a radio series container (holds episodes)."""

    def __post_init__(self):
        if self.image_url:
            self.image_url = image_from_recipe(self.image_url, size=1280)

    def __str__(self):
        return pformat(self)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.id})"


@dataclass(kw_only=True)
class Collection(Container):
    """Represents a collection container."""

    def __post_init__(self):
        if self.image_url:
            self.image_url = image_from_recipe(self.image_url, size=1280)


@dataclass(kw_only=True)
class Category(Container):
    """Represents a content category."""

    def __post_init__(self):
        if self.image_url:
            self.image_url = image_from_recipe(self.image_url, size=1280)


@dataclass(kw_only=True)
class CategoryItemContainer:
    """Represents a content category container."""

    id: Optional[str] = None
    total: int
    limit: int
    offset: int
    sub_items: Optional[List[SoundsTypes]] = None


@dataclass(kw_only=True)
class CollectionItemContainer(CategoryItemContainer):
    """Represents a content collection container."""


@dataclass(kw_only=True)
class MenuItem(Container):
    """Represents a menu item container."""

    pass


@dataclass(kw_only=True)
class RecommendedMenuItem(MenuItem):
    """Represents a recommended menu item."""

    pass


@dataclass(kw_only=True)
class Menu:
    """Represents a menu container with items."""

    sub_items: List[MenuItem] | Sequence[MenuItem] | None

    def get(self, key: str) -> Optional[MenuItem | RecommendedMenuItem]:
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
class SearchResults:
    stations: List[LiveStation]
    shows: List[Podcast | RadioShow]
    episodes: List[PodcastEpisode | RadioClip | RadioShow]


def model_factory(object):
    from .constants import ContainerType, ItemType, ItemURN, IDType

    schema_type = None
    new_type = None

    if "$schema" in object:
        schema_type = object["$schema"].rsplit("/", 1)[1]

    object_type = object.get("type", None)
    if object_type is None:
        object_type = schema_type
    urn = object.get("urn").rsplit(":", 1)[0] if object.get("urn") else None

    if object_type in ItemType:
        match object_type:
            case ItemType.INLINE_DISPLAY_MODULE.value:
                # Menu item, container or schedule
                if object["id"] == IDType.SCHEDULE_ITEMS.value:
                    # This is a container of schedule items
                    new_type = Schedule
                elif "container" in object.get("id"):
                    new_type = Container
                elif object["id"] == IDType.SINGLE_ITEM_PROMO.value:
                    # This is the special promo item menu, ignoring for now
                    pass
                else:
                    new_type = MenuItem
            case ItemType.PLAYABLE_ITEM.value:
                match urn:
                    case ItemURN.EPISODE.value:
                        if (
                            object.get("container")
                            and ContainerType(object.get("container").get("type"))
                            == ContainerType.BRAND
                            and object.get("network").get("id") != "bbc_sounds_podcasts"
                        ) or not object.get("container"):
                            new_type = RadioShow
                        else:
                            new_type = PodcastEpisode
                    case ItemURN.CLIP.value:
                        # Sometimes these can appear in podcast episodes listings
                        if (
                            object.get("container")
                            and ContainerType(object.get("container").get("type"))
                            == ContainerType.BRAND
                        ):
                            new_type = PodcastEpisode
                        else:
                            new_type = RadioClip
                    case ItemURN.COLLECTION.value:
                        new_type = Collection
                    case ItemURN.CATEGORY.value:
                        new_type = Category
                    case ItemURN.SERIES.value:
                        new_type = Podcast
                    case ItemURN.RADIO_SHOW_OR_PODCAST.value:
                        new_type = RadioShow
                    case ItemURN.STATION.value:
                        if object.get("synopses") is not None:
                            new_type = LiveStation
                        else:
                            new_type = Station
                    case ItemURN.PROMO_ITEM.value:
                        new_type = PromoItem
                    case _:
                        print(f"No playableitem: {object} {type(object)}")
            case ItemType.INLINE_HEADER_MODULE.value:
                new_type = Podcast
            case ItemType.DISPLAY_ITEM.value:
                new_type = DisplayItem
                # new_type = object.item
            case ItemType.BROADCAST_SUMMARY.value | ItemType.BROADCAST.value:
                if urn == ItemURN.STATION:
                    new_type = Station
                if (
                    object.get("progress") and object.get("progress").get("value") == 0
                ) or object.get("on_air"):
                    # Live, or not yet aired
                    new_type = ScheduleItem
                elif object["playable_item"] is not None:
                    new_type = RadioShow
                elif hasattr(object, "live"):
                    new_type = Broadcast
                else:
                    new_type = ScheduleItem
            case ItemType.EPISODE.value:
                new_type = RadioShow
            case ItemType.BROADCAST.value:
                raise Exception("Broadcast?")
            case ItemType.RADIO_SEARCH.value:
                new_type = StationSearchResult
                # Search results embed the actual station details in a now key
                object = object["now"]
            case ItemType.SEGMENT_ITEM.value:
                new_type = Segment
            case _:
                print("No IT found")
    elif object_type in ContainerType or object_type in BaseSoundsTypes:
        # This is a nested/parent container, work out which
        if urn == ItemURN.COLLECTION.value:
            new_type = Collection
        elif urn == ItemURN.CATEGORY.value:
            new_type = Category
        elif object_type == ContainerType.BRAND.value:
            new_type = RadioSeries
            if (
                hasattr(object, "network")
                and object.get("network").get("id") == "bbc_sounds_podcasts"
                or "brand" in object.get("urn")
            ):
                new_type = Podcast
            else:
                # This is a radio show
                new_type = RadioSeries
        elif object_type == BaseSoundsTypes.PLAYABLE_ITEMS.value:
            # Category of items
            new_type = CategoryItemContainer
        elif object_type == BaseSoundsTypes.CONTAINER_ITEMS.value:
            # Collection group of items
            new_type = CollectionItemContainer
        elif object_type == BaseSoundsTypes.PROGRAMMES.value:
            if object["total"] > 1:
                raise NotImplementedError("Container has more than 1 programme!")
            new_type = PodcastEpisode
        # elif object["id"] == IDType.SHOW_SEARCH_CONTAINER.value:
        #     new_type = Container
        elif object_type == ContainerType.SERIES.value:
            new_type = RadioSeries
        elif urn == ItemURN.RADIO_SHOW_OR_PODCAST.value:
            new_type = RadioSeries
        elif object_type == ContainerType.ITEM.value:
            # Default to podcast
            new_type = Podcast
        else:
            print(f"Unknown container type: {object_type}")
            print(object)
    elif object.get("network_type", None) is not None:
        # This is a station or network
        if object.get("network_type") == "master_brand":
            new_type = Network
        elif object.get("network_type") == "service":
            # Local station, treat the same at present
            new_type = Network
        else:
            raise Exception(f"Other network type: {object_type} {object}")
    elif "key" in object:
        # This is a weird nested network thing
        new_type = Network
    elif schema_type in PlayableSoundsTypes:
        print(schema_type)
        return None
    else:
        print(f"Not in IT {object} {object_type} {schema_type}")
        return None

    try:
        required_fields = {f.name for f in fields(new_type)}
    except TypeError:
        return None
    attrs = {k: v for k, v in object.items() if k in required_fields}

    new_object = new_type(**attrs)
    return new_object
