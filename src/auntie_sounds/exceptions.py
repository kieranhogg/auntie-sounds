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
    """Generic login failed error."""


class CredentialsRejectedError(LoginFailedError):
    """The API rejected the username or password combination."""


class NetworkError(SoundsHttpException):
    """Generic network error."""


class APIResponseError(SoundsHttpException):
    """The API response was not as expected."""
    def __init__(self, message: str | None = None, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class InvalidFormatError(SoundsException):
    """The parameter, or parameters, were given in an invalid format."""


class UnauthorisedError(SoundsHttpException):
    """The endpoint requires authentication, and the current user is not authenticated."""


class InvalidArgumentsError(SoundsException):
    """Invalid arguments were supplied."""


class NotFoundError(SoundsHttpException):
    """The requested resource was not found."""


class NotExpectedTypeError(NotFoundError):
    """A unexpected type error."""


class MultipleObjectsFound(SoundsException):
    """More than one object was found when looking for exactly one."""


class ParserError(SoundsException):
    """Generic parser error when interpreting the API response."""


class ConfigurationError(SoundsException):
    """Raised when a test is not configured correctly."""


class DateOutOfRangeError(APIResponseError):
    """Schedule requested outside the window the API serves."""


class NotStartedError(SoundsException):
    """SoundsClient services accessed before .start() was called."""
