from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import cast

import pytest
from niquests.exceptions import RequestException

import rentry.client as client_module
from rentry import (
    AsyncClient,
    Client,
    CreatedPage,
    InvalidEditCodeError,
    InvalidSlugError,
    ProtocolError,
    RentryDomain,
    RentryError,
    TransportError,
)
from rentry.models import page_from_content

from .conftest import FakeAsyncSession, FakeResponse, FakeSession, session_for_async_client, session_for_client


def success(content: object = "OK", **fields: object) -> FakeResponse:
    return FakeResponse({"status": "200", "content": content, **fields})


def test_create_preserves_text_and_builds_a_secret_safe_model() -> None:
    session = FakeSession(
        success(
            url="https://rentry.co/MixedCase",
            url_short="MixedCase",
            edit_code="secret-edit-code",
        )
    )

    client = Client(session=session_for_client(session))
    page = client.create("  first line\nlast line\n", metadata={"PAGE_TITLE": "Title"}, slug="MixedCase")

    assert page == CreatedPage(
        slug="mixedcase",
        url="https://rentry.co/MixedCase",
        short_url="MixedCase",
        edit_code="secret-edit-code",
    )
    assert "secret-edit-code" not in repr(page)
    assert session.requests[0]["data"] == {
        "text": "  first line\nlast line\n",
        "metadata": '{"PAGE_TITLE":"Title"}',
        "url": "MixedCase",
    }
    assert session.requests[0]["headers"]["User-Agent"].startswith("rentry.py/1.0.0")


def test_create_accepts_success_fields_nested_in_content() -> None:
    session = FakeSession(success({"url": "https://rentry.co/example", "url_short": "example", "edit_code": "edit"}))
    page = Client(session=session_for_client(session)).create("")

    assert page.slug == "example"
    assert page.edit_code == "edit"


def test_page_urls_must_use_an_official_rentry_domain() -> None:
    session = FakeSession()

    with pytest.raises(InvalidSlugError):
        Client(session=session_for_client(session)).exists("https://rentry.example/example")

    assert not session.requests


def test_fetch_returns_an_immutable_snapshot_and_keeps_raw_text() -> None:
    session = FakeSession(
        success(
            {
                "url": "mixedcase",
                "url_case": "MixedCase",
                "views": 42,
                "pub_date": "2026-07-01T01:02:03",
                "activated_date": None,
                "edit_date": "2026-07-02T04:05:06Z",
                "modify_code_set": True,
                "text": "  exact\n",
                "metadata": {"PAGE_TITLE": "Example", "CONTENT_TEXT_COLOR": ["black", "white"]},
                "metadata_version": 1,
            }
        )
    )

    page = Client(session=session_for_client(session)).fetch("https://rentry.org/MixedCase", "m:shared")

    assert page.slug == "mixedcase"
    assert page.url == "https://rentry.co/MixedCase"
    assert page.text == "  exact\n"
    assert page.views == 42
    assert page.published_at == datetime(2026, 7, 1, 1, 2, 3)
    assert page.edited_at is not None and page.edited_at.tzinfo is not None
    assert page.metadata["CONTENT_TEXT_COLOR"] == ("black", "white")
    assert page.metadata_version == 1
    assert session.requests[0]["url"] == "https://rentry.co/api/fetch/mixedcase"

    with pytest.raises(TypeError):
        cast(dict[str, object], page.metadata)["PAGE_TITLE"] = "Changed"


def test_raw_access_code_is_scoped_to_the_raw_request() -> None:
    session = FakeSession(
        success("markdown"),
        success(
            {
                "text": "markdown",
                "metadata": {},
                "url": "example",
            }
        ),
    )

    client = Client(session=session_for_client(session))

    assert client.raw("example", access_code="raw-secret") == "markdown"

    client.fetch("example", "edit-secret")

    assert session.requests[0]["headers"]["rentry-auth"] == "raw-secret"
    assert "rentry-auth" not in session.requests[1]["headers"]


@pytest.mark.parametrize(("text", "expected"), [("True", True), ("False", False)])
def test_exists_uses_the_plain_text_endpoint(text: str, expected: bool) -> None:
    session = FakeSession(FakeResponse(status_code=200, text=text))

    assert Client(session=session_for_client(session)).exists("example") is expected
    assert session.requests[0]["url"] == "https://rentry.co/example/exists"


def test_exists_rejects_an_unexpected_protocol_response() -> None:
    session = FakeSession(FakeResponse(status_code=200, text="yes"))

    with pytest.raises(ProtocolError):
        Client(session=session_for_client(session)).exists("example")


