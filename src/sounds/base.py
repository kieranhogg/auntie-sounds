import logging
from abc import ABC

import aiohttp
from pytz import tzinfo

logger = logging.getLogger(__name__)


class Base(ABC):
    """Base class for other classes to inherit shared session and state"""

    DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10)

    def __init__(
        self,
        session: aiohttp.ClientSession,
        timezone: tzinfo | None = None,
        timeout: aiohttp.ClientTimeout | None = None,
        mock_session: bool = False,
        *args,
        **kwargs,
    ):
        self._session = session
        self.timezone = timezone
        self._timeout = timeout or self.DEFAULT_TIMEOUT
        self.mock_session = mock_session
