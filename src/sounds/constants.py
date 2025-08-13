from enum import Enum
import re
from typing import Final

# This is the ID of the cookie we use to check we have a valid session
COOKIE_ID = "ckns_id"

VERBOSE_LOG_LEVEL: Final[int] = 5


class URLs:
    # Auth URLs
    LOGIN_START = "https://session.bbc.co.uk/session?ptrt=https%3A%2F%2Fwww.bbc.co.uk%2Fsounds&context=iplayerradio&userOrigin=sounds"
    LOGIN_BASE = "https://account.bbc.com"
    COOKIE_URL = "https://www.bbc.co.uk"
    JWT_URL = "https://rms.api.bbc.co.uk/v2/sign/token/{station_id}"
    INTL_JWT = "https://web-cdn.api.bbci.co.uk/xd/media-token?{id_type}={id}"
    USER_INFO = "https://www.bbc.co.uk/userinfo"

    # Streaming URLs
    MEDIASET_URL = "https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/mediaset/pc/vpid/{station_id}/format/json?jwt_auth={jwt_auth_token}"
    EPISODE_MEDIASET = "https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/mediaset/pc/vpid/{episode_id}"

    # Station URLs
    STATIONS_URL = "https://rms.api.bbc.co.uk/v2/experience/inline/stations"
    LIVE_STATION_DETAILS = (
        "https://rms.api.bbc.co.uk/v2/experience/inline/play/{station_id}"
    )
    LIVE_STATION_URL = "https://www.bbc.co.uk/sounds/play/live:{station_id}"
    NOW_PLAYING_URL = "https://rms.api.bbc.co.uk/v2/services/{station_id}/segments/latest?limit={limit}"
    SCHEDULE_URL = (
        "https://rms.api.bbc.co.uk/v2/experience/inline/schedules/{station_id}"
    )
    SEGMENTS = "https://rms.api.bbc.co.uk/v2/versions/{pid}/segments"
    PID_LIVE = "https://rms.api.bbc.co.uk/v2/broadcasts/{pid}"
    PID_PLAYABLE = "https://rms.api.bbc.co.uk/v2/programmes/{pid}/playable"
    CONTAINER_URL = "https://rms.api.bbc.co.uk/v2/experience/inline/container/{urn}"

    # Menu, search, etc.
    EXPERIENCE_MENU = "https://rms.api.bbc.co.uk/v2/my/experience/inline/listen"

    SEARCH_URL = "https://rms.api.bbc.co.uk/v2/experience/inline/search?q={search}"
    SHOW_SEARCH_URL = (
        "https://rms.api.bbc.co.uk/v2/programmes/search/container?q={search}"
    )
    EPISOSDE_SEARCH_URL = (
        "ttps://rms.api.bbc.co.uk/v2/programmes/search/playable?q={search}"
    )
    PODCASTS = "https://rms.api.bbc.co.uk/v2/experience/inline/speech"
    MUSIC = "https://rms.api.bbc.co.uk/v2/experience/inline/music"
    NEWS = "https://rms.api.bbc.co.uk/v2/experience/inline/container/urn:bbc:radio:category:news"


class SignedInURLs:
    RENEW_SESSION = (
        "https://session.bbc.co.uk/session?context=iplayerradio&userOrigin=sounds"
    )
    PLAYS_URL = "https://rms.api.bbc.co.uk/v2/my/programmes/plays"
    RECOMMENDATIONS = (
        "https://rms.api.bbc.co.uk/v2/my/programmes/recommendations/playable"
    )
    MUSIC_RECOMMENDATIONS = "https://rms.api.bbc.co.uk/v2/my/programmes/recommendations/music-mixes/playable"
    LATEST = "https://rms.api.bbc.co.uk/v2/my/programmes/follows/playable"
    SUBSCRIBED = "https://rms.api.bbc.co.uk/v2/my/programmes/follows"
    BOOKMARKS = "https://rms.api.bbc.co.uk/v2/my/programmes/favourites/playable"
    CONTINUE = "https://rms.api.bbc.co.uk/v2/my/programmes/plays/playable"


class ImageType(Enum):
    """An enum for valid image types for recipes"""

    COLOUR = "colour"
    COLOUR_DEFAULT = "colour_default"
    BACKGROUND = "background"
    BLOCKS_COLOUR = "blocks_colour"
    BLOCKS_COLOUR_BLACK = "blocks_colour_black"
    BLOCKS_COLOUR_WHITE = "blocks_colour_white"


class ItemURN(Enum):
    EPISODE = "urn:bbc:radio:episode"
    CLIP = "urn:bbc:radio:clip"
    COLLECTION = "urn:bbc:radio:collection"
    CATEGORY = "urn:bbc:radio:category"
    SERIES = "urn:bbc:radio:series"
    RADIO_SHOW_OR_PODCAST = "urn:bbc:radio:brand"
    STATION = "urn:bbc:radio:network"
    PROMO_ITEM = "bbc:radio:content:single_item_promo"


class ItemURNRegex(Enum):
    EPISODE = r"(urn\:bbc\:radio\:episode\:(.*))"
    CLIP = r"(urn\:bbc\:radio\:clip)\:(.*)"
    COLLECTION = r"(urn\:bbc\:radio\:collection)\:(.*)"
    CATEGORY = r"(urn\:bbc\:radio\:category)\:(.*)"
    SERIES = r"(urn\:bbc\:radio\:series)\:(.*)"
    RADIO_SHOW_OR_PODCAST = r"(urn\:bbc\:radio\:brand)\:(.*)"
    STATION = r"(urn\:bbc\:radio\:network)\:(.*)"
    PROMO_ITEM = "bbc:radio:content:single_item_promo"

    @staticmethod
    def get(value):
        for regex in ItemURN:
            item_type = ItemURN(regex).name
            pattern = ItemURN(regex).value
            match = re.findall(pattern, value)
            if match:
                return item_type, match
        return None


class ItemObjectMap(Enum):
    # Prevent circular import
    from .models import (
        Category,
        Collection,
        Podcast,
        PodcastEpisode,
        PromoItem,
        PlayableItem,
        RadioShow,
        ScheduleItem,
        Station,
    )

    EPISODE = [
        (
            PodcastEpisode,
            lambda item: ContainerType(item.get("container").get("type"))
            == ContainerType.SERIES,
        ),
        (
            ScheduleItem,
            lambda item: ContainerType(item.get("container").get("type"))
            == ContainerType.BRAND,
        ),
    ]
    CLIP = PlayableItem
    COLLECTION = Collection
    CATEGORY = Category
    SERIES = Podcast  # These are time-based collections of radio shows, e.g.: Glastonbury Live Sets (2025)
    RADIO_SHOW_OR_PODCAST = [
        (RadioShow, lambda item: ItemType(item.get("type")) == ItemType.CONTAINER),
        (
            Podcast,
            lambda item: item.get("container")
            and item.get("container").get("network").get("id") == "bbc_sounds_podcasts",
        ),
    ]
    STATION = Station
    PROMO_ITEM = PromoItem


class ItemType(Enum):
    MODULE = "inline_display_module"
    PLAYABLE_ITEM = "playable_item"
    CONTAINER = "container_item"
    DISPLAY_ITEM = "display_item"
    BROADCAST_SUMMARY = "broadcast_summary"


class ContainerType(Enum):
    BRAND = "brand"
    SERIES = "series"
    ITEM = "container_item"


class NetworkType(Enum):
    MASTER = "master_brand"
