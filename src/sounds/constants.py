from enum import Enum
from typing import TYPE_CHECKING, Final

# This is the ID of the cookie we use to check we have a valid session
COOKIE_ID = "ckns_id"

VERBOSE_LOG_LEVEL: Final[int] = 5

FIXTURES_FOLDER = "tests/json/"


class Fixtures(Enum):
    EXPERIENCE_MENU = "menu.json"
    SCHEDULE_DATE_URL = "schedule.json"
    SCHEDULE_URL = "schedule.json"


class SignedInURLs(Enum):
    RENEW_SESSION = (
        "https://session.bbc.co.uk/session?context=iplayerradio&userOrigin=sounds"
    )
    PLAYS = "https://rms.api.bbc.co.uk/v2/my/programmes/plays"
    RECOMMENDATIONS = (
        "https://rms.api.bbc.co.uk/v2/my/programmes/recommendations/playable"
    )
    MUSIC_RECOMMENDATIONS = "https://rms.api.bbc.co.uk/v2/my/programmes/recommendations/music-mixes/playable"
    LATEST = "https://rms.api.bbc.co.uk/v2/my/programmes/follows/playable"
    SUBSCRIBED = "https://rms.api.bbc.co.uk/v2/my/programmes/follows"
    BOOKMARKS = "https://rms.api.bbc.co.uk/v2/my/programmes/favourites/playable"
    CONTINUE = "https://rms.api.bbc.co.uk/v2/my/programmes/plays/playable"
    PID_PLAYABLE = "https://rms.api.bbc.co.uk/v2/my/programmes/{pid}/playable"
    CONTAINER_URL = "https://rms.api.bbc.co.uk/v2/my/experience/inline/container/{urn}"


class URLs(Enum):
    # Not yet used
    """
            /v2/networks - Provides the list of all the v2 networks
            /v2/networks/playable - Provides the list of all the playable networks
            /v2/networks/{id}/playable - Provides the network playable item by network ID. <span>🎶</span> Green Day
            /radio/networks.json - All iPlayer Radio networks - contains business logic for masterbrand and service relationships
    /v2/services/{sid}/tracks/latest/playable - Retrieve list of tracks as playable items for a service <span>🎶</span> Deftones

    """

    # Auth URLs
    LOGIN_START = "https://session.bbc.co.uk/session?ptrt=https%3A%2F%2Fwww.bbc.co.uk%2Fsounds&context=iplayerradio&userOrigin=sounds"
    LOGIN_BASE = "https://account.bbc.com"
    COOKIE_BASE = "https://www.bbc.co.uk"
    JWT = "https://rms.api.bbc.co.uk/v2/sign/token/{station_id}"
    INTL_JWT = "https://web-cdn.api.bbci.co.uk/xd/media-token?{id_type}={id}"
    USER_INFO = "https://www.bbc.co.uk/userinfo"

    # Streaming URLs
    MEDIASET = "https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/mediaset/pc/vpid/{station_id}/format/json?jwt_auth={jwt_auth_token}"
    EPISODE_MEDIASET = "https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/mediaset/pc/vpid/{episode_id}"

    # Station URLs
    NETWORKS_LIST = "https://rms.api.bbc.co.uk/radio/networks.json"
    STATIONS = "https://rms.api.bbc.co.uk/v2/experience/inline/stations"
    LIVE_STATION_DETAILS = (
        "https://rms.api.bbc.co.uk/v2/experience/inline/play/{station_id}"
    )
    STATION_DETAILS = "https://rms.api.bbc.co.uk/v2/networks/{station_id}"
    STATION_PLAYABLE_DETAILS = (
        "https://rms.api.bbc.co.uk/v2/networks/{station_id}/playable"
    )
    LIVE_STATION = "https://www.bbc.co.uk/sounds/play/live:{station_id}"
    NOW_PLAYING = "https://rms.api.bbc.co.uk/v2/services/{station_id}/segments/latest?limit={limit}"
    SCHEDULE = "https://rms.api.bbc.co.uk/v2/experience/inline/schedules/{station_id}"
    SCHEDULE_DATE = (
        "https://rms.api.bbc.co.uk/v2/experience/inline/schedules/{station_id}/{date}"
    )
    SEGMENTS = "https://rms.api.bbc.co.uk/v2/versions/{vpid}/segments"

    # Episodes, programmes, series etc.
    PLAYABLE_ITEMS_CONTAINER = (
        "https://rms.api.bbc.co.uk/v2/programmes/playable?container={pid}&sort=sequential"
    )
    CATEGORY_LATEST = "https://rms.api.bbc.co.uk/v2/programmes/playable?category={category}&sort=-release_date&experience=domestic"
    CATEGORY_POPULAR = "https://rms.api.bbc.co.uk/v2/programmes/playable?category={category}&sort=popular&experience=domestic"
    BROADCAST = "https://rms.api.bbc.co.uk/v2/broadcasts/{pid}"
    PID = "https://rms.api.bbc.co.uk/v2/programmes/{pid}"
    PID_PLAYABLE = "https://rms.api.bbc.co.uk/v2/programmes/{pid}/playable"
    CONTAINER_URL = "https://rms.api.bbc.co.uk/v2/experience/inline/container/{urn}"
    PLAYLIST = "https://www.bbc.co.uk/programmes/{pid}/playlist.json"
    COLLECTIONS_FULL = "https://rms.api.bbc.co.uk/v2/collections/{pid}/members/container?experience=domestic&offset={offset}&limit={limit}"
    COLLECTIONS = "https://rms.api.bbc.co.uk/v2/collections/{pid}/members/container?experience=domestic"

    # Menu, search, etc.
    EXPERIENCE_MENU = "https://rms.api.bbc.co.uk/v2/my/experience/inline/listen"

    SEARCH_URL = "https://rms.api.bbc.co.uk/v2/experience/inline/search?q={search}"
    SHOW_SEARCH_URL = (
        "https://rms.api.bbc.co.uk/v2/programmes/search/container?q={search}"
    )
    EPISOSDE_SEARCH_URL = (
        "https://rms.api.bbc.co.uk/v2/programmes/search/playable?q={search}"
    )
    PODCASTS = "https://rms.api.bbc.co.uk/v2/experience/inline/speech"
    MUSIC = "https://rms.api.bbc.co.uk/v2/experience/inline/music"
    NEWS = "https://rms.api.bbc.co.uk/v2/experience/inline/container/urn:bbc:radio:category:news"


