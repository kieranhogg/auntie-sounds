import logging
from dataclasses import fields
from enum import StrEnum, auto, unique
from typing import ClassVar

from sounds.models import (
    Category,
    CategoryItemContainer,
    Collection,
    CollectionItemContainer,
    Container,
    Header,
    LiveStation,
    MenuItem,
    Network,
    Playlist,
    Podcast,
    PodcastEpisode,
    PromoItem,
    RadioClip,
    RadioSeries,
    RadioShow,
    Schedule,
    ScheduleItem,
    Segment,
    Station,
    StationSearchResult,
)

logger = logging.getLogger(__name__)


def _podcast_or_series(
    original_object: dict,
    urn: str,
    parent_network: dict | Network | None = None,
) -> type:
    network_id = None
    if type(parent_network) is Network:
        network_id = parent_network.id
    else:
        network = original_object.get("network") or parent_network
        if network:
            network_id = network.get("id")

    if (network_id in ("bbc_sounds_podcasts", "bbc_news")) or (
        not network_id and urn == ItemURN.RADIO_SHOW_OR_PODCAST
    ):
        return Podcast
    return RadioSeries


def _episode_or_show(original_object) -> type:
    container = original_object.get("container")
    if not container:
        return RadioShow
    is_brand = ContainerType(container.get("type")) == ContainerType.BRAND
    is_podcast_network = (original_object.get("network") or {}).get(
        "id"
    ) == "bbc_sounds_podcasts"
    return RadioShow if is_brand and not is_podcast_network else PodcastEpisode


def _clip_or_episode(original_object) -> type:
    # Sometimes these can appear in podcast episodes listings
    container = original_object.get("container")
    if container and ContainerType(container.get("type")) == ContainerType.BRAND:
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
    STATION = "urn:bbc:radio:network"
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
    }

    def _programme_episode(self, original_object) -> tuple[type, dict]:
        """Reads contents from PROGRAMME_FROM_PID, decides its type and extracts the episode"""
        if original_object["total"] > 1:
            raise NotImplementedError("Container has more than 1 programme!")
        episode = original_object["data"][0]
        formats = {c.get("key") for c in episode.get("categories", [])}
        return (PodcastEpisode if "podcasts" in formats else RadioShow), episode

    def parse_object(
        self, original_object: dict, parent_network: dict | None = None, force_type=None
    ):
        if force_type:
            new_type = force_type
        else:
            new_type = None

            schema_type = (
                original_object["$schema"].rsplit("/", 1)[1]
                if "$schema" in original_object
                else None
            )

            object_type = original_object.get("type", None)
            if object_type is None:
                object_type = schema_type
            urn = (
                original_object.get("urn").rsplit(":", 1)[0]
                if original_object.get("urn")
                else None
            )

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
                            new_type = _episode_or_show(original_object)
                        elif urn == ItemURN.CLIP:
                            # Sometimes these can appear in podcast episodes listings
                            new_type = _clip_or_episode(original_object)
                        elif urn == ItemURN.STATION:
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
                        if urn == ItemURN.STATION:
                            new_type = Station
                        if (
                            original_object.get("progress")
                            and original_object["progress"].get("value") == 0
                        ) or original_object.get("on_air"):
                            # Live, or not yet aired
                            new_type = ScheduleItem
                        elif original_object.get("playable_item") is not None:
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

                    case _:
                        logger.error(f"No ItemType handler for {original_object}")
                        return None

            elif object_type in ContainerType or object_type in BaseSoundsTypes:
                # This is a nested/parent container, work out which
                if urn in self.CONTAINER_URN_MAP:
                    new_type = self.CONTAINER_URN_MAP[urn]
                elif object_type == ContainerType.BRAND:
                    new_type = _podcast_or_series(original_object, urn)
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
                    logger.warning(f"Unknown container type: {object_type}")
                    logger.debug(original_object)
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
                return None

        try:
            required_fields = {f.name for f in fields(new_type)}
        except TypeError:
            return None
        attrs = {k: v for k, v in original_object.items() if k in required_fields}

        new_object = new_type(**attrs)
        return new_object
