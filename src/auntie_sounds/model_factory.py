import dataclasses
import logging
from dataclasses import fields
from enum import StrEnum, auto, unique
from typing import Any, ClassVar, Final, NamedTuple

from auntie_sounds.exceptions import ParserError
from auntie_sounds.models import (
    URI,
    URN,
    AudiobookEpisode,
    BasicContainer,
    Category,
    CategoryItemContainer,
    Collection,
    CollectionItemContainer,
    Container,
    Duration,
    Header,
    ItemCategory,
    LiveStation,
    MenuItem,
    Network,
    Playlist,
    Podcast,
    PodcastEpisode,
    Progress,
    PromoItem,
    RadioClip,
    RadioSeries,
    RadioShow,
    Schedule,
    ScheduleItem,
    Segment,
    SoundsTypes,
    Station,
    StationSearchResult,
    Synopses,
    Titles,
)

logger = logging.getLogger(__name__)


class NestedObject(NamedTuple):
    source_key: str
    replacement_model: type[Any]
    concrete_class: bool = True
    # Leave dicts alone for this key
    list_only: bool = False


NESTED_OBJECTS: Final[tuple[NestedObject, ...]] = (
    NestedObject("network", Network),
    NestedObject("container", Container, False),
    NestedObject("titles", Titles),
    NestedObject("progress", Progress),
    NestedObject("duration", Duration),
    NestedObject("synopses", Synopses),
    NestedObject("services", Station),
    NestedObject("ancestors", Container, False),
    NestedObject("categories", ItemCategory),
    NestedObject("uris", URI, list_only=True),
    NestedObject("urn", URN),
)


def _api_field_map(new_type: type) -> dict[str, str]:
    """Process the Sounds->library key mapping defined on the model."""
    merged: dict[str, str] = {}
    for cls in reversed(new_type.__mro__):
        merged.update(cls.__dict__.get("API_FIELD_MAP", {}))
    return merged


# Set by OwnerService on brand and series entries: whether the network that
# owns them is a radio station, i.e. has a live service of its own
STATION_OWNED: Final = "station_owned"

# Only used for entries OwnerService hasn't marked: when the station list
# couldn't be fetched, or a response is parsed without a client
PODCAST_NETWORKS: Final = frozenset({"bbc_sounds_podcasts", "bbc_news"})


def _network_id(network: dict | SoundsTypes | None) -> str | None:
    if isinstance(network, Network):
        return network.id
    if isinstance(network, dict):
        return network.get("id")
    return None


def _podcast_or_series(
    original_object: dict,
    urn: str | None,
    parent_network: dict | SoundsTypes | None = None,
) -> type:
    """A brand or series owned by a radio station is a RadioSeries. Anything
    else is a Podcast."""
    if STATION_OWNED in original_object:
        return RadioSeries if original_object[STATION_OWNED] else Podcast
    # Unmarked, so fall back to the fixed set. A container's own network is its
    # owner, while one nested in an episode has none and uses the episode's,
    # the same as the episode does.
    network_id = _network_id(original_object.get("network")) or _network_id(
        parent_network
    )
    if network_id in PODCAST_NETWORKS or (
        not network_id and urn == ItemURN.RADIO_SHOW_OR_PODCAST
    ):
        return Podcast
    return RadioSeries


def _in_a_podcast(
    original_object: dict, parent_network: dict | SoundsTypes | None = None
) -> bool:
    """Whether an episode or clip belongs to a Podcast rather than a RadioSeries.

    It's decided by its top-level container, so the item and its container
    always agree. /playable responses have that as the container, /programmes
    ones only have ancestors, which run top-down.
    """
    top_level = original_object.get("container") or next(
        iter(original_object.get("ancestors") or []), None
    )
    if isinstance(top_level, dict) and STATION_OWNED in top_level:
        return not top_level[STATION_OWNED]
    # Unmarked, so fall back to the container's network, then a parent passed
    # down, and only then the network the item went out on
    owner = (
        (_network_id(top_level.get("network")) if isinstance(top_level, dict) else None)
        or _network_id(parent_network)
        or _network_id(original_object.get("network"))
    )
    return owner in PODCAST_NETWORKS


def _is_audiobook_episode(original_object):
    if original_object.get("categories") and len(original_object.get("categories")) > 0:
        return next(
            (c for c in original_object.get("categories") if c["id"] == "audiobooks"),
            False,
        )
    return False