def test_update_is_an_upsert_and_encodes_metadata_removal() -> None:
    session = FakeSession(success())
    client = Client(session=session_for_client(session))

    client.update(
        "example",
        "edit",
        text="",
        metadata={"PAGE_TITLE": None, "OPTION_DISABLE_VIEWS": True},
        new_modify_code=None,
        allow_secret_metadata_changes=True,
    )

    assert session.requests[0]["data"] == {
        "edit_code": "edit",
        "update_mode": "upsert",
        "text": "",
        "metadata": '{"PAGE_TITLE":"","OPTION_DISABLE_VIEWS":true}',
        "new_modify_code": "m:",
        "update_secret_metadata": "true",
    }


def test_update_rejects_rotation_with_a_modify_code_before_a_request() -> None:
    session = FakeSession()

    with pytest.raises(InvalidEditCodeError):
        Client(session=session_for_client(session)).update("example", "m:shared", new_slug="new-example")

    assert not session.requests


def test_update_requires_a_change() -> None:
    session = FakeSession()

    with pytest.raises(ValueError, match="at least one"):
        Client(session=session_for_client(session)).update("example", "edit")


def test_replace_always_sends_text_and_metadata() -> None:
    session = FakeSession(success())
    Client(session=session_for_client(session)).replace("example", "edit", text="", metadata={})

    assert session.requests[0]["data"] == {
        "edit_code": "edit",
        "update_mode": "replace",
        "text": "",
        "metadata": "{}",
    }


def test_delete_rejects_modify_codes() -> None:
    session = FakeSession()

    with pytest.raises(InvalidEditCodeError):
        Client(session=session_for_client(session)).delete("example", "m:shared")


def test_an_injected_session_is_not_closed() -> None:
    session = FakeSession()

    with Client(session=session_for_client(session)):
        pass

    assert session.close_calls == 0


def test_an_owned_session_is_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    monkeypatch.setattr(client_module.niquests, "Session", lambda: session)

    with Client():
        pass

    assert session.close_calls == 1


def test_closed_clients_fail_before_requesting() -> None:
    session = FakeSession()
    client = Client(session=session_for_client(session))
    client.close()

    with pytest.raises(RentryError, match="closed"):
        client.raw("example")


def test_transport_failures_are_wrapped() -> None:
    class FailingSession(FakeSession):
        def request(self, method: str, url: str, **kwargs: object) -> FakeResponse:
            raise RequestException("connection failed")

    with pytest.raises(TransportError, match="connection failed"):
        Client(session=session_for_client(FailingSession())).raw("example")


@pytest.mark.asyncio
async def test_async_client_matches_sync_payloads_and_closing_rules() -> None:
    session = FakeAsyncSession(success())

    async with AsyncClient(session=session_for_async_client(session)) as client:
        await client.update("example", "edit", metadata={"PAGE_TITLE": None})

    assert session.requests[0]["data"] == {
        "edit_code": "edit",
        "update_mode": "upsert",
        "metadata": '{"PAGE_TITLE":""}',
    }
    assert session.close_calls == 0


@pytest.mark.asyncio
async def test_async_client_exercises_the_complete_public_transport_surface() -> None:
    session = FakeAsyncSession(
        success(url="https://rentry.co/MixedCase", url_short="MixedCase", edit_code="edit"),
        success({"url": "mixedcase", "url_case": "MixedCase", "text": "markdown", "metadata": {}}),
        FakeResponse(status_code=200, text="True"),
        success("markdown"),
        success(),
        success(),
    )

    client = AsyncClient(session=session_for_async_client(session))
    created = await client.create("markdown")
    page = await client.fetch(created.slug, created.edit_code)
    exists = await client.exists(created.slug)
    raw = await client.raw(created.slug, access_code="raw-code")
    await client.replace(created.slug, created.edit_code, text="replacement", metadata={})
    await client.delete(created.slug, created.edit_code)

    assert page.text == "markdown"
    assert exists is True
    assert raw == "markdown"
    assert [(request["method"], request["url"]) for request in session.requests] == [
        ("POST", "https://rentry.co/api/new"),
        ("POST", "https://rentry.co/api/fetch/mixedcase"),
        ("GET", "https://rentry.co/mixedcase/exists"),
        ("GET", "https://rentry.co/api/raw/mixedcase"),
        ("POST", "https://rentry.co/api/edit/mixedcase"),
        ("POST", "https://rentry.co/api/delete/mixedcase"),
    ]


@pytest.mark.asyncio
async def test_owned_async_session_is_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeAsyncSession()
    monkeypatch.setattr(client_module.niquests, "AsyncSession", lambda: session)

    async with AsyncClient():
        pass

    assert session.close_calls == 1