# URLs = GenericURLs. SignedInURLs


class BaseSoundsTypes(Enum):
    """Types as defined in the JSON schema"""

    PROGRAMMES = "Programmes"
    EXPERIENCE_RESPONSE = "ExperienceResponse"
    CONTAINER = "PlayableItems"
    ERROR = "ErrorResponse"
    SEGMENTS = "SegmentItemsResponse"
    CONTAINER_ITEMS = "ContainerItems"
    PLAYABLE_ITEMS = "PlayableItems"


class PlayableSoundsTypes(Enum):
    """Types as defined in the JSON schema"""

    EPISODE = "Episode"
    PROGRAMMES = "Programmes"
    EXPERIENCE_RESPONSE = "ExperienceResponse"
    PLAYABLE_ITEM = "PlayableItem"
    BROADCASTS = "BroadcastsResponse"


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
    PROMO_ITEM = "urn:bbc:radio:content:single_item_promo"
    SEGMENT_ITEM = "urn:bbc:radio:segment:music"


class ItemType(Enum):
    PLAYABLE_ITEM = "playable_item"
    DISPLAY_ITEM = "display_item"
    BROADCAST_SUMMARY = "broadcast_summary"
    INLINE_DISPLAY_MODULE = "inline_display_module"
    INLINE_HEADER_MODULE = "inline_header_module"
    EPISODE = "episode"
    BROADCAST = "broadcast"
    RADIO_SEARCH = "live_search_result_item"
    SEGMENT_ITEM = "segment_item"


class ContainerType(Enum):
    BRAND = "brand"
    SERIES = "series"
    ITEM = "container_item"


class NetworkType(Enum):
    MASTER = "master_brand"


class IDType(Enum):
    SCHEDULE_ITEMS = "schedule_items"
    SINGLE_ITEM_PROMO = "single_item_promo"
    STATION_SEARCH_CONTAINER = "live_search"
    SHOW_SEARCH_CONTAINER = "container_search"
    EPISODE_SEARCH_CONTAINER = "playable_search"


class PlayStatus(Enum):
    STARTED = "started"
    PAUSED = "paused"
    ENDED = "ended"
    HEARTBEAT = "heartbeat"
