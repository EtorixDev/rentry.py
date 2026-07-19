from __future__ import annotations

import pytest

from rentry import (
    AccessDeniedError,
    APIError,
    MethodNotAllowedError,
    NotFoundError,
    ProtocolError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)
from rentry._api import parse_api_response

from .conftest import FakeResponse


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        ("400", ValidationError),
        ("403", AccessDeniedError),
        ("404", NotFoundError),
        ("405", MethodNotAllowedError),
        ("429", RateLimitError),
        ("503", ServiceUnavailableError),
        ("599", APIError),
    ],
)
def test_application_statuses_have_structured_exceptions(status: str, error_type: type[APIError]) -> None:
    with pytest.raises(error_type) as raised:
        parse_api_response(FakeResponse({"status": status, "content": "failed", "errors": {"url": ["bad"]}}))

    assert raised.value.status == status
    assert raised.value.content == "failed"
    assert raised.value.errors == {"url": ["bad"]}


@pytest.mark.parametrize(
    "response",
    [
        FakeResponse({}, status_code=500),
        FakeResponse(ValueError("not json")),
        FakeResponse([]),
        FakeResponse({"content": "missing status"}),
    ],
)
def test_malformed_responses_raise_protocol_errors(response: FakeResponse) -> None:
    with pytest.raises(ProtocolError):
        parse_api_response(response)


@pytest.mark.parametrize(
    ("content", "errors", "expected"),
    [("content detail", None, "content detail"), (None, None, "Rentry API returned status 599")],
)
def test_api_error_messages_fall_back_to_content(
    content: object,
    errors: object,
    expected: str,
) -> None:
    with pytest.raises(APIError) as raised:
        parse_api_response(FakeResponse({"status": "599", "content": content, "errors": errors}))

    assert expected in str(raised.value)