def _episode_or_show_or_audiobook_episode(
    original_object: dict, parent_network: dict | SoundsTypes | None = None
) -> type:
    if _is_audiobook_episode(original_object):
        return AudiobookEpisode
    return (
        PodcastEpisode if _in_a_podcast(original_object, parent_network) else RadioShow
    )


def _clip_or_episode(
    original_object: dict, parent_network: dict | SoundsTypes | None = None
) -> type:
    # Clips in a podcast's listing are its episodes. Elsewhere they stay clips.
    if original_object.get("container") and _in_a_podcast(
        original_object, parent_network
    ):
        return PodcastEpisode
    return RadioClip


def _live_station_or_station(original_object) -> type:
    return LiveStation if original_object.get("synopses") is not None else Station


@unique
class BaseSoundsTypes(StrEnum):
    """Types as defined in the JSON schema"""

    PROGRAMMES = "Programmes"
    EXPERIENCE_RESPONSE = "ExperienceResponse"
    ERROR = "ErrorResponse"
    SEGMENTS = "SegmentItemsResponse"
    CONTAINER_ITEMS = "ContainerItems"
    PLAYABLE_ITEMS = "PlayableItems"
    PLAYABLE_ITEMS_RESPONSE = "PlayableItemsResponse"
    NETWORKS_RESPONSE = "NetworksResponse"
    CONTAINER_ITEMS_PAGINATED_RESPONSE = "ContainerItemsPaginatedResponse"


@unique
class PlayableSoundsTypes(StrEnum):
    """Types as defined in the JSON schema"""

    EPISODE = "Episode"
    PROGRAMMES = "Programmes"
    EXPERIENCE_RESPONSE = "ExperienceResponse"
    PLAYABLE_ITEM = "PlayableItem"
    BROADCASTS = "BroadcastsResponse"


@unique
class ItemURN(StrEnum):
    EPISODE = "urn:bbc:radio:episode"
    CLIP = "urn:bbc:radio:clip"
    COLLECTION = "urn:bbc:radio:collection"
    CATEGORY = "urn:bbc:radio:category"
    SERIES = "urn:bbc:radio:series"
    RADIO_SHOW_OR_PODCAST = "urn:bbc:radio:brand"
    NETWORK = "urn:bbc:radio:network"
    PROMO_ITEM = "urn:bbc:radio:content:single_item_promo"
    SEGMENT_ITEM = "urn:bbc:radio:segment:music"
    PLAYLIST = "urn:bbc:radio:curation"


@unique
class ItemType(StrEnum):
    PLAYABLE_ITEM = auto()
    DISPLAY_ITEM = auto()
    BROADCAST_SUMMARY = auto()
    INLINE_DISPLAY_MODULE = auto()
    INLINE_HEADER_MODULE = auto()
    EPISODE = auto()
    BROADCAST = auto()
    RADIO_SEARCH = "live_search_result_item"
    SEGMENT_ITEM = auto()


@unique
class ContainerType(StrEnum):
    BRAND = "brand"
    SERIES = "series"
    ITEM = "container_item"


@unique
class NetworkType(StrEnum):
    MASTER = "master_brand"


@unique
class IDType(StrEnum):
    SCHEDULE_ITEMS = "schedule_items"
    SINGLE_ITEM_PROMO = "single_item_promo"
    STATION_SEARCH_CONTAINER = "live_search"
    SHOW_SEARCH_CONTAINER = "container_search"
    EPISODE_SEARCH_CONTAINER = "playable_search"


def _broadcast_as_summary(original_object: dict) -> dict:
    """Make a single broadcast match a broadcast summary format.

    A summary has the broadcast pid in `id` and the episode's details at the
    top level. A single /v2/broadcasts/{pid} response has the broadcast pid in
    `pid`, the episode nested under `programme` and `progress` as plain seconds.
    Both end up with the broadcast pid in `id` and the episode pid in the urn.
    """
    programme = original_object.get("programme")
    if not isinstance(programme, dict):
        return original_object
    # The broadcast's own fields win, including its `type` and `id`
    summary = {
        **programme,
        **{k: v for k, v in original_object.items() if k != "programme"},
    }
    summary["id"] = original_object.get("id") or original_object.get("pid")
    summary["urn"] = original_object.get("urn") or programme.get("urn")
    if not isinstance(summary.get("progress"), dict):
        # Seconds into the broadcast, not the listener's progress through it
        summary.pop("progress", None)
    return summary


