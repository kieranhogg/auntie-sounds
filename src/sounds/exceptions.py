class SoundsException(Exception):
    """Generic exception for the module"""


class LoginFailedError(SoundsException):
    pass


class NetworkError(SoundsException):
    pass


class APIResponseError(SoundsException):
    pass


class InvalidFormatError(SoundsException):
    pass
