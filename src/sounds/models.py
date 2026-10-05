from collections.abc import Mapping, Sequence
from copy import copy
from dataclasses import dataclass, field
from datetime import datetime as dt
from logging import Logger
from typing import Annotated, Any, ClassVar, Final, Literal
from urllib.parse import parse_qs, urlparse
from warnings import deprecated
from zoneinfo import ZoneInfo

import mashumaro
import pytz
from mashumaro.types import Discriminator

from sounds.utils import image_from_recipe, network_logo

NETWORK_LOGO_FORMAT = "https://sounds.files.bbci.co.uk/3.12.0/networks/{network_id}/{type}_{size}.{format}"

from datetime import UTC


###### Helpers ##################################################################
def _parse_datetime(value):
    return dt.fromisoformat(value) if isinstance(value, str) else value


def station_description(station_id, is_local: bool = False):
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
        "bbc_afrique_radio": "Infos, musique et sports",
        "bbc_arabic_radio": "خدمة إخبارية على مدار الساعة و برامج حوارية وتفاعلية تناقش قضايا المنطقة والعالم وباقة من البرامج المنوعة من إذاعة بي بي سي",
        "bbc_burmese_radio": "",
        "bbc_dari_radio": "بی بی سی برای افغانستان تازه ترین و دقیق ترین خبرهای افغانستان ، منطقه و جهان را با تحلیل های همه جانبه ارایه می کند",
        "bbc_hindi_radio": "",
        "bbc_gahuza_radio": "Amakuru y’amahanga, ubusesenguzi, amakuru y’akarere k’ibiyaga bigari, ikinamico, ubuzima, imibereho y’abagore",
        "bbc_hausa_radio": "Labaran duniya da sharhi da kuma bayanai kan al'amuran yau da kullum daga sashin Hausa na BBC.",
        "bbc_nepali_radio": "नेपाली भाषामा बीबीसी विश्व सेवाको राष्ट्रिय तथा अन्तर्राष्ट्रिय समाचार तथा समसामयिक चर्चा, राष्ट्रिय तथा अन्तर्राष्ट्रिय समाचार विश्लेषण, समाचारमा रहेका व्यक्तित्वहरुसंगको अन्तर्वार्ता, साप्ताहिक बहस तथा छलफल, विज्ञान, स्वास्थ्य.",
        "bbc_pashto_radio": "بي بي سي د افغانستان لپاره کورني، سیمه ییز او نړیوال وروستي او کره خبرونه د هر اړخېزو څېړونو او شننو سره تاسې ته وړاندې کوي",
        "bbc_uzbek_radio": "O’zbekiston, mintaqa va dunyo yangiliklari O’zbek tilida",
        "bbc_somali_radio": "Wararka iyo xaaladda taagan ee dunida oo dhan, faallo, muusig, madadaallo iyo cayaaro.",
        "bbc_swahili_radio": "Habari za kimataifa, michezo na uchambuzi kutoka kwa idhaa ya dunia.",
    }
    return (
        descriptions_dict.get("local")
        if is_local
        else descriptions_dict.get(station_id, None)
    )


###### Serialisation ###########################################################
MODEL_TAG: Final = "_model"
"""Key to identify the concrete class.

Without this, base types would de-serialise to accepted, but not neccessarily 
the correct class.
"""

# Fields which can be polymorphic get this to keep their concrete type."""

_POLYMORPHIC = Discriminator(
    field=MODEL_TAG,
    include_supertypes=True,
    include_subtypes=True,
    variant_tagger_fn=lambda cls: cls.__name__,
)


###### Mixins ##################################################################
class SerializableMixin(mashumaro.DataClassDictMixin):
    def __post_serialize__(self, d: dict[Any, Any]) -> dict[Any, Any]:
        d[MODEL_TAG] = type(self).__name__
        return d


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

    def is_live(self) -> bool:
        return self.start <= dt.now(tz=UTC) < self.end  # type: ignore

    def has_already_aired(self) -> bool:
        return dt.now(tz=UTC) > self.end  # type: ignore


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
    type: str


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

    # Unique ID
    id: str
    # Song identifier, identical each time
    segment_type: str
    uris: list[URI]
    urn: str | None = None
    titles: Titles = field(
        default_factory=lambda: Titles(
            primary=None, secondary=None, tertiary=None, entity_title=None
        )
    )
    image_url: str | None
    offset: dict | None

    @property
    def record_id(self):
        if self.urn:
            return self.urn.rsplit(":", 1)[-1]
        return None

    def music_service_uri(self, platform: Literal["spotify", "apple"]):
        service_found = next(
            (
                uri
                for uri in self.uris
                if uri.id == f"commercial-music-service-{platform}"
            ),
            None,
        )
        if service_found:
            return service_found.uri
        return None

    @property
    def spotify_url(self):
        return self.music_service_uri("spotify")

    @property
    def apple_music_url(self):
        return self.music_service_uri("apple")


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
    title: str | None = None
    pid: str | None = None
    short_title: str
    type: str
    region: str | None = None
    coverage: Literal["local", "regional", "national"] = "national"
    active: str | None = None
    # present in NETWORKS_DETAILED
    date_ranges: list[dict[str, Any]] = field(default_factory=list)
    default_language: Literal["en", "gd", "ga", "cy"] = "en"
    default: bool | None = None


