from dataclasses import dataclass, fields
from datetime import datetime as dt
from pprint import pformat
from typing import TYPE_CHECKING, List, Optional

from pytz import BaseTzInfo

from .utils import image_from_recipe

if TYPE_CHECKING:
    from .constants import ContainerType

from dataclasses import dataclass
from datetime import datetime as dt
from typing import Optional, List, Union
from zoneinfo import ZoneInfo


@dataclass(kw_only=True)
class BaseObject:
    """Base class for all objects with common functionality."""

    type: Optional[str] = None

    def __str__(self):
        return pformat(self)


@dataclass(kw_only=True)
class Network:
    """Represents a network/brand with basic metadata."""

    id: str
    key: Optional[str] = None
    short_title: Optional[str] = None
    logo_url: Optional[str] = None
    network_type: str = "master_brand"


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
    sub_items: Optional[List[Union["Container", "PlayableItem"]]] = None


@dataclass(kw_only=True)
class PlayableItem(BaseObject):
    """Base class for actual playable content."""

    id: str
    urn: str
    duration: Optional[int] = None
    progress: Optional[int] = None
    image_url: Optional[str] = None
    titles: Optional[dict] = None
    network: Optional[Network] = None
    container: Optional[Container] = None
    start: Optional[dt] = None
    end: Optional[dt] = None

    @property
    def image(self):
        if self.image_url:
            return image_from_recipe(self.image_url, size=400)
        return None


@dataclass(kw_only=True)
class TimedContent:
    """Mixin for content with timing information."""

    start: dt
    end: dt
    duration: Optional[int] = None

    def is_live(self, timezone: ZoneInfo) -> bool:
        now = dt.now(tz=timezone)
        return self.start <= now < self.end

    def has_already_aired(self, timezone: ZoneInfo) -> bool:
        return dt.now(tz=timezone) > self.end


@dataclass(kw_only=True)
class ScheduleItem(Container, TimedContent):
    """Represents a scheduled program item."""

    short_synopsis: str = ""
    medium_synopsis: str = ""
    long_synopsis: str = ""
    primary_title: str = ""
    secondary_title: str = ""
    tertiary_title: Optional[str] = None
    episode_id: Optional[str] = None
    container_id: Optional[str] = None
    container: Optional[Container] = None
    stream: Optional[str] = None

    @property
    def vpid(self) -> Optional[str]:
        if self.urn:
            return self.urn.rsplit(":", 1)[-1]
        return None

    @property
    def longest_description(self) -> str:
        """Returns the longest available description."""
        return (
            self.long_synopsis
            or self.medium_synopsis
            or self.short_synopsis
            or self.secondary_title
            or self.primary_title
            or ""
        )


@dataclass(kw_only=True)
class Station(Container):
    """Represents a radio/media station."""

    local: bool = False
    stream: Optional["Stream"] = None
    schedule: Optional[List[ScheduleItem]] = None


@dataclass(kw_only=True)
class Stream(TimedContent):
    """Represents a station stream."""

    id: str
    uri: str
    image_url: str
    show_title: str
    show_description: str
    station: Station

    @property
    def can_seek(self) -> bool:
        """Indicates if the stream supports seeking."""
        return False  # Always False for now


@dataclass(kw_only=True)
class Segment:
    """Represents a segment within a stream."""

    id: str
    primary_title: str
    secondary_title: str
    image_url: str
    start_seconds: int
    end_seconds: int
    label: str
    now_playing: bool
    tertiary_title: str = ""
    entity_title: Optional[str] = None

    def __post_init__(self):
        # Set entity_title to primary_title if not provided
        if self.entity_title is None:
            self.entity_title = self.primary_title


@dataclass(kw_only=True)
class Schedule(BaseObject):
    """Represents a schedule for a given date."""

    date: dt
    schedule_list: List[ScheduleItem]

    def get_current_item(self, timezone: ZoneInfo) -> Optional[ScheduleItem]:
        """Get the currently airing schedule item."""
        for item in self.schedule_list:
            if item.is_live(timezone):
                return item
        return None


