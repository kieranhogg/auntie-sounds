from enum import Enum, StrEnum, unique


@unique
class URLs(StrEnum):
    """URLs not in the usual endpoint format."""

    # resolves to: https://account.bbc.com/auth/identifier/signin?realm=%2F&clientId=Account&context=iplayerradio&ptrt=https%3A%2F%2Fwww.bbc.co.uk%2Fsounds&userOrigin=sounds&mvtUserId=<hash>&isCasso=false&action=sign-in&sequenceId=&redirectUri=https%3A%2F%2Fsession.bbc.co.uk%2Fsession%2Fcallback%3Frealm%3D%2F&service=IdSignInService&nonce=<nonce>

    JWT = "/v2/sign/token/{id}"
    INTL_JWT = "https://web-cdn.api.bbci.co.uk/xd/media-token"  # ?{id_type}={id}"
    USER_INFO = "https://www.bbc.co.uk/userinfo"

    # Streaming URLs
    MEDIASET = "https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/mediaset/pc/vpid/{id}/format/json"  # ?jwt_auth={jwt_auth_token}"
    I18N_MEDIASET = "https://open.live.bbc.co.uk/mediaselector/6/select/version/3.0/mediaset/pc/cvid/urn:bbc:pips:pid:{id}/format/json"

    """
    Takes: a vpid.
    Returns: stream connections.
    Used by: get_episode_stream.
    """
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
        "/v2/networks",  # ?limit={limit}
        False,
        "NetworksResponse",
        None,
    )
    NETWORK_SERVICES = (
        "/v2/networks/services",  # ?limit={limit}
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
    CURRENT_PROGRAMME = (
        "/v2/broadcasts/latest",  # ?on_air=now | service={service_id}&sort=-start_at
        False,
    )
    BROADCAST_SCHEDULE = ("/v2/broadcasts/schedules/{service_id}/{date}", False)
    LATEST_TRACKS = ("/v2/services/{station_id}/tracks/latest/playable", False)
    NOW_PLAYING = (
        "/v2/services/{service_id}/segments/latest",  # ?limit={limit}
        False,
    )
    """
    Takes: a service id.
    Returns: an experience made of modules. Some have uris.polling, a template
        to refresh them with and wait_before_poll_sec, how long to leave
        between requests. live_play_area holds the on-air programme then the
        next few. recent_tracks only has a polling uri on stations with tracks.
    Used by: ScheduleService.polling.
    """
    PLAY_EXPERIENCE = (
        "/v2/experience/inline/play/{service_id}",
        False,
        "ExperienceResponse",
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

    ####### Episodes, programmes, series etc. ##########################################

    """
    Takes: a brand or series pid.
    Returns: a list of container_items
    Useful fields: id, urn, and uris[latest], which links to the episode listing.
    Used by: get_podcast.
    """
    CONTAINER_FROM_PIDS = ("/v2/programmes/container/{pids}", False)

    """
    Takes: ?parent={brand pid}&type=series
    Returns: the seasons as container_items, in pid order rather than date order.
        Includes seasons with nothing available (e.g. omnibus editions).
        Empty for a brand without seasons. Rejects sort=sequential with a 400.
    Used by: get_podcast.
    """
    SERIES_CONTAINER = ("/v2/programmes/container", False)
    SERIES_EPISODES = ("/v2/programmes/playable/{pids}", False)

    """
    Takes: ?container={brand or series pid}&sort=sequential
    Returns: playable_items. Each one's container is the top-level brand, even
        when listing by series, and its "latest" uri points at its season.
        sort=sequential groups the episodes by season. ?parent= with
        sort=sequential is a 400.
    Used by: get_pid_container.
    """
    PLAYABLE_ITEMS_CONTAINER = (
        "/v2/programmes/playable",  # ?container={pid}&sort=sequential | sort=popular | sort=-release_date
        False,
    )
    BROADCAST = ("/v2/broadcasts/{pid}", False)

    """
    Takes: an episode pid.
    Returns: a Programmes response with total: 1 and the episode in data[0],
        for radio and podcast episodes alike. ancestors holds the brand and
        the series, availability.id is the vpid, and the artwork is in images.
        There's no container, image_url or duration.
        An unknown pid is a 200 with total: 0.
    Used by: the _get_programme helpers.
    """
    PROGRAMME_FROM_PID = ("/v2/programmes/{pid}", False)
    """
    Takes: an episode pid.
    Returns: a single playable_item. container is the top-level brand, the
        "latest" uri points at the season and id is the vpid.
        An unknown pid is a 404.
    Used by: get_by_pid.
    """
    PROGRAMME_FROM_PID_PLAYABLE = (
        "/v2/programmes/{pid}/playable",
        False,
    )

    """
    Takes: a container urn.
    Returns: a page with two parts: a header module holding the brand, and a 
        container_list holding all the episodes as playable_items
    Used by: get_container and get_radio_series.
    """
    URN_CONTAINER = (
        "/v2/experience/inline/container/{urn}",
        False,
    )

    """
    Takes: an episode pid.
    Returns: the vpid and statsObject.parentPIDType.
    Used by: the heartbeat.
    """
    PID_DETAILS = ("https://www.bbc.co.uk/programmes/{pid}/playlist.json", False)
    COLLECTIONS = (
        "/v2/collections/{pid}/members/container",
        False,
    )
    CURATIONS = (
        "/v2/curations/{pid}/members/playable",
        False,
    )
    # Options: focus feel_good_tunes dance fresh_new_music greatest_hits
    TAGGED = ("/v2/tagged/{tag}/playable", False)
    # Menu, search, etc.
    SEARCH_URL = (
        "/v2/experience/inline/search",
        False,
    )
    SHOW_SEARCH_URL = (
        "/v2/programmes/search/container",
        False,
    )
    EPISODE_SEARCH_URL = (
        "/v2/programmes/search/playable",
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
        "/v2/programmes/playable?category=audiobooks&sort=popular",
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
    # Same shapes as PROGRAMME_FROM_PID_PLAYABLE and PLAYABLE_ITEMS_CONTAINER,
    # plus progress, which is None for anything not yet played
    PID_PLAYABLE = ("/v2/my/programmes/{pid}/playable", True)
    MY_PLAYABLE_ITEMS_CONTAINER = ("/v2/my/programmes/playable", True)
