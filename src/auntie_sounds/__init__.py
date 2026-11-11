from auntie_sounds.client import SoundsClient
from auntie_sounds.constants import SCHEDULE_TIMEZONE, VERBOSE_LOG_LEVEL
from auntie_sounds.exceptions import (
    APIResponseError,
    ConfigurationError,
    CredentialsRejectedError,
    DateOutOfRangeError,
    InvalidArgumentsError,
    InvalidFormatError,
    LoginFailedError,
    MultipleObjectsFound,
    NetworkError,
    NotExpectedTypeError,
    NotFoundError,
    NotStartedError,
    ParserError,
    SoundsException,
    SoundsHttpException,
    UnauthorisedError,
)

__all__ = [
    "SCHEDULE_TIMEZONE",
    "VERBOSE_LOG_LEVEL",
    "APIResponseError",
    "ConfigurationError",
    "CredentialsRejectedError",
    "DateOutOfRangeError",
    "InvalidArgumentsError",
    "InvalidFormatError",
    "LoginFailedError",
    "MultipleObjectsFound",
    "NetworkError",
    "NotExpectedTypeError",
    "NotFoundError",
    "NotStartedError",
    "ParserError",
    "SoundsClient",
    "SoundsException",
    "SoundsHttpException",
    "UnauthorisedError",
    "parse",
]


def parse(json_dict: dict):
    """Parse an API response into an auntie-sounds output without the client."""
    from auntie_sounds.model_factory import ModelFactory

    return ModelFactory().parse_object(json_dict)
