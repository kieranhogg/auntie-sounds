from enum import Enum, StrEnum, unique


@unique
class URLs(StrEnum):
    """URLs not in the usual endpoint format."""

    # resolves to: https://account.bbc.com/auth/identifier/signin?realm=%2F&clientId=Account&context=iplayerradio&ptrt=https%3A%2F%2Fwww.bbc.co.uk%2Fsounds&userOrigin=sounds&mvtUserId=<hash>&isCasso=false&action=sign-in&sequenceId=&redirectUri=https%3A%2F%2Fsession.bbc.co.uk%2Fsession%2Fcallback%3Frealm%3D%2F&service=IdSignInService&nonce=<nonce>

    JWT = "/v2/sign/token/{id}"
    INTL_JWT = "https://web-cdn.api.bbci.co.uk/xd/media-token?{id_type}={id}"
    USER_INFO = "https://www.bbc.co.uk/userinfo"

    # Streaming URLs
    MEDIASET = "https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/mediaset/pc/vpid/{id}/format/json?jwt_auth={jwt_auth_token}"
    I18N_MEDIASET = "https://open.live.bbc.co.uk/mediaselector/6/select/version/3.0/mediaset/pc/cvid/urn:bbc:pips:pid:{id}/format/json"
    EPISODE_MEDIASET = "https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/mediaset/pc/vpid/{episode_id}"

    # Auth URLs
    RENEW_SESSION = (
        "https://session.bbc.co.uk/session?context=iplayerradio&userOrigin=sounds"
    )
    LOGIN_START = (
        "https://session.bbc.co.uk/session?ptrt=https%3A%2F%2Fwww.bbc.co.uk%2Fsounds"
    )
    LOGIN_START_I18N = "https://account.bbc.com/auth?realm=%2F&clientId=Account&ptrt=https%3A%2F%2Fwww.bbc.com%2F&userOrigin=BBCS_BBC&purpose=free&isCasso=false&action=sign-in&redirectUri=https%3A%2F%2Fsession.bbc.com%2Fsession%2Fcallback%3Frealm%3D%2F&service=IdSignInService"
    LOGIN_BASE = "https://account.bbc.com"
    COOKIE_BASE = "https://www.bbc.co.uk"
    COOKIE_BASE_I18N = "https://www.bbc.com"


