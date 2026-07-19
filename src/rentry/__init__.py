"""A Python client for Rentry."""

from importlib.metadata import version

from .client import DEFAULT_DOMAIN, DEFAULT_USER_AGENT, UNSET, AsyncClient, Client, RentryDomain, UnsetType
from .exceptions import (
    AccessDeniedError,
    APIError,
    InvalidEditCodeError,
    InvalidMetadataError,
    InvalidSlugError,
    MethodNotAllowedError,
    NotFoundError,
    ProtocolError,
    RateLimitError,
    RentryError,
    ServiceUnavailableError,
    TransportError,
    ValidationError,
)
from .metadata import Metadata, MetadataInput, MetadataPatch, MetadataPatchValue, MetadataValue
from .models import CreatedPage, Page

__version__ = version("rentry.py")

__all__ = [
    "DEFAULT_DOMAIN",
    "DEFAULT_USER_AGENT",
    "UNSET",
    "APIError",
    "AccessDeniedError",
    "AsyncClient",
    "Client",
    "CreatedPage",
    "InvalidEditCodeError",
    "InvalidMetadataError",
    "InvalidSlugError",
    "Metadata",
    "MetadataInput",
    "MetadataPatch",
    "MetadataPatchValue",
    "MetadataValue",
    "MethodNotAllowedError",
    "NotFoundError",
    "Page",
    "ProtocolError",
    "RateLimitError",
    "RentryDomain",
    "RentryError",
    "ServiceUnavailableError",
    "TransportError",
    "UnsetType",
    "ValidationError",
    "__version__",
]