@dataclass(kw_only=True)
class URI(SerializableMixin):
    type: str
    uri: str
    id: str | None = None
    label: str | None = None

    def query_param(self, name: str) -> str | None:
        return parse_qs(urlparse(self.uri).query).get(name, [None])[0]


@dataclass(kw_only=True)
class Release(SerializableMixin):
    date: str
    label: str


@dataclass(kw_only=True)
class URN(SerializableMixin):
    urn: str


###### Base types ##############################################################
@dataclass(kw_only=True)
class BaseObject(SerializableMixin):
    """Base class for all objects with common functionality."""

    # Sounds key -> library key mapping
    API_FIELD_MAP: ClassVar[Mapping[str, str]] = {}

    type: str | None = None
    # List of URIs e.g. [{"type":"latest"...}] or the pagination and polling
    # URLs, e.g. {"pagination": ..., "polling": ...}
    uris: list[URI] | dict[str, Any] | None = field(default_factory=list)
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
    services: list[Station] | None = None
    service: Station | None = None
    default_service_id: str | None = None
    active: bool = True
    coverage: Literal["national", "regional", "local"] | None = None
    international: bool = True
    promoted_category_summaries: list[dict[str, Any]] = field(default_factory=list)
    date_ranges: list[dict[str, Any]] = field(default_factory=list)
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

        self.description = station_description(self.id)
        if self.service:
            self.default_service_id = self.service.id
            self.service.description = self.description

        self.logo_url = network_logo(
            self.logo_url or NETWORK_LOGO_FORMAT, network_id=self.id
        )


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
    network: Annotated[Network, _POLYMORPHIC] | None = None

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
class BasicContainer(IdentifiableMixin):
    """Just a bare wrapper for items, e.g. PlayableItemsResponse."""

    series_pid: str | None = None
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
    network: Annotated[Network, _POLYMORPHIC] | None = None
    sub_items: Sequence[Annotated[SoundsTypes, _POLYMORPHIC]] | None = None


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
    version_pid: str | None = None
    series_pid: str | None = None
    type: str | None = None
    # Duration object normally; plain seconds on broadcast summaries
    duration: Duration | int | None = None
    progress: Progress | None = None
    image_url: str | None = None
    titles: Titles = field(
        default_factory=lambda: Titles(
            primary=None, secondary=None, tertiary=None, entity_title=None
        )
    )
    synopses: Synopses | None = None
    network: Annotated[Network, _POLYMORPHIC] | None = None
    container: Annotated[Container, _POLYMORPHIC] | None = None
    ancestors: list[Annotated[Container, _POLYMORPHIC]] | None = None
    categories: list[ItemCategory] | None = None
    start: dt | None = None
    end: dt | None = None
    release: dict | None = None
    availability: dict | None = None
    # Only on PROGRAMME_FROM_PID, in place of image_url
    images: list[dict] | None = None
    stream: str | None = None

    @property
    def is_promo(self):
        promo_keywords = [
            "coming soon",
            "coming up",
            "is back",
            "returns",
            "new series",
            "new episodes",
            "stand by",
        ]
        # Title is exactly Trailer, or contains a promo word and is <5 mins
        return self.titles.entity_title == "Trailer" or (
            self.titles.entity_title is not None
            and any(keyword in self.titles.entity_title for keyword in promo_keywords)
            and (
                (type(self.duration) is int and self.duration < (5 * 60))
                or (type(self.duration) is Duration and self.duration.value < (5 * 60))
            )
        )

    def post_processing(self, logger: Logger) -> None:
        # Subclasses run process_image() after this, which fills in the recipe
        if not self.image_url and self.images:
            standard = next(
                (i for i in self.images if i.get("type") == "standard"), self.images[0]
            )
            self.image_url = standard.get("url")

        # Set dates
        self.start = _parse_datetime(self.start)
        self.end = _parse_datetime(self.end)

        # Get PID from URN
        if self.urn:
            self.pid = self.urn.rsplit(":", 1)[-1]

        if not self.container and self.ancestors:
            # ancestors run top-down (brand, then series). The container is
            # always the brand so its identity doesn't depend on the endpoint
            # the item came from; the series is tracked in series_pid.
            self.container = next(
                (a for a in self.ancestors if a.type == "brand"),
                self.ancestors[0],
            )

        series = next((a for a in self.ancestors or [] if a.type == "series"), None)
        series_pid = None
        # broadcasts / by-pid items
        if series:
            series_pid = series.id
        # playable-endpoint items
        elif isinstance(self.uris, list):
            latest = next((u for u in self.uris if u.type == "latest"), None)
            series_pid = latest.query_param("container") if latest else None
        # A series that is also the container is a flat brand
        if series_pid and series_pid != getattr(self.container, "id", None):
            self.series_pid = series_pid

        # Derive VPID
        if not self.version_pid:
            if self.availability and self.availability.get("id"):
                self.version_pid = self.availability["id"]
            elif self.pid and self.id != self.pid:
                self.version_pid = self.id

        # Programmes responses (e.g. get_by_pid) only give the length under availability
        if (
            self.duration is None
            and self.availability
            and (seconds := self.availability.get("duration")) is not None
        ):
            self.duration = Duration(label=f"{seconds // 60} mins", value=seconds)

    @property
    def is_live(self) -> bool:
        if self.start and self.end:
            return self.start <= dt.now(tz=UTC) < self.end
        return False

    def has_already_aired(self, timezone: ZoneInfo | pytz.tzinfo.BaseTzInfo) -> bool:
        if self.end:
            return dt.now(tz=UTC) > self.end
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
    description: str | None = None

    def post_processing(self, logger: Logger) -> None:
        self.description = station_description(self.pid, self.local)


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
    progress: Progress | None
    duration: Duration | None

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
        self.description = station_description(self.pid, self.local)


