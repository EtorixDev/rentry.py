from __future__ import annotations

from typing import Any


class RentryError(Exception):
    """Base exception for rentry.py."""


class InvalidSlugError(RentryError, ValueError):
    """Exception for when a page slug or URL is invalid."""


class InvalidEditCodeError(RentryError, ValueError):
    """Exception for when an edit or modify code is invalid."""


class InvalidMetadataError(RentryError, ValueError):
    """Exception for when metadata is invalid."""


class TransportError(RentryError):
    """Exception for when a request cannot reach Rentry."""


class ProtocolError(RentryError):
    """Exception for when a response does not follow the Rentry API protocol."""


class APIError(RentryError):
    """---
    Exception for when the Rentry API rejects a request.

    #### Attributes
    - status: `str` — The Rentry application status.
    - content: `Any` — The response content supplied by Rentry.
    - errors: `Any` — The validation errors supplied by Rentry.
    """

    def __init__(self, status: str, content: Any = None, errors: Any = None) -> None:
        self.status = status
        self.content = content
        self.errors = errors
        detail = errors if errors not in (None, "") else content
        message = f"Rentry API returned status {status}"

        if detail not in (None, ""):
            message = f"{message}: {detail}"

        super().__init__(message)


class ValidationError(APIError):
    """Exception for when the Rentry API rejects invalid request data."""


class AccessDeniedError(APIError):
    """Exception for when the supplied code does not grant access."""


class NotFoundError(APIError):
    """Exception for when a requested page does not exist."""


class MethodNotAllowedError(APIError):
    """Exception for when an endpoint does not accept a request method."""


class RateLimitError(APIError):
    """Exception for when the Rentry rate limit is exceeded."""


class ServiceUnavailableError(APIError):
    """Exception for when Rentry is temporarily unavailable."""
