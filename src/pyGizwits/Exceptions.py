class GizwitsException(Exception):
    """An exception returned via the API."""


class GizwitsOfflineException(GizwitsException):
    """Device is offline."""


class GizwitsDeviceNotBound(GizwitsException):
    """Device is not bound to this user."""


class GizwitsAuthException(GizwitsException):
    """An authentication error."""


class GizwitsTokenInvalidException(GizwitsAuthException):
    """Auth token is invalid or expired."""


class GizwitsUserDoesNotExistException(GizwitsAuthException):
    """User does not exist."""


class GizwitsIncorrectPasswordException(GizwitsAuthException):
    """Password is incorrect."""
