from enum import Enum, StrEnum, unique


@unique
class URLs(StrEnum):
    """URLs not in the usual endpoint format."""

    # resolves to: https://account.bbc.com/auth/identifier/signin?realm=%2F&clientId=Account&context=iplayerradio&ptrt=https%3A%2F%2Fwww.bbc.co.uk%2Fsounds&userOrigin=sounds&mvtUserId=<hash>&isCasso=false&action=sign-in&sequenceId=&redirectUri=https%3A%2F%2Fsession.bbc.co.uk%2Fsession%2Fcallback%3Frealm%3D%2F&service=IdSignInService&nonce=<nonce>

    JWT = "/v2/sign/token/{id}"
    USER_INFO = "https://www.bbc.co.uk/userinfo"

    # Streaming URLs
    MEDIASET = "https://open.live.bbc.co.uk/mediaselector/6/select/version/3.0/mediaset/pc/cvid/urn:bbc:pips:pid:{id}/format/json"
    """
    Takes: an id, which is the service id for a live station or the vpid for an episode.
    Returns: media variants by bitrate, each with a list of stream connections.
    Auth: domestic live stations need a JWT from JWT, sent as a Bearer header.
        International stations and episodes need none.
    Used by: get_live_streams and get_episode_streams.
    """

    # Auth URLs
    RENEW_SESSION = (
        "https://session.bbc.co.uk/session?context=iplayerradio&userOrigin=sounds"
    )
    LOGIN_START = (
        "https://session.bbc.co.uk/session?ptrt=https%3A%2F%2Fwww.bbc.co.uk%2Fsounds"
    )
    LOGIN_BASE = "https://account.bbc.com"
    COOKIE_BASE = "https://www.bbc.co.uk"


