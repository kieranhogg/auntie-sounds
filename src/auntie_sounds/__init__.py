from auntie_sounds.client import SoundsClient
from auntie_sounds.constants import FEATURE_FLAGS, SCHEDULE_TIMEZONE, VERBOSE_LOG_LEVEL
from auntie_sounds.exceptions import SoundsException

__all__ = [
    "FEATURE_FLAGS",
    "SCHEDULE_TIMEZONE",
    "VERBOSE_LOG_LEVEL",
    "SoundsClient",
    "SoundsException",
]


def parse(json_dict: dict):
    """Parse an API response into an auntie-sounds output without the client."""
    from auntie_sounds.model_factory import ModelFactory

    return ModelFactory().parse_object(json_dict)
