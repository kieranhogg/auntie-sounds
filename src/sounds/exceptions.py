class SoundsException(Exception):
    """Generic exception for the module"""


class LoginFailedException(SoundsException):
    pass


class NetworkErrorException(SoundsException):
    pass


class APIResponseException(SoundsException):
    pass