# Specific content types
@dataclass(kw_only=True)
class RadioShow(PlayableItem, TimedContent):
    """Represents a playable radio show."""

    titles: dict


@dataclass(kw_only=True)
class PodcastEpisode(PlayableItem):
    """Represents a playable podcast episode."""

    pass


@dataclass(kw_only=True)
class RadioSeries(Container):
    """Represents a radio series container (holds episodes)."""

    pass


@dataclass(kw_only=True)
class Podcast(Container):
    """Represents a podcast container (holds episodes)."""

    pass


@dataclass(kw_only=True)
class Collection(Container):
    """Represents a collection container."""

    pass


@dataclass(kw_only=True)
class Category(Container):
    """Represents a content category container."""

    pass


@dataclass(kw_only=True)
class MenuItem(Container):
    """Represents a menu item container."""

    pass


@dataclass(kw_only=True)
class Menu:
    """Represents a menu container with items."""

    sub_items: Optional[list[BaseObject]]

    def get(self, key: str) -> Optional[Union[Container, PlayableItem]]:
        """Get a menu item by ID."""
        if self.sub_items:
            for item in self.sub_items:
                if hasattr(item, "id") and item.id == key:
                    return item
        return None


DisplayItem = PlayableItem
PromoItem = PlayableItem


def model_factory(object):
    from .constants import ContainerType, ItemType, ItemURN

    container_keys = {f.name for f in fields(Container)}
    playable_item_keys = {f.name for f in fields(PlayableItem)}

    object_type = object.get("type")
    urn = object.get("urn").rsplit(":", 1)[0] if object.get("urn") else None

    if object.get("data"):
        init_values = {k: v for k, v in object.items() if k in container_keys}
    else:
        init_values = {k: v for k, v in object.items() if k in playable_item_keys}

    if object_type in ItemType:
        match object_type:
            case ItemType.MODULE.value:
                return MenuItem(**init_values)
            case ItemType.PLAYABLE_ITEM.value:
                match urn:
                    case ItemURN.EPISODE.value:
                        return (
                            RadioShow(**init_values)
                            if object.get("container")
                            and ContainerType(object.get("container").get("type"))
                            == ContainerType.BRAND
                            else PodcastEpisode(**init_values)
                        )
                    case ItemURN.CLIP.value:
                        return RadioShow(**init_values)
                    case ItemURN.COLLECTION.value:
                        return Collection(**init_values)
                    case ItemURN.CATEGORY.value:
                        return Category(**init_values)
                    case ItemURN.SERIES.value:
                        return Podcast(**init_values)
                    case ItemURN.RADIO_SHOW_OR_PODCAST.value:
                        return (
                            PodcastEpisode(**init_values)
                            if object.get("container").get("network").get("id")
                            == "bbc_sounds_podcasts"
                            else RadioShow(**init_values)
                        )
                    case ItemURN.STATION.value:
                        station_keys = {f.name for f in fields(Station)}
                        init_values = {
                            k: v for k, v in object.items() if k in station_keys
                        }
                        return Station(**init_values)
                    case ItemURN.PROMO_ITEM.value:
                        return PromoItem(**init_values)
                    case _:
                        print(f"No playableitem: {object} {type(object)}")
            case ItemType.CONTAINER.value:
                print(object.get("container"))
                return RadioSeries(**init_values)
                # if object.get("")
                # match object.get("container").get("type"):
                #     case ContainerType.BRAND.value:
                #         return RadioShow(**init_values)
                #     case ContainerType.SERIES.value:
                #         return Podcast(**init_values)
                #     case ContainerType.ITEM.value:
                #         pass
                #     case None:
                #     case _:
                #         raise Exception(f"Other containeritem {object}")
            case ItemType.DISPLAY_ITEM.value:
                return DisplayItem(**init_values)
            case ItemType.BROADCAST_SUMMARY.value:
                return ScheduleItem(**init_values)
            case _:
                print("No IT found")

    else:
        print("Not in IT")
    return object