class ModelFactory:
    PLAYABLE_ITEM_URN_MAP: ClassVar[dict[str, type]] = {
        ItemURN.COLLECTION: Collection,
        ItemURN.CATEGORY: Category,
        ItemURN.SERIES: Podcast,
        ItemURN.RADIO_SHOW_OR_PODCAST: RadioShow,
        ItemURN.PROMO_ITEM: PromoItem,
        ItemURN.PLAYLIST: Playlist,
    }

    CONTAINER_URN_MAP: ClassVar[dict[str, type]] = {
        ItemURN.COLLECTION: Collection,
        ItemURN.CATEGORY: Category,
        ItemURN.PLAYLIST: Playlist,
    }

    CONTAINER_SCHEMA_MAP: ClassVar[dict[str, type]] = {
        BaseSoundsTypes.PLAYABLE_ITEMS: CategoryItemContainer,
        # Collection group of items
        BaseSoundsTypes.CONTAINER_ITEMS: CollectionItemContainer,
        BaseSoundsTypes.CONTAINER_ITEMS_PAGINATED_RESPONSE: CollectionItemContainer,
    }

    def _programme_episode(self, original_object) -> tuple[type, dict]:
        """Reads contents from PROGRAMME_FROM_PID, decides its type and extracts the episode"""
        if original_object["total"] > 1:
            raise NotImplementedError("Container has more than 1 programme!")
        episode = original_object["data"][0]
        episode_type = _episode_or_show_or_audiobook_episode(episode)
        # return (PodcastEpisode if "podcasts" in formats else RadioShow), episode
        return episode_type, episode

    def parse_object(
        self,
        original_object: dict,
        parent_network: dict | SoundsTypes | None = None,
        type_hint: type[SoundsTypes] | None = None,
    ) -> Any:
        new_type: type[Any]
        if type_hint:
            new_type = type_hint
        else:
            schema_type = (
                original_object["$schema"].rsplit("/", 1)[1]
                if "$schema" in original_object
                else None
            )

            object_type = original_object.get("type", None)
            if object_type is None:
                object_type = schema_type

            raw_urn = original_object.get("urn")
            urn = raw_urn.rsplit(":", 1)[0] if raw_urn else None

            if object_type in ItemType:
                match object_type:
                    # Menu item, container or schedule
                    case ItemType.INLINE_DISPLAY_MODULE:
                        if original_object["id"] == IDType.SCHEDULE_ITEMS:
                            # This is a container of schedule items
                            new_type = Schedule
                        elif "container" in original_object["id"]:
                            new_type = Container
                        elif original_object["id"] == IDType.SINGLE_ITEM_PROMO:
                            # This is the special promo item menu, ignoring for now
                            return None
                        else:
                            new_type = MenuItem

                    case ItemType.PLAYABLE_ITEM:
                        if urn == ItemURN.EPISODE:
                            new_type = _episode_or_show_or_audiobook_episode(
                                original_object, parent_network
                            )
                        elif urn == ItemURN.CLIP:
                            # Sometimes these can appear in podcast episodes listings
                            new_type = _clip_or_episode(original_object, parent_network)
                        elif urn == ItemURN.NETWORK:
                            new_type = _live_station_or_station(original_object)
                        elif urn in self.PLAYABLE_ITEM_URN_MAP:
                            new_type = self.PLAYABLE_ITEM_URN_MAP[urn]
                        else:
                            logger.warning(
                                f"No playableitem: {original_object} {type(original_object)}"
                            )
                            return None

                    case ItemType.DISPLAY_ITEM:
                        if original_object.get("item") is not None:
                            return None
                        new_type = MenuItem

                    case ItemType.BROADCAST_SUMMARY | ItemType.BROADCAST:
                        if urn == ItemURN.NETWORK:
                            new_type = Station
                        original_object = _broadcast_as_summary(original_object)
                        playable = original_object.get("playable_item")
                        if playable is not None:
                            # On a broadcast summary, playable_item.id is the version pid.
                            original_object = {
                                **original_object,
                                "version_pid": playable.get("id"),
                            }
                        if (
                            original_object.get("progress")
                            and original_object["progress"].get("value") == 0
                        ) or original_object.get("on_air"):
                            # Live, or not yet aired
                            new_type = ScheduleItem
                        elif playable is not None:
                            new_type = RadioShow
                        else:
                            new_type = ScheduleItem

                    case ItemType.RADIO_SEARCH:
                        new_type = StationSearchResult
                        # Search results embed the actual station details in a now key
                        original_object = original_object["now"]

                    case ItemType.SEGMENT_ITEM:
                        new_type = Segment

                    case ItemType.INLINE_HEADER_MODULE:
                        new_type = Header

                    case ItemType.EPISODE:
                        new_type = _episode_or_show_or_audiobook_episode(
                            original_object, parent_network
                        )

                    case _:
                        logger.error(f"No ItemType handler for {original_object}")
                        return None

            elif object_type in ContainerType or object_type in BaseSoundsTypes:
                # This is a nested/parent container, work out which
                if urn in self.CONTAINER_URN_MAP:
                    new_type = self.CONTAINER_URN_MAP[urn]
                elif object_type == BaseSoundsTypes.PLAYABLE_ITEMS_RESPONSE:
                    new_type = BasicContainer
                elif object_type == ContainerType.BRAND:
                    new_type = _podcast_or_series(original_object, urn, parent_network)
                elif object_type in self.CONTAINER_SCHEMA_MAP:
                    new_type = self.CONTAINER_SCHEMA_MAP[object_type]
                elif object_type == BaseSoundsTypes.PROGRAMMES:
                    new_type, original_object = self._programme_episode(original_object)
                elif object_type in (
                    ContainerType.ITEM,
                    ContainerType.SERIES,
                ):
                    new_type = _podcast_or_series(original_object, urn, parent_network)
                else:
                    logger.warning(f"Unknown container type: {object_type}.")
                    logger.warning("Defaulting to bare Container.")
                    logger.debug(original_object)
                    new_type = Container
                # This is a station or network
            elif original_object.get("network_type"):
                new_type = Network
            elif "key" in original_object:
                # This is a weird nested network thing
                new_type = Network
            else:
                return None

            if not new_type:
                logger.error(f"Unexpected original_object type: {object_type}")
                logger.debug(f"Object:\n{original_object}\n\nSchema type:{schema_type}")
                raise ParserError("Unexpected object type.")

        new_object = convert_between_types(original_object, new_type)

        if hasattr(new_object, "post_processing"):
            new_object.post_processing(logger=logger)
        if type_hint and type(new_object) is not type_hint:
            raise ParserError(f"{type_hint} requested, but {type(new_object)} received")
        return new_object


