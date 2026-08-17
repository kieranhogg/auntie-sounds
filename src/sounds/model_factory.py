from dataclasses import fields
from logging import Logger

from sounds.constants import BaseSoundsTypes, PlayableSoundsTypes
from sounds.exceptions import ParserError
from sounds.models import (
    Broadcast,
    Category,
    CategoryItemContainer,
    Collection,
    CollectionItemContainer,
    Container,
    DisplayItem,
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


class ModelFactory:
    def __init__(self, logger: Logger):
        self.logger = logger

    def parse_object(self, original_object: dict):
        from sounds.constants import ContainerType, IDType, ItemType, ItemURN

        schema_type = None
        new_type = None

        if "$schema" in original_object:
            schema_type = original_object["$schema"].rsplit("/", 1)[1]

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
                case ItemType.INLINE_DISPLAY_MODULE.value:
                    # Menu item, container or schedule
                    if original_object["id"] == IDType.SCHEDULE_ITEMS.value:
                        # This is a container of schedule items
                        new_type = Schedule
                    elif "container" in original_object.get("id"):
                        new_type = Container
                    elif original_object["id"] == IDType.SINGLE_ITEM_PROMO.value:
                        # This is the special promo item menu, ignoring for now
                        pass
                    else:
                        new_type = MenuItem
                case ItemType.PLAYABLE_ITEM.value:
                    match urn:
                        case ItemURN.EPISODE.value:
                            if (
                                original_object.get("container")
                                and ContainerType(
                                    original_object.get("container").get("type")
                                )
                                == ContainerType.BRAND
                                and original_object.get("network").get("id")
                                != "bbc_sounds_podcasts"
                            ) or not original_object.get("container"):
                                new_type = RadioShow
                            else:
                                new_type = PodcastEpisode
                        case ItemURN.CLIP.value:
                            # Sometimes these can appear in podcast episodes listings
                            if (
                                original_object.get("container")
                                and ContainerType(
                                    original_object.get("container").get("type")
                                )
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
                            if original_object.get("synopses") is not None:
                                new_type = LiveStation
                            else:
                                new_type = Station
                        case ItemURN.PROMO_ITEM.value:
                            new_type = PromoItem
                        case ItemURN.PLAYLIST.value:
                            new_type = Playlist
                        case _:
                            self.logger.warning(
                                f"No playableitem: {original_object} {type(original_object)}"
                            )

                case ItemType.DISPLAY_ITEM.value:
                    new_type = DisplayItem
                case ItemType.BROADCAST_SUMMARY.value | ItemType.BROADCAST.value:
                    if urn == ItemURN.STATION.value:
                        new_type = Station
                    if (
                        original_object.get("progress")
                        and original_object.get("progress").get("value", None) == 0
                    ) or original_object.get("on_air"):
                        # Live, or not yet aired
                        new_type = ScheduleItem
                    elif original_object["playable_item"] is not None:
                        new_type = RadioShow
                    elif hasattr(original_object, "live"):
                        new_type = Broadcast
                    else:
                        new_type = ScheduleItem
                case ItemType.EPISODE.value:
                    new_type = RadioShow
                case ItemType.RADIO_SEARCH.value:
                    new_type = StationSearchResult
                    # Search results embed the actual station details in a now key
                    original_object = original_object["now"]
                case ItemType.SEGMENT_ITEM.value:
                    new_type = Segment
                case ItemType.INLINE_HEADER_MODULE.value:
                    new_type = Header
                case _:
                    self.logger.warning("No IT found")
        elif object_type in ContainerType or object_type in BaseSoundsTypes:
            # This is a nested/parent container, work out which
            if urn == ItemURN.COLLECTION.value:
                new_type = Collection
            elif urn == ItemURN.CATEGORY.value:
                new_type = Category
            elif object_type == ContainerType.BRAND.value:
                if (
                    "network" in original_object
                    and (
                        original_object.get("network").get("id")
                        == "bbc_sounds_podcasts"
                    )
                ) or (
                    "network" not in original_object
                    and urn == ItemURN.RADIO_SHOW_OR_PODCAST.value
                ):
                    new_type = Podcast
                else:
                    new_type = RadioSeries
            elif object_type == BaseSoundsTypes.PLAYABLE_ITEMS.value:
                # Category of items
                new_type = CategoryItemContainer
            elif object_type == BaseSoundsTypes.CONTAINER_ITEMS.value:
                # Collection group of items
                new_type = CollectionItemContainer
            elif object_type == BaseSoundsTypes.PROGRAMMES.value:
                original_object = original_object["data"][0]
                if original_object["total"] > 1:
                    raise NotImplementedError("Container has more than 1 programme!")
                new_type = PodcastEpisode
            elif (
                object_type == ContainerType.SERIES.value
                or urn == ItemURN.RADIO_SHOW_OR_PODCAST.value
            ):
                new_type = RadioSeries
            elif object_type == ContainerType.ITEM.value:
                if urn == ItemURN.SERIES.value:
                    new_type = Podcast
                elif urn == ItemURN.RADIO_SHOW_OR_PODCAST.value:
                    new_type = (
                        Podcast
                        if (object.get("network") or {}).get("id")
                        == "bbc_sounds_podcasts"
                        else RadioSeries
                    )
                else:
                    new_type = Podcast
            else:
                self.logger.warning(f"Unknown container type: {object_type}")
                self.logger.debug(original_object)
        elif original_object.get("network_type", None) is not None:
            # This is a station or network
            if original_object.get("network_type") == "master_brand":
                new_type = Network
            elif original_object.get("network_type") == "service":
                # Local station, treat the same at present
                new_type = Network
            else:
                raise ParserError(
                    f"Other network type: {object_type} {original_object}"
                )
        elif "key" in original_object:
            # This is a weird nested network thing
            new_type = Network
        elif schema_type in PlayableSoundsTypes:
            self.logger.error("Unable to parse object")
            self.logger.debug(schema_type)
            return None
        else:
            self.logger.error(f"Unexpected object type: {object_type}")
            self.logger.debug(
                f"Object:\n{original_object}\n\nSchema type:{schema_type}"
            )
            return None

        try:
            required_fields = {f.name for f in fields(new_type)}
        except TypeError:
            return None
        attrs = {k: v for k, v in original_object.items() if k in required_fields}

        new_object = new_type(**attrs)
        return new_object
