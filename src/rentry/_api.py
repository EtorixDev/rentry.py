from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, cast

from .exceptions import (
    AccessDeniedError,
    APIError,
    MethodNotAllowedError,
    NotFoundError,
    ProtocolError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)


class ResponseLike(Protocol):
    status_code: int
    text: str

    def json(self) -> Any: ...


_ERROR_TYPES: dict[str, type[APIError]] = {
    "400": ValidationError,
    "403": AccessDeniedError,
    "404": NotFoundError,
    "405": MethodNotAllowedError,
    "429": RateLimitError,
    "503": ServiceUnavailableError,
}


def parse_api_response(response: ResponseLike) -> Mapping[str, Any]:
    """Parse a Rentry API response."""

    if response.status_code != 200:
        raise ProtocolError(f"Rentry returned unexpected HTTP status {response.status_code}.")

    try:
        raw_payload = response.json()
    except (TypeError, ValueError) as exc:
        raise ProtocolError("Rentry returned a response that is not valid JSON.") from exc

    if not isinstance(raw_payload, dict):
        raise ProtocolError("Rentry returned a JSON response that is not an object.")

    payload = cast(dict[str, Any], raw_payload)
    raw_status = payload.get("status")

    if not isinstance(raw_status, str | int):
        raise ProtocolError("Rentry returned a JSON response without an application status.")

    status = str(raw_status)

    if status == "200":
        return payload

    error_type = _ERROR_TYPES.get(status, APIError)

    raise error_type(status, payload.get("content"), payload.get("errors"))