def convert_between_types(original_object, new_type):
    try:
        required_fields = {f.name for f in fields(new_type)}
    except TypeError as e:
        raise ParserError(f"Unexpected field when creating object: {new_type}") from e

    attrs = {}

    if dataclasses.is_dataclass(original_object) and not isinstance(
        original_object, type
    ):
        attrs = {
            f.name: getattr(original_object, f.name)
            for f in dataclasses.fields(original_object)
            if f.name in required_fields
        }
    elif isinstance(original_object, dict):
        renames = _api_field_map(new_type)
        source = {renames.get(k, k): v for k, v in original_object.items()}
        attrs = {k: v for k, v in source.items() if k in required_fields}
    else:
        pass
    try:
        new_object = new_type(**attrs)
    except TypeError as e:
        raise ParserError(
            "Not all required fields present.\n"
            "Required fields: {required_fields}\n"
            "Available fields: {attrs}"
        ) from e
    new_object = parse_nested_objects(new_object)
    return new_object


def parse_nested_objects(node: SoundsTypes) -> SoundsTypes:
    for nested_object in NESTED_OBJECTS:
        value = getattr(node, nested_object.source_key, None)
        if not value:
            continue

        # There are occasional (annoying) clashes where a typically nested
        # object key is used for another type, e.g. duration can be an int
        if type(value) is dict:
            source_dicts, is_list = [value], False
        elif type(value) is list and all(type(item) is dict for item in value):
            source_dicts, is_list = value, True
        else:
            continue

        if nested_object.list_only and type(value) is dict:
            continue

        out_objects = []
        for source_dict in source_dicts:
            if nested_object.concrete_class:
                out_object = ModelFactory().parse_object(
                    source_dict,
                    parent_network=getattr(node, "network", None) or node,
                    type_hint=nested_object.replacement_model,
                )
            else:
                out_object = ModelFactory().parse_object(
                    source_dict,
                    parent_network=getattr(node, "network", None) or node,
                )
            if out_object is None or type(out_object) is dict:
                logger.error("Failed to parse nested object: %s", source_dict)
            out_objects.append(out_object)

        setattr(
            node,
            nested_object.source_key,
            out_objects if is_list else out_objects[0],
        )
    return node