@unique
class Endpoints(Enum):
    login_required: bool
    response_type: str | None
    return_type: str | None

    def __new__(cls, value, login_required, response_type=None, return_type=None):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.login_required = login_required
        obj.response_type = response_type
        obj.return_type = return_type
        return obj

    # Station & Networks
    NETWORKS_DETAILED = (
        "/radio/networks.json",
        False,
        "NetworksResponse",
    )
    NETWORKS = (
        "/v2/networks?limit={limit}",
        False,
        "NetworksResponse",
        None,
    )
    NETWORK_SERVICES = (
        "/v2/networks/services?limit={limit}",
        False,
        "ServicesResponse",
    )
    NETWORKS_PLAYABLE = (
        "/v2/networks/playable",
        False,
        "PlayableItemsResponse",
        None,
    )
    NETWORK_DETAILS = ("/v2/networks/{network_id}", False, "NetworkResponse")
    NETWORK_PROMOS = (
        "/v2/networks/{network_id}/promos/display",
        False,
    )
    NETWORK_PROMOS_PLAYABLE = (
        "/v2/networks/{network_id}/promos/playable",
        False,
    )
    NETWORK_PLAYABLE_DETAILS = (
        "/v2/networks/{network_id}/playable",
        False,
    )

    STATIONS = (
        "/v2/experience/inline/stations",
        False,
        "ExperienceResponse",
    )
    STATION_DETAILS = ("/v2/networks/{station_id}", False)
    STATION_PLAYABLE_DETAILS = (
        "/v2/networks/{station_id}/playable",
        False,
    )
    LIVE_STATION = ("https://www.bbc.co.uk/sounds/play/live:{network_id}", False)

    # Segments & Schedules
    BROADCASTS = ("/v2/broadcasts?service={service_id}&sort=-start_at", False)
    BROADCASTS_LATEST = (
        "/v2/broadcasts/latest?service={service_id*}&sort=-start_at",
        False,
    )
    CURRENT_PROGRAMME = (
        "/v2/broadcasts/latest?on_air=now",
        False,
    )
    BROADCAST_SCHEDULE = ("/v2/broadcasts/schedules/{service_id}/{date}", False)
    LATEST_TRACKS = ("/v2/services/{station_id}/tracks/latest/playable", False)
    NOW_PLAYING = (
        "/v2/services/{service_id}/segments/latest?limit={limit}",
        False,
    )
    SCHEDULE = (
        "/v2/experience/inline/schedules/{service_id}",
        False,
    )
    SCHEDULE_DATE = (
        "/v2/experience/inline/schedules/{service_id}/{date}",
        False,
    )
    SEGMENTS = ("/v2/versions/{vpid}/segments", False)
    TRACKS = ("/v2/versions/{vpid}/tracks", False)

    # Episodes, programmes, series etc.
    PLAYABLE_ITEMS_CONTAINER = (
        "/v2/programmes/playable?container={pid}&sort=sequential",
        False,
    )
    CATEGORY_LATEST = (
        "/v2/programmes/playable?category={category}&sort=-release_date&experience=domestic",
        False,
    )
    CATEGORY_POPULAR = (
        "/v2/programmes/playable?category={category}&sort=popular&experience=domestic",
        False,
    )
    BROADCAST = ("/v2/broadcasts/{pid}", False)
    # Despite the name, this returns a single programme
    PROGRAMME_FROM_PID = ("/v2/programmes/{pid}", False)
    PROGRAMME_FROM_PID_PLAYABLE = (
        "/v2/programmes/{pid}/playable",
        False,
    )
    URN_CONTAINER = (
        "/v2/experience/inline/container/{urn}",
        False,
    )

    # This endpoint gets extra details from a pid such as vpid and parent pid
    PID_DETAILS = ("https://www.bbc.co.uk/programmes/{pid}/playlist.json", False)
    COLLECTIONS_FULL = (
        "/v2/collections/{pid}/members/container?experience=domestic&offset={offset}&limit={limit}",
        False,
    )
    COLLECTIONS = (
        "/v2/collections/{pid}/members/container?experience=domestic",
        False,
    )
    CURATIONS = (
        "/v2/curations/{pid}/members/playable?experience=domestic",
        False,
    )
    # Options: focus feel_good_tunes dance fresh_new_music greatest_hits
    TAGGED = ("/v2/tagged/{tag}/playable", False)
    # Menu, search, etc.
    SEARCH_URL = (
        "/v2/experience/inline/search?q={search}",
        False,
    )
    SHOW_SEARCH_URL = (
        "/v2/programmes/search/container?q={search}",
        False,
    )
    EPISODE_SEARCH_URL = (
        "/v2/programmes/search/playable?q={search}",
        False,
    )
    PODCASTS = ("/v2/experience/inline/speech", False)
    MUSIC = ("/v2/experience/inline/music", False)
    NEWS = (
        "/v2/experience/inline/container/urn:bbc:radio:category:news",
        False,
    )
    AUDIOBOOKS = "", False
    POPULAR_AUDIOBOOKS = (
        "/v2/programmes/playable?category=audiobooks&sort=popular&experience=domestic",
        False,
    )
    # Authenticated URLs
    EXPERIENCE_MENU = ("/v2/my/experience/inline/listen", True)
    PLAYS = ("/v2/my/programmes/plays", True)
    RECOMMENDATIONS = (
        "/v2/my/programmes/recommendations/playable",
        True,
    )
    MUSIC_RECOMMENDATIONS = (
        "/v2/my/programmes/recommendations/music-mixes/playable",
        True,
    )
    LATEST = ("/v2/my/programmes/follows/playable", True)
    SUBSCRIBED = ("/v2/my/programmes/follows", True)
    BOOKMARKS = ("/v2/my/programmes/favourites/playable", True)
    CONTINUE = ("/v2/my/programmes/plays/playable", True)
    PID_PLAYABLE = ("/v2/my/programmes/{pid}/playable", True)