@dataclass(kw_only=True)
class Schedule(Container):
    """Represents a schedule for a given date."""

    id: str
    # title is the date of the schedule
    sub_items: Sequence[Annotated[ScheduleItem | RadioShow, _POLYMORPHIC]] | None = None

    def get_current_item(self) -> ScheduleItem | None:
        """Get the currently airing schedule item."""
        return next(
            (
                item
                for item in self.sub_items or ()
                if isinstance(item, ScheduleItem) and item.is_live
            ),
            None,
        )


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

    @property
    def item_id(self):
        return self.pid

    def post_processing(self, logger: Logger) -> None:
        super().post_processing(logger)
        self.process_image()


# Not a PodcastEpisode subclass: consumers dispatch on isinstance and check
# PodcastEpisode before RadioShow.
@dataclass(kw_only=True)
class RadioShow(PlayableItem, ImageMixin, IdentifiableMixin):
    """Represents a playable radio show."""

    service_id: str | None = None
    version_pid: str | None = None

    @property
    def item_id(self):
        return self.pid

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

    seasons: list[Season] | None = None


@dataclass(kw_only=True)
class Audiobook(Podcast):
    """Represents a podcast container (holds episodes)."""


@dataclass(kw_only=True)
class RadioSeries(Podcast):
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
    sub_items: Sequence[Annotated[SoundsTypes, _POLYMORPHIC]] | None = None


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

    sub_items: list[Annotated[MenuItem, _POLYMORPHIC]]

    def get(self, key: str) -> MenuItem | RecommendedMenuItem | None:
        """Get a menu item by ID."""
        if self.sub_items:
            for item in self.sub_items:
                if hasattr(item, "id") and item.id == key:
                    return item
        return None


@dataclass(kw_only=True)
class DisplayItem(Container):
    item: Annotated[PlayableItem, _POLYMORPHIC] | None = None


@dataclass(kw_only=True)
class PromoItem(Container):
    item: Annotated[PlayableItem, _POLYMORPHIC]


@dataclass(kw_only=True)
class SearchResults(SerializableMixin):
    stations: list[Annotated[LiveStation | StationSearchResult, _POLYMORPHIC]]
    shows: list[Annotated[Podcast | RadioShow, _POLYMORPHIC]]
    episodes: list[Annotated[PodcastEpisode | RadioClip | RadioShow, _POLYMORPHIC]]


@dataclass(kw_only=True)
class Header(BaseObject):
    pass


@dataclass(kw_only=True)
class Season(ImageContainer):
    API_FIELD_MAP: ClassVar[Mapping[str, str]] = {"tlec_urn": "brand_urn"}
    brand_urn: str | None = None
    sub_items: Sequence[Annotated[EpisodeTypes, _POLYMORPHIC]] | None = None


EpisodeTypes = PodcastEpisode | RadioShow | RadioClip

type SoundsTypes = (
    AudiobookEpisode
    | Audiobook
    | CategoryItemContainer
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
    | Season
    | Segment
    | Schedule
    | ScheduleItem
    | Station
    | StationSearchResult
)
"""Types we expect to find within other SoundsTypes."""
type NestedSoundsTypes = ItemCategory | Titles | Synopses | Duration | Progress
