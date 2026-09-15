from enum import Enum, unique


@unique
class URLs(Enum):
    login_required: bool

    def __new__(cls, value, login_required):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.login_required = login_required
        return obj

    LOGIN_START = (
        "https://session.bbc.co.uk/session?ptrt=https%3A%2F%2Fwww.bbc.co.uk%2Fsounds",
        False,
        # resolves to: https://account.bbc.com/auth/identifier/signin?realm=%2F&clientId=Account&context=iplayerradio&ptrt=https%3A%2F%2Fwww.bbc.co.uk%2Fsounds&userOrigin=sounds&mvtUserId=<hash>&isCasso=false&action=sign-in&sequenceId=&redirectUri=https%3A%2F%2Fsession.bbc.co.uk%2Fsession%2Fcallback%3Frealm%3D%2F&service=IdSignInService&nonce=<nonce>
    )
    LOGIN_START_I18N = (
        "https://account.bbc.com/auth?realm=%2F&clientId=Account&ptrt=https%3A%2F%2Fwww.bbc.com%2F&userOrigin=BBCS_BBC&purpose=free&isCasso=false&action=sign-in&redirectUri=https%3A%2F%2Fsession.bbc.com%2Fsession%2Fcallback%3Frealm%3D%2F&service=IdSignInService",
        False,
    )
    LOGIN_BASE = ("https://account.bbc.com", False)
    COOKIE_BASE = ("https://www.bbc.co.uk", False)
    COOKIE_BASE_I18N = ("https://www.bbc.com", False)
    JWT = ("https://rms.api.bbc.co.uk/v2/sign/token/{station_id}", False)
    INTL_JWT = ("https://web-cdn.api.bbci.co.uk/xd/media-token?{id_type}={id}", False)
    USER_INFO = ("https://www.bbc.co.uk/userinfo", False)

    # Streaming URLs
    MEDIASET = (
        "https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/mediaset/pc/vpid/{station_id}/format/json?jwt_auth={jwt_auth_token}",
        False,
    )
    EPISODE_MEDIASET = (
        "https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/mediaset/pc/vpid/{episode_id}",
        False,
    )

    # Station URLs
    NETWORKS_LIST = ("https://rms.api.bbc.co.uk/radio/networks.json", False)
    STATIONS = ("https://rms.api.bbc.co.uk/v2/experience/inline/stations", False)
    LIVE_STATION_DETAILS = (
        "https://rms.api.bbc.co.uk/v2/experience/inline/play/{station_id}",
        False,
    )
    STATION_DETAILS = ("https://rms.api.bbc.co.uk/v2/networks/{station_id}", False)
    STATION_PLAYABLE_DETAILS = (
        "https://rms.api.bbc.co.uk/v2/networks/{station_id}/playable",
        False,
    )
    LIVE_STATION = ("https://www.bbc.co.uk/sounds/play/live:{station_id}", False)
    NOW_PLAYING = (
        "https://rms.api.bbc.co.uk/v2/services/{station_id}/segments/latest?limit={limit}",
        False,
    )
    SCHEDULE = (
        "https://rms.api.bbc.co.uk/v2/experience/inline/schedules/{station_id}",
        False,
    )
    SCHEDULE_DATE = (
        "https://rms.api.bbc.co.uk/v2/experience/inline/schedules/{station_id}/{date}",
        False,
    )
    SEGMENTS = ("https://rms.api.bbc.co.uk/v2/versions/{vpid}/segments", False)

    # Episodes, programmes, series etc.
    PLAYABLE_ITEMS_CONTAINER = (
        "https://rms.api.bbc.co.uk/v2/programmes/playable?container={pid}&sort=sequential",
        False,
    )
    CATEGORY_LATEST = (
        "https://rms.api.bbc.co.uk/v2/programmes/playable?category={category}&sort=-release_date&experience=domestic",
        False,
    )
    CATEGORY_POPULAR = (
        "https://rms.api.bbc.co.uk/v2/programmes/playable?category={category}&sort=popular&experience=domestic",
        False,
    )
    BROADCAST = ("https://rms.api.bbc.co.uk/v2/broadcasts/{pid}", False)
    # Despite the name, this returns a single programme
    PROGRAMME_FROM_PID = ("https://rms.api.bbc.co.uk/v2/programmes/{pid}", False)
    PROGRAMME_FROM_PID_PLAYABLE = (
        "https://rms.api.bbc.co.uk/v2/programmes/{pid}/playable",
        False,
    )
    CONTAINER_URL = (
        "https://rms.api.bbc.co.uk/v2/experience/inline/container/{urn}",
        False,
    )

    # This endpoint gets extra details from a pid such as vpid and parent pid
    PID_DETAILS = ("https://www.bbc.co.uk/programmes/{pid}/playlist.json", False)
    COLLECTIONS_FULL = (
        "https://rms.api.bbc.co.uk/v2/collections/{pid}/members/container?experience=domestic&offset={offset}&limit={limit}",
        False,
    )
    COLLECTIONS = (
        "https://rms.api.bbc.co.uk/v2/collections/{pid}/members/container?experience=domestic",
        False,
    )
    CURATIONS = (
        "https://rms.api.bbc.co.uk/v2/curations/{pid}/members/playable?experience=domestic",
        False,
    )

    # Menu, search, etc.
    SEARCH_URL = (
        "https://rms.api.bbc.co.uk/v2/experience/inline/search?q={search}",
        False,
    )
    SHOW_SEARCH_URL = (
        "https://rms.api.bbc.co.uk/v2/programmes/search/container?q={search}",
        False,
    )
    EPISODE_SEARCH_URL = (
        "https://rms.api.bbc.co.uk/v2/programmes/search/playable?q={search}",
        False,
    )
    PODCASTS = ("https://rms.api.bbc.co.uk/v2/experience/inline/speech", False)
    MUSIC = ("https://rms.api.bbc.co.uk/v2/experience/inline/music", False)
    NEWS = (
        "https://rms.api.bbc.co.uk/v2/experience/inline/container/urn:bbc:radio:category:news",
        False,
    )

    # Authenticated URLs
    EXPERIENCE_MENU = ("https://rms.api.bbc.co.uk/v2/my/experience/inline/listen", True)
    RENEW_SESSION = (
        "https://session.bbc.co.uk/session?context=iplayerradio&userOrigin=sounds",
        True,
    )
    PLAYS = ("https://rms.api.bbc.co.uk/v2/my/programmes/plays", True)
    RECOMMENDATIONS = (
        "https://rms.api.bbc.co.uk/v2/my/programmes/recommendations/playable",
        True,
    )
    MUSIC_RECOMMENDATIONS = (
        "https://rms.api.bbc.co.uk/v2/my/programmes/recommendations/music-mixes/playable",
        True,
    )
    LATEST = ("https://rms.api.bbc.co.uk/v2/my/programmes/follows/playable", True)
    SUBSCRIBED = ("https://rms.api.bbc.co.uk/v2/my/programmes/follows", True)
    BOOKMARKS = ("https://rms.api.bbc.co.uk/v2/my/programmes/favourites/playable", True)
    CONTINUE = ("https://rms.api.bbc.co.uk/v2/my/programmes/plays/playable", True)
    PID_PLAYABLE = ("https://rms.api.bbc.co.uk/v2/my/programmes/{pid}/playable", True)

    # The only difference between this and the unauthenticated endpoint is the uris
    # CONTAINER_URL = ("https://rms.api.bbc.co.uk/v2/my/experience/inline/container/{urn}", True)
