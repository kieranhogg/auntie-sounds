from enum import Enum
from typing import Final


class URLs:
    LOGIN_START = "https://session.bbc.co.uk/session?ptrt=https%3A%2F%2Fwww.bbc.co.uk%2Fsounds&context=iplayerradio&userOrigin=sounds"
    LOGIN_BASE = "https://account.bbc.com"
    COOKIE_URL = "https://www.bbc.co.uk"
    MEDIASET_URL = "https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/mediaset/pc/vpid/{station_id}/format/json?jwt_auth={jwt_auth_token}"
    EPISODE_MEDIASET = "https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/mediaset/pc/vpid/{self.verpid}"
    STATIONS_URL = "https://rms.api.bbc.co.uk/v2/experience/inline/stations"
    LIVE_STATION_URL = "https://www.bbc.co.uk/sounds/play/live:{station_id}"
    NOW_PLAYING_URL = "https://rms.api.bbc.co.uk/v2/services/{station_id}/segments/latest?limit={limit}"
    JWT_URL = "https://rms.api.bbc.co.uk/v2/sign/token/{station_id}"
    SCHEDULE_URL = (
        "https://rms.api.bbc.co.uk/v2/experience/inline/schedules/{station_id}"
    )
    SEGMENTS = "https://rms.api.bbc.co.uk/v2/versions/{pid}/segments"
    PID_LIVE = "https://rms.api.bbc.co.uk/v2/broadcasts/{pid}"
    PID_PLAYABLE = "https://rms.api.bbc.co.uk/v2/programmes/{pid}/playable"


# This is the ID of the cookie we use to check we have a valid session
COOKIE_ID = "ckns_id"


class ImageType(Enum):
    """An enum for valid image types for recipes"""

    COLOUR = "colour"
    COLOUR_DEFAULT = "colour_default"
    BACKGROUND = "background"
    BLOCKS_COLOUR = "blocks_colour"
    BLOCKS_COLOUR_BLACK = "blocks_colour_black"
    BLOCKS_COLOUR_WHITE = "blocks_colour_white"


VERBOSE_LOG_LEVEL: Final[int] = 5