@pytest.mark.parametrize(
    "content",
    [
        [],
        {},
        {"text": 3},
        {"text": "ok", "views": True},
        {"text": "ok", "modify_code_set": "yes"},
        {"text": "ok", "metadata_version": "1"},
        {"text": "ok", "url": 4},
        {"text": "ok", "url": "invalid slug"},
        {"text": "ok", "url": "example", "url_case": 4},
        {"text": "ok", "url": "example", "url_case": "invalid slug"},
        {"text": "ok", "url": "example", "url_case": "different"},
        {"text": "ok", "pub_date": "not-a-date"},
    ],
)
def test_fetch_rejects_malformed_success_content(content: object) -> None:
    session = FakeSession(success(content))

    with pytest.raises(ProtocolError):
        Client(session=session_for_client(session)).fetch("example", "edit")


@pytest.mark.parametrize("code", ["", "m:", "x" * 101])
def test_invalid_edit_codes_fail_locally(code: str) -> None:
    session = FakeSession()

    with pytest.raises(InvalidEditCodeError):
        Client(session=session_for_client(session)).fetch("example", code)

    assert not session.requests


def test_raw_rejects_non_text_success_content() -> None:
    session = FakeSession(success({"text": "nested"}))

    with pytest.raises(ProtocolError):
        Client(session=session_for_client(session)).raw("example")


def test_unset_representation() -> None:
    assert repr(client_module.UNSET) == "UNSET"


@pytest.mark.parametrize(
    ("domain", "error_type"),
    [
        (3, TypeError),
        ("https://rentry.co", ValueError),
        ("ftp://rentry.co", ValueError),
        ("https://user@rentry.co", ValueError),
        ("https://rentry.co/path", ValueError),
        ("https://rentry.co?query=yes", ValueError),
        ("rentry.example", ValueError),
        ("www.rentry.co", ValueError),
    ],
)
def test_invalid_domains_fail_locally(domain: object, error_type: type[Exception]) -> None:
    with pytest.raises(error_type):
        Client(cast(RentryDomain, domain))


def test_domains_and_page_urls_are_normalised() -> None:
    client = Client(
        cast(RentryDomain, " RENTRY.ORG "),
        session=session_for_client(FakeSession(FakeResponse(status_code=200, text="True"))),
    )

    assert client.domain == "rentry.org"
    assert client.exists("https://rentry.co/example") is True


def test_operational_paths_lowercase_display_slugs_without_changing_requested_new_slugs() -> None:
    session = FakeSession(
        FakeResponse(status_code=200, text="True"),
        success("markdown"),
        success({"url": "mixedcase", "url_case": "MixedCase", "text": "markdown", "metadata": {}}),
        success(),
        success(),
    )

    client = Client(session=session_for_client(session))

    assert client.exists("MixedCase") is True
    assert client.raw("https://rentry.org/MixedCase") == "markdown"

    page = client.fetch("MixedCase", "edit")
    client.update("MixedCase", "edit", new_slug="NewDisplayCase")
    client.delete("MixedCase", "edit")

    assert page.slug == "mixedcase"
    assert page.url == "https://rentry.co/MixedCase"
    assert [request["url"] for request in session.requests] == [
        "https://rentry.co/mixedcase/exists",
        "https://rentry.co/api/raw/mixedcase",
        "https://rentry.co/api/fetch/mixedcase",
        "https://rentry.co/api/edit/mixedcase",
        "https://rentry.co/api/delete/mixedcase",
    ]
    assert session.requests[3]["data"]["new_url"] == "NewDisplayCase"


@pytest.mark.parametrize(
    "slug",
    [
        3,
        "x",
        "invalid slug",
        "http://rentry.co/example",
        "https://www.rentry.co/example",
        "https://rentry.co/example?raw=1",
        "https://rentry.co/example#part",
    ],
)
def test_invalid_slugs_fail_locally(slug: object) -> None:
    with pytest.raises(TypeError if not isinstance(slug, str) else InvalidSlugError):
        Client(session=session_for_client(FakeSession())).exists(cast(str, slug))


def test_create_validates_and_forwards_all_optional_fields() -> None:
    session = FakeSession(success(url="example", edit_code="edit"))
    page = Client(session=session_for_client(session)).create("text", edit_code="chosen")

    assert page.url == "https://rentry.co/example"
    assert page.short_url == "example"
    assert session.requests[0]["data"] == {"text": "text", "edit_code": "chosen"}