@unique
class Endpoints(Enum):
    login_required: bool
    response_type: str | None
    return_type: str | None

    def __new__(cls, value, login_required=False, response_type=None, return_type=None):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.login_required = login_required
        obj.response_type = response_type
        obj.return_type = return_type
        return obj

    # Station & Networks
    NETWORKS_DETAILED = "/radio/networks.json"
    NETWORKS = "/v2/networks"  # ?limit={limit})
    NETWORK_SERVICES = "/v2/networks/services"  # ?limit={limit})
    NETWORKS_PLAYABLE = "/v2/networks/playable"
    NETWORK_DETAILS = "/v2/networks/{network_id}"
    NETWORK_PROMOS = "/v2/networks/{network_id}/promos/display"
    NETWORK_PROMOS_PLAYABLE = "/v2/networks/{network_id}/promos/playable"
    NETWORK_PLAYABLE_DETAILS = "/v2/networks/{network_id}/playable"

    STATIONS = "/v2/experience/inline/stations"
    STATION_DETAILS = "/v2/networks/{station_id}"
    STATION_PLAYABLE_DETAILS = "/v2/networks/{station_id}/playable"

    # Segments & Schedules
    BROADCASTS = "/v2/broadcasts?service={service_id}&sort=-start_at"
    CURRENT_PROGRAMME = (
        "/v2/broadcasts/latest"  # ?on_air=now | service={service_id}&sort=-start_at)
    )
    BROADCAST_SCHEDULE = "/v2/broadcasts/schedules/{service_id}/{date}"
    LATEST_TRACKS = "/v2/services/{station_id}/tracks/latest/playable"
    NOW_PLAYING = "/v2/services/{service_id}/segments/latest"  # ?limit={limit})
    PLAY_EXPERIENCE = "/v2/experience/inline/play/{service_id}"

    """
    Takes: a service id.
    Returns: an experience made of modules. Some have uris.polling, a template
        to refresh them with and wait_before_poll_sec, how long to leave
        between requests. live_play_area holds the on-air programme then the
        next few. recent_tracks only has a polling uri on stations with tracks.
    Used by: ScheduleService.polling.
    """
    SCHEDULE = "/v2/experience/inline/schedules/{service_id}"
    SCHEDULE_DATE = "/v2/experience/inline/schedules/{service_id}/{date}"
    SEGMENTS = "/v2/versions/{vpid}/segments"

    ####### Episodes, programmes, series etc. ##########################################

    CONTAINER_FROM_PIDS = "/v2/programmes/container/{pids}"

    """
    Takes: a brand or series pid.
    Returns: a list of container_items
    Useful fields: id, urn, and uris[latest], which links to the episode listing.
    Used by: get_podcast.
    """
    SERIES_CONTAINER = "/v2/programmes/container"
    """
    Takes: ?parent={brand pid}&type=series
    Returns: the seasons as container_items, in pid order rather than date order.
        Includes seasons with nothing available (e.g. omnibus editions).
        Empty for a brand without seasons. Rejects sort=sequential with a 400.
    Used by: get_podcast.
    """
    SERIES_EPISODES = "/v2/programmes/playable/{pids}"

    PLAYABLE_ITEMS_CONTAINER = (
        "/v2/programmes/playable",
    )  # ?container={pid}&sort=sequential | sort=popular | sort=-release_date)
    """
    Takes: ?container={brand or series pid}&sort=sequential
    Returns: playable_items. Each one's container is the top-level brand, even
        when listing by series, and its "latest" uri points at its season.
        sort=sequential groups the episodes by season. ?parent= with
        sort=sequential is a 400.
    Used by: get_pid_container.
    """
    BROADCAST = "/v2/broadcasts/{pid}"

    PROGRAMME_FROM_PID = "/v2/programmes/{pid}"
    """
    Takes: an episode pid.
    Returns: a Programmes response with total: 1 and the episode in data[0],
        for radio and podcast episodes alike. ancestors holds the brand and
        the series, availability.id is the vpid, and the artwork is in images.
        There's no container, image_url or duration.
        An unknown pid is a 200 with total: 0.
    Used by: the _get_programme helpers.
    """
    PROGRAMME_FROM_PID_PLAYABLE = "/v2/programmes/{pid}/playable"
    """
    Takes: an episode pid.
    Returns: a single playable_item. container is the top-level brand, the
        "latest" uri points at the season and id is the vpid.
        An unknown pid is a 404.
    Used by: get_by_pid.
    """

    URN_CONTAINER = "/v2/experience/inline/container/{urn}"
    """
    Takes: a container urn.
    Returns: a page with two parts: a header module holding the brand, and a 
        container_list holding all the episodes as playable_items
    Used by: get_container and get_radio_series.
    """

    PID_DETAILS = "https://www.bbc.co.uk/programmes/{pid}/playlist.json"
    """
    Takes: an episode pid.
    Returns: the vpid and statsObject.parentPIDType.
    Used by: the heartbeat.
    """
    COLLECTIONS = "/v2/collections/{pid}/members"  # ?experience=domestic)
    CURATIONS = "/v2/curations/{pid}/members/playable"
    # Options: focus feel_good_tunes dance fresh_new_music greatest_hits
    TAGGED = "/v2/tagged/{tag}/playable"

    ####### Menu, search, etc. #########################################################

    SEARCH_URL = "/v2/experience/inline/search"
    SHOW_SEARCH_URL = "/v2/programmes/search/container"
    EPISODE_SEARCH_URL = "/v2/programmes/search/playable"
    PODCASTS = "/v2/experience/inline/speech"
    MUSIC = "/v2/experience/inline/music"
    NEWS = "/v2/experience/inline/container/urn:bbc:radio:category:news"
    AUDIOBOOKS = "/v2/programmes/playable?category=audiobooks"
    POPULAR_AUDIOBOOKS = "/v2/programmes/playable?category=audiobooks&sort=popular"

    ####### Authenticated URLs #########################################################

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

    # The same as PROGRAMME_FROM_PID_PLAYABLE and PLAYABLE_ITEMS_CONTAINER,
    # plus progress, which is None for anything not yet played
    PID_PLAYABLE = ("/v2/my/programmes/{pid}/playable", True)
    MY_PLAYABLE_ITEMS_CONTAINER = ("/v2/my/programmes/playable", True)
