class SoundsAPIException(Exception):
    """Generic exception for the module"""


class LoginFailedException(SoundsAPIException):
    pass


class NetworkErrorException(SoundsAPIException):
    pass


class APIResponseException(SoundsAPIException):
    pass
