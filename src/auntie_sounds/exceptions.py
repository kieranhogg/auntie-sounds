class SoundsException(Exception):
    """Generic exception for the module"""

    def __init__(self, message: str | None = None):
        self.message = message
        super().__init__(self.message)


class SoundsHttpException(SoundsException):
    """Anything that comes from a HTTP request."""

    def __init__(self, message: str | None = None, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class LoginFailedError(SoundsException):
    pass


class CredentialsRejectedError(LoginFailedError):
    """BBC rejected the username or password; retrying won't help."""


class NetworkError(SoundsHttpException):
    pass


class APIResponseError(SoundsHttpException):
    def __init__(self, message: str | None = None, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class InvalidFormatError(SoundsException):
    pass


class UnauthorisedError(SoundsHttpException):
    pass


class InvalidArgumentsError(SoundsException):
    pass


class NotFoundError(SoundsHttpException):
    pass


class MultipleObjectsFound(SoundsException):
    pass


class ParserError(SoundsException):
    pass


class ConfigurationError(SoundsException):
    pass


class DateOutOfRangeError(APIResponseError):
    """Schedule requested outside the window the API serves."""
