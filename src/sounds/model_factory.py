from dataclasses import fields
from logging import Logger
from typing import ClassVar

from sounds.constants import (
    BaseSoundsTypes,
    ContainerType,
    ItemURN,
    PlayableSoundsTypes,
)
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
    PLAYABLE_ITEM_URN_MAP: ClassVar[dict[str, type]] = {
        ItemURN.COLLECTION.value: Collection,
        ItemURN.CATEGORY.value: Category,
        ItemURN.SERIES.value: Podcast,
        ItemURN.RADIO_SHOW_OR_PODCAST.value: RadioShow,
        ItemURN.PROMO_ITEM.value: PromoItem,
        ItemURN.PLAYLIST.value: Playlist,
    }

    CONTAINER_URN_MAP: ClassVar[dict[str, type]] = {
        ItemURN.COLLECTION.value: Collection,
        ItemURN.CATEGORY.value: Category,
        ItemURN.PLAYLIST.value: Playlist,
    }

    CONTAINER_SCHEMA_MAP: ClassVar[dict[str, type]] = {
        BaseSoundsTypes.PLAYABLE_ITEMS.value: CategoryItemContainer,
        # Collection group of items
        BaseSoundsTypes.CONTAINER_ITEMS.value: CollectionItemContainer,
    }

    def __init__(self, logger: Logger):
        self.logger = logger

    def _podcast_or_series(self, original_object, urn) -> type:
        # return (
        #     Podcast
        #     if (original_object.get("network") or {}).get("id") == "bbc_sounds_podcasts"
        #     else RadioSeries
        # )
        if (
            "network" in original_object
            and (original_object.get("network").get("id") == "bbc_sounds_podcasts")
        ) or (
            "network" not in original_object
            and urn == ItemURN.RADIO_SHOW_OR_PODCAST.value
        ):
            return Podcast
        return RadioSeries

    def _episode_or_show(self, original_object) -> type:
        container = original_object.get("container")
        if not container:
            return RadioShow
        is_brand = ContainerType(container.get("type")) == ContainerType.BRAND
        is_podcast_network = (original_object.get("network") or {}).get(
            "id"
        ) == "bbc_sounds_podcasts"
        return RadioShow if is_brand and not is_podcast_network else PodcastEpisode

    def _clip_or_episode(self, original_object) -> type:
        # Sometimes these can appear in podcast episodes listings
        container = original_object.get("container")
        if container and ContainerType(container.get("type")) == ContainerType.BRAND:
            return PodcastEpisode
        return RadioClip

    def _live_station_or_station(self, original_object) -> type:
        return LiveStation if original_object.get("synopses") is not None else Station

    def _programme_episode(self, original_object) -> tuple[type, dict]:
        pass

    def parse_object(self, original_object: dict):
        from sounds.constants import ContainerType, IDType, ItemType, ItemURN

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
                case ItemType.INLINE_DISPLAY_MODULE.value:
                    if original_object["id"] == IDType.SCHEDULE_ITEMS.value:
                        # This is a container of schedule items
                        new_type = Schedule
                    elif "container" in original_object["id"]:
                        new_type = Container
                    elif original_object["id"] == IDType.SINGLE_ITEM_PROMO.value:
                        # This is the special promo item menu, ignoring for now
                        return None
                    else:
                        new_type = MenuItem

                case ItemType.PLAYABLE_ITEM.value:
                    if urn == ItemURN.EPISODE.value:
                        new_type = self._episode_or_show(original_object)
                    elif urn == ItemURN.CLIP.value:
                        # Sometimes these can appear in podcast episodes listings
                        new_type = self._clip_or_episode(original_object)
                    elif urn == ItemURN.STATION.value:
                        new_type = self._live_station_or_station(original_object)
                    elif urn in self.PLAYABLE_ITEM_URN_MAP:
                        new_type = self.PLAYABLE_ITEM_URN_MAP[urn]
                    else:
                        self.logger.warning(
                            f"No playableitem: {original_object} {type(original_object)}"
                        )
                        return None

                case ItemType.DISPLAY_ITEM.value:
                    if object.get("item") is not None:
                        return None
                    new_type = MenuItem

                case ItemType.BROADCAST_SUMMARY.value | ItemType.BROADCAST.value:
                    if urn == ItemURN.STATION.value:
                        new_type = Station
                    if (
                        object.get("progress") and object["progress"].get("value") == 0
                    ) or object.get("on_air"):
                        # Live, or not yet aired
                        new_type = ScheduleItem
                    elif original_object.get("playable_item") is not None:
                        new_type = RadioShow
                    else:
                        new_type = ScheduleItem

                case ItemType.RADIO_SEARCH.value:
                    new_type = StationSearchResult
                    # Search results embed the actual station details in a now key
                    original_object = original_object["now"]

                case ItemType.SEGMENT_ITEM.value:
                    new_type = Segment

                case ItemType.INLINE_HEADER_MODULE.value:
                    new_type = Header

                case _:
                    self.logger.error(f"No ItemType handler for {original_object}")
                    return None

        elif object_type in ContainerType or object_type in BaseSoundsTypes:
            # This is a nested/parent container, work out which
            if urn in self.CONTAINER_URN_MAP:
                new_type = self.CONTAINER_URN_MAP[urn]
            elif object_type == ContainerType.BRAND.value:
                new_type = self._podcast_or_series(original_object, urn)
            elif object_type in self.CONTAINER_SCHEMA_MAP:
                new_type = self.CONTAINER_SCHEMA_MAP[object_type]
            elif object_type == BaseSoundsTypes.PROGRAMMES.value:
                new_type, original_object = self._programme_episode(original_object)
            elif object_type in (ContainerType.ITEM.value, ContainerType.SERIES.value):
                if urn == ItemURN.RADIO_SHOW_OR_PODCAST.value:
                    new_type = (
                        Podcast
                        if (original_object.get("network") or {}).get("id")
                        in ("bbc_sounds_podcasts", "bbc_news")
                        else RadioSeries
                    )
                else:
                    new_type = Podcast
            else:
                self.logger.warning(f"Unknown container type: {object_type}")
                self.logger.debug(original_object)
            # This is a station or network
        elif original_object.get("network_type") is not None:
            new_type = Network
        elif "key" in original_object:
            # This is a weird nested network thing
            new_type = Network
        else:
            return None

        if not new_type:
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