@pytest.mark.parametrize(
    ("method", "args", "kwargs", "responses", "error_type"),
    [
        ("create", (3,), {}, (), TypeError),
        ("create", ("text",), {"edit_code": "m:invalid"}, (), InvalidEditCodeError),
        ("create", ("text",), {}, (success(url="example"),), ProtocolError),
        ("create", ("text",), {}, (success(url="example", edit_code=3),), ProtocolError),
        ("create", ("text",), {}, (success(url="https://rentry.co/example", url_short="different", edit_code="edit"),), ProtocolError),
        ("fetch", ("example", 3), {}, (), TypeError),
    ],
)
def test_invalid_create_and_fetch_inputs(
    method: str,
    args: tuple[object, ...],
    kwargs: dict[str, object],
    responses: tuple[FakeResponse, ...],
    error_type: type[Exception],
) -> None:
    client = Client(session=session_for_client(FakeSession(*responses)))

    with pytest.raises(error_type):
        getattr(client, method)(*args, **kwargs)


def test_exists_rejects_http_errors_and_wraps_transport_failures() -> None:
    with pytest.raises(ProtocolError, match="HTTP status 503"):
        Client(session=session_for_client(FakeSession(FakeResponse(status_code=503)))).exists("example")

    class FailingGetSession(FakeSession):
        def get(self, url: str, **kwargs: object) -> FakeResponse:
            raise RequestException("get failed")

    with pytest.raises(TransportError, match="get failed"):
        Client(session=session_for_client(FailingGetSession())).exists("example")


def test_sync_client_close_is_idempotent_and_allows_successful_delete() -> None:
    session = FakeSession(success())
    client = Client(session=session_for_client(session))
    client.delete("example", "edit")
    client.close()
    client.close()

    assert session.requests[0]["url"] == "https://rentry.co/api/delete/example"

    with pytest.raises(RentryError, match="closed"):
        client.exists("example")


def test_update_forwards_rotations_and_validates_values() -> None:
    session = FakeSession(success(), success())
    client = Client(session=session_for_client(session))

    client.update(
        "example",
        "edit",
        new_slug="renamed",
        new_edit_code="new-edit",
        new_modify_code="m:shared",
    )

    assert session.requests[0]["data"] == {
        "edit_code": "edit",
        "update_mode": "upsert",
        "new_url": "renamed",
        "new_edit_code": "new-edit",
        "new_modify_code": "m:shared",
    }

    with pytest.raises(TypeError, match="text"):
        client.update("example", "edit", text=cast(str, 3))

    with pytest.raises(InvalidEditCodeError, match="start with"):
        client.update("example", "edit", new_modify_code="shared")

    client.update("example", "edit", new_modify_code=" m:trimmed ")

    assert session.requests[1]["data"]["new_modify_code"] == "m:trimmed"

    with pytest.raises(TypeError, match="strings"):
        client.update("example", "edit", new_modify_code=cast(str, 3))


def test_replace_validates_text_and_allows_secret_metadata_changes() -> None:
    session = FakeSession(success())
    client = Client(session=session_for_client(session))
    client.replace("example", "m:shared", text="text", metadata={}, allow_secret_metadata_changes=True)

    assert session.requests[0]["data"]["update_secret_metadata"] == "true"

    with pytest.raises(TypeError, match="text"):
        client.replace("example", "edit", text=cast(str, 3), metadata={})


@pytest.mark.asyncio
async def test_async_closed_and_transport_failures_are_wrapped() -> None:
    class FailingAsyncSession(FakeAsyncSession):
        async def request(self, method: str, url: str, **kwargs: object) -> FakeResponse:
            raise RequestException("async request failed")

        async def get(self, url: str, **kwargs: object) -> FakeResponse:
            raise RequestException("async get failed")

    with pytest.raises(TransportError, match="async request failed"):
        await AsyncClient(session=session_for_async_client(FailingAsyncSession())).raw("example")

    with pytest.raises(TransportError, match="async get failed"):
        await AsyncClient(session=session_for_async_client(FailingAsyncSession())).exists("example")

    client = AsyncClient(session=session_for_async_client(FakeAsyncSession()))
    await client.aclose()
    await client.aclose()

    with pytest.raises(RentryError, match="closed"):
        await client.raw("example")

    with pytest.raises(RentryError, match="closed"):
        await client.exists("example")


def test_page_model_handles_empty_response_slugs_and_freezes_nested_metadata() -> None:
    page = page_from_content(
        {
            "url": "",
            "text": "text",
            "metadata": {"nested": {"colors": ["red"]}},
            "pub_date": "",
        },
        slug="fallback",
        origin="https://rentry.co",
    )

    assert page.slug == "fallback"
    assert page.published_at is None

    nested_metadata = cast(Mapping[str, object], page.metadata["nested"])

    assert nested_metadata["colors"] == ("red",)

    with pytest.raises(TypeError):
        cast(dict[str, object], nested_metadata)["colors"] = ()


def test_page_model_rejects_non_string_dates() -> None:
    with pytest.raises(ProtocolError, match="date string"):
        page_from_content(
            {"url": "example", "text": "text", "metadata": {}, "pub_date": 3},
            slug="example",
            origin="https://rentry.co",
        )
