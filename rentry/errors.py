class RentryError(Exception):
    """Base class for rentry exceptions."""


class RentryInvalidResponseError(RentryError):
    """Raised when the response from the rentry API is invalid."""

    def __init__(self, message: str = "") -> None:
        default_message = "The response from the rentry API was invalid for an unknown reason."
        message = message or default_message
        super().__init__(message)


class RentryInvalidCSRFError(RentryError):
    """Raised when the CSRF token is invalid."""

    def __init__(self, message: str = "") -> None:
        default_message = "The CSRF token is invalid."
        message = message or default_message
        super().__init__(message)


class RentryInvalidAuthTokenError(RentryError):
    """Raised when the auth_token is invalid."""

    def __init__(self, message: str = "") -> None:
        default_message = "The auth_token is invalid."
        message = message or default_message
        super().__init__(message)


class RentryInvalidEditCodeError(RentryError):
    """Raised when the edit code is invalid."""

    def __init__(self, message: str = "") -> None:
        default_message = "The edit code is invalid."
        message = message or default_message
        super().__init__(message)


class RentryInvalidPageURLError(RentryError):
    """Raised when the page URL is invalid."""

    def __init__(self, message: str = "") -> None:
        default_message = "The page URL is invalid."
        message = message or default_message
        super().__init__(message)


class RentryInvalidMetadataError(RentryError):
    """Raised when the metadata is invalid."""

    def __init__(self, message: str = "") -> None:
        default_message = "The metadata is invalid."
        message = message or default_message
        super().__init__(message)


class RentryInvalidContentLengthError(RentryError):
    """Raised when the content is an invalid length."""

    def __init__(self, message: str = "") -> None:
        default_message = "The content is an invalid length."
        message = message or default_message
        super().__init__(message)


class RentryExistingPageError(RentryError):
    """Raised when the page already exists."""

    def __init__(self, message: str = "") -> None:
        default_message = "That page is already in use."
        message = message or default_message
        super().__init__(message)


class RentryNonExistentPageError(RentryError):
    """Raised when the page does not exist."""

    def __init__(self, message: str = "") -> None:
        default_message = "That page does not exist."
        message = message or default_message
        super().__init__(message)


