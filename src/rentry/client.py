from __future__ import annotations

from collections.abc import Mapping
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Final, Literal, cast
from urllib.parse import urlsplit

import niquests
from niquests.exceptions import RequestException

from ._api import ResponseLike, parse_api_response
from ._slugs import RENTRY_DOMAINS as _RENTRY_DOMAINS
from ._slugs import normalise_slug as _normalise_slug
from .exceptions import InvalidEditCodeError, ProtocolError, RentryError, TransportError
from .metadata import MetadataInput, MetadataPatch, encode_metadata
from .models import CreatedPage, Page, page_from_content

RentryDomain = Literal["rentry.co", "rentry.org"]
DEFAULT_DOMAIN: Final[RentryDomain] = "rentry.co"


def _package_version() -> str:
    try:
        return version("rentry.py")
    except PackageNotFoundError:
        return "1.0.0"


DEFAULT_USER_AGENT: Final = f"rentry.py/{_package_version()} (PyPI)"


class UnsetType:
    """Represents an omitted argument."""

    __slots__ = ()

    def __repr__(self) -> str:
        """Return the representation of `UNSET`."""
        return "UNSET"


UNSET: Final = UnsetType()


def _normalise_domain(domain: RentryDomain) -> RentryDomain:
    if not isinstance(domain, str):
        raise TypeError("domain must be a string.")

    candidate = domain.strip().lower()

    if candidate not in _RENTRY_DOMAINS:
        raise ValueError("domain must be 'rentry.co' or 'rentry.org'.")

    return cast(RentryDomain, candidate)


def _normalise_code(value: str, *, allow_modify: bool) -> str:
    if not isinstance(value, str):
        raise TypeError("edit codes must be strings.")

    code = value.strip()

    if not 1 <= len(code) <= 100:
        raise InvalidEditCodeError("Edit and modify codes must contain 1 to 100 characters.")

    is_modify = code.lower().startswith("m:")

    if is_modify and len(code) == 2:
        raise InvalidEditCodeError("A modify code must contain a value after 'm:'.")

    if is_modify and not allow_modify:
        raise InvalidEditCodeError("A modify code cannot be used for this operation.")

    return code


def _normalise_new_edit_code(value: str) -> str:
    code = _normalise_code(value, allow_modify=False)

    return code


def _normalise_new_modify_code(value: str | None) -> str:
    if value is None:
        return "m:"

    code = _normalise_code(value, allow_modify=True)

    if not code.lower().startswith("m:"):
        raise InvalidEditCodeError("A modify code must start with 'm:'.")

    return code


def _as_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ProtocolError(f"The successful response is missing its {field_name!r} field.")

    return value


def _response_content(payload: Mapping[str, Any]) -> object:
    return payload.get("content")


def _created_page(payload: Mapping[str, Any], *, origin: str) -> CreatedPage:
    content = _response_content(payload)
    fields = cast(Mapping[str, Any], content) if isinstance(content, Mapping) else payload
    returned_url = fields.get("url")
    returned_short_url = fields.get("url_short")

    if not isinstance(returned_short_url, str):
        returned_short_url = _as_string(returned_url, "url")

    slug = _normalise_slug(returned_short_url).lower()
    edit_code = _as_string(fields.get("edit_code"), "edit_code")
    page_url = f"{origin}/{slug}"

    if isinstance(returned_url, str) and returned_url.startswith("https://"):
        returned_slug = _normalise_slug(returned_url)
        returned_domain = urlsplit(returned_url).netloc.lower()

        if returned_slug.lower() != slug:
            raise ProtocolError("The successful response contains mismatched page URLs.")

        page_url = f"https://{returned_domain}/{returned_slug}"

    return CreatedPage(slug=slug, url=page_url, short_url=returned_short_url, edit_code=edit_code)


def _create_payload(
    text: str,
    *,
    metadata: MetadataInput | UnsetType,
    slug: str | None,
    edit_code: str | None,
) -> dict[str, str]:
    if not isinstance(text, str):
        raise TypeError("text must be a string.")

    payload = {"text": text}

    if metadata is not UNSET:
        payload["metadata"] = encode_metadata(cast(MetadataInput, metadata))

    if slug is not None:
        payload["url"] = _normalise_slug(slug)

    if edit_code is not None:
        payload["edit_code"] = _normalise_code(edit_code, allow_modify=False)

    return payload


def _page_credentials(slug: str, edit_code: str, *, allow_modify: bool) -> tuple[str, str]:
    return _normalise_slug(slug).lower(), _normalise_code(edit_code, allow_modify=allow_modify)


def _raw_text(payload: Mapping[str, Any]) -> str:
    content = _response_content(payload)

    if not isinstance(content, str):
        raise ProtocolError("The raw endpoint returned non-text content.")

    return content


def _parse_exists(response: ResponseLike) -> bool:
    if response.status_code != 200:
        raise ProtocolError(f"Rentry returned unexpected HTTP status {response.status_code}.")

    if response.text not in {"True", "False"}:
        raise ProtocolError("The Rentry existence endpoint did not return True or False.")

    return response.text == "True"


def _update_request(
    slug: str,
    edit_code: str,
    *,
    text: str | UnsetType,
    metadata: MetadataPatch | UnsetType,
    new_slug: str | UnsetType,
    new_edit_code: str | UnsetType,
    new_modify_code: str | None | UnsetType,
    allow_secret_metadata_changes: bool,
) -> tuple[str, dict[str, str]]:
    page_slug, code = _page_credentials(slug, edit_code, allow_modify=True)
    rotations = (new_slug, new_edit_code, new_modify_code)

    if code.lower().startswith("m:") and any(value is not UNSET for value in rotations):
        raise InvalidEditCodeError("Modify codes cannot rotate a page slug, edit code, or modify code.")

    payload = {"edit_code": code, "update_mode": "upsert"}

    if text is not UNSET:
        if not isinstance(text, str):
            raise TypeError("text must be a string.")

        payload["text"] = text

    if metadata is not UNSET:
        payload["metadata"] = encode_metadata(cast(MetadataPatch, metadata), allow_removal=True)

    if new_slug is not UNSET:
        payload["new_url"] = _normalise_slug(cast(str, new_slug))

    if new_edit_code is not UNSET:
        payload["new_edit_code"] = _normalise_new_edit_code(cast(str, new_edit_code))

    if new_modify_code is not UNSET:
        payload["new_modify_code"] = _normalise_new_modify_code(cast(str | None, new_modify_code))

    if allow_secret_metadata_changes:
        payload["update_secret_metadata"] = "true"

    if len(payload) == 2:
        raise ValueError("update() requires at least one field to change.")

    return page_slug, payload


def _replace_request(
    slug: str,
    edit_code: str,
    *,
    text: str,
    metadata: MetadataInput,
    allow_secret_metadata_changes: bool,
) -> tuple[str, dict[str, str]]:
    if not isinstance(text, str):
        raise TypeError("text must be a string.")

    page_slug, code = _page_credentials(slug, edit_code, allow_modify=True)

    payload = {
        "edit_code": code,
        "update_mode": "replace",
        "text": text,
        "metadata": encode_metadata(metadata),
    }

    if allow_secret_metadata_changes:
        payload["update_secret_metadata"] = "true"

    return page_slug, payload


class Client:
    """---
    Synchronous Rentry API client.

    #### Attributes
    - domain: `RentryDomain` — The Rentry domain used for requests.
    - timeout: `float` — The request timeout in seconds.
    - user_agent: `str` — The User-Agent sent with requests.

    #### Methods
    - `create()` — Create a page.
    - `fetch()` — Fetch a page.
    - `exists()` — Return whether a page exists.
    - `raw()` — Return a page's raw Markdown.
    - `update()` — Update a page.
    - `replace()` — Replace a page's text and metadata.
    - `delete()` — Delete a page.
    - `close()` — Close the client.

    #### Raises
    - `InvalidSlugError` when a page slug or URL is invalid.
    - `InvalidEditCodeError` when an edit or modify code is invalid.
    - `InvalidMetadataError` when metadata is invalid.
    - `TransportError` when a request cannot reach Rentry.
    - `ProtocolError` when a response does not follow the Rentry API protocol.
    - `APIError` when the Rentry API rejects a request.
    - `RentryError` when the client is used after being closed.
    - `TypeError` when an argument has an invalid type.
    - `ValueError` when the domain or requested update is invalid.
    """

    def __init__(
        self,
        domain: RentryDomain = DEFAULT_DOMAIN,
        *,
        timeout: float = 30.0,
        user_agent: str | None = None,
        session: niquests.Session | None = None,
    ) -> None:
        self.domain = _normalise_domain(domain)
        self._origin = f"https://{self.domain}"
        self.timeout = timeout
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self._session = session if session is not None else niquests.Session()
        self._owns_session = session is None
        self._closed = False

    def __enter__(self) -> Client:
        """Enter the context manager."""
        return self

    def __exit__(self, *_: object) -> None:
        """Exit the context manager."""
        self.close()

    def close(self) -> None:
        """Close the client."""

        if self._closed:
            return

        if self._owns_session:
            self._session.close()

        self._closed = True

    def _request(
        self,
        method: str,
        path: str,
        *,
        data: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]:
        if self._closed:
            raise RentryError("This client is closed.")

        request_headers = {"User-Agent": self.user_agent}

        if headers:
            request_headers.update(headers)

        try:
            response = self._session.request(
                method,
                f"{self._origin}{path}",
                data=data,
                headers=request_headers,
                timeout=self.timeout,
            )
        except RequestException as exc:
            raise TransportError(f"Rentry request failed: {exc}") from exc

        return parse_api_response(cast(ResponseLike, response))

    def create(
        self,
        text: str,
        *,
        metadata: MetadataInput | UnsetType = UNSET,
        slug: str | None = None,
        edit_code: str | None = None,
    ) -> CreatedPage:
        """---
        Create a page.

        #### Arguments
        - text: `str` — The page's Markdown text.
        - metadata: `MetadataInput | UnsetType = UNSET` — The page's metadata. Omit to use Rentry's defaults.
        - slug: `str | None = None` — The requested page slug. If `None`, Rentry generates one.
        - edit_code: `str | None = None` — The requested full edit code. If `None`, Rentry generates one.

        #### Returns
        - A `CreatedPage` containing the page's slug, URLs, and full edit code.

        #### Raises
        - `InvalidSlugError` when `slug` is invalid.
        - `InvalidEditCodeError` when `edit_code` is invalid.
        - `InvalidMetadataError` when `metadata` is invalid.
        - `TransportError` when the request cannot reach Rentry.
        - `ProtocolError` when the response does not follow the Rentry API protocol.
        - `APIError` when the Rentry API rejects the request.
        - `RentryError` when the client is closed.
        - `TypeError` when an argument has an invalid type.
        """

        payload = _create_payload(
            text,
            metadata=metadata,
            slug=slug,
            edit_code=edit_code,
        )

        response = self._request("POST", "/api/new", data=payload)

        return _created_page(response, origin=self._origin)

    def fetch(self, slug: str, edit_code: str) -> Page:
        """---
        Fetch a page.

        #### Arguments
        - slug: `str` — The page's slug or full Rentry URL.
        - edit_code: `str` — The page's full edit code or modify code.

        #### Returns
        - A `Page` containing the page's text, metadata, and available details.

        #### Raises
        - `InvalidSlugError` when `slug` is invalid.
        - `InvalidEditCodeError` when `edit_code` is invalid.
        - `TransportError` when the request cannot reach Rentry.
        - `ProtocolError` when the response does not follow the Rentry API protocol.
        - `APIError` when the Rentry API rejects the request.
        - `RentryError` when the client is closed.
        - `TypeError` when an argument has an invalid type.
        """

        page_slug, code = _page_credentials(slug, edit_code, allow_modify=True)
        response = self._request("POST", f"/api/fetch/{page_slug}", data={"edit_code": code})

        return page_from_content(_response_content(response), slug=page_slug, origin=self._origin)

    def exists(self, slug: str) -> bool:
        """---
        Return whether a page exists.

        #### Arguments
        - slug: `str` — The page's slug or full Rentry URL.

        #### Returns
        - `True` when the page exists, otherwise `False`.

        #### Raises
        - `InvalidSlugError` when `slug` is invalid.
        - `TransportError` when the request cannot reach Rentry.
        - `ProtocolError` when the response does not follow the Rentry API protocol.
        - `RentryError` when the client is closed.
        - `TypeError` when `slug` has an invalid type.
        """

        page_slug = _normalise_slug(slug).lower()

        if self._closed:
            raise RentryError("This client is closed.")

        try:
            response = self._session.get(
                f"{self._origin}/{page_slug}/exists",
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout,
            )
        except RequestException as exc:
            raise TransportError(f"Rentry request failed: {exc}") from exc

        return _parse_exists(cast(ResponseLike, response))

    def raw(self, slug: str, *, access_code: str | None = None) -> str:
        """---
        Return a page's raw Markdown.

        #### Arguments
        - slug: `str` — The page's slug or full Rentry URL.
        - access_code: `str | None = None` — A Rentry-issued raw access code.

        #### Returns
        - The page's raw Markdown text.

        #### Raises
        - `InvalidSlugError` when `slug` is invalid.
        - `TransportError` when the request cannot reach Rentry.
        - `ProtocolError` when the response does not follow the Rentry API protocol.
        - `APIError` when the Rentry API rejects the request.
        - `RentryError` when the client is closed.
        - `TypeError` when `slug` has an invalid type.
        """

        page_slug = _normalise_slug(slug).lower()
        headers = {"rentry-auth": access_code} if access_code is not None else None
        response = self._request("GET", f"/api/raw/{page_slug}", headers=headers)

        return _raw_text(response)

    def update(
        self,
        slug: str,
        edit_code: str,
        *,
        text: str | UnsetType = UNSET,
        metadata: MetadataPatch | UnsetType = UNSET,
        new_slug: str | UnsetType = UNSET,
        new_edit_code: str | UnsetType = UNSET,
        new_modify_code: str | None | UnsetType = UNSET,
        allow_secret_metadata_changes: bool = False,
    ) -> None:
        """---
        Update a page without changing omitted fields.

        #### Arguments
        - slug: `str` — The page's slug or full Rentry URL.
        - edit_code: `str` — The page's full edit code or modify code.
        - text: `str | UnsetType = UNSET` — New Markdown text. Omit to preserve the current text or pass an empty string to clear it.
        - metadata: `MetadataPatch | UnsetType = UNSET` — Metadata changes. Omit to preserve all metadata or use `None` values to remove individual options.
        - new_slug: `str | UnsetType = UNSET` — A new page slug.
        - new_edit_code: `str | UnsetType = UNSET` — A new full edit code.
        - new_modify_code: `str | None | UnsetType = UNSET` — A new modify code. Omit to preserve the current code or pass `None` to remove it.
        - allow_secret_metadata_changes: `bool = False` — Allow changes to `SECRET_*` metadata options.

        #### Raises
        - `InvalidSlugError` when `slug` or `new_slug` is invalid.
        - `InvalidEditCodeError` when a supplied edit or modify code is invalid, or when a modify code attempts to rotate a slug or code.
        - `InvalidMetadataError` when `metadata` is invalid.
        - `TransportError` when the request cannot reach Rentry.
        - `ProtocolError` when the response does not follow the Rentry API protocol.
        - `APIError` when the Rentry API rejects the request.
        - `RentryError` when the client is closed.
        - `TypeError` when an argument has an invalid type.
        - `ValueError` when no changes are provided.
        """

        page_slug, payload = _update_request(
            slug,
            edit_code,
            text=text,
            metadata=metadata,
            new_slug=new_slug,
            new_edit_code=new_edit_code,
            new_modify_code=new_modify_code,
            allow_secret_metadata_changes=allow_secret_metadata_changes,
        )

        self._request("POST", f"/api/edit/{page_slug}", data=payload)

    def replace(
        self,
        slug: str,
        edit_code: str,
        *,
        text: str,
        metadata: MetadataInput,
        allow_secret_metadata_changes: bool = False,
    ) -> None:
        """---
        Replace a page's complete text and metadata set.

        #### Arguments
        - slug: `str` — The page's slug or full Rentry URL.
        - edit_code: `str` — The page's full edit code or modify code.
        - text: `str` — The complete replacement Markdown text.
        - metadata: `MetadataInput` — The complete replacement metadata set.
        - allow_secret_metadata_changes: `bool = False` — Allow changes to `SECRET_*` metadata options.

        #### Raises
        - `InvalidSlugError` when `slug` is invalid.
        - `InvalidEditCodeError` when `edit_code` is invalid.
        - `InvalidMetadataError` when `metadata` is invalid.
        - `TransportError` when the request cannot reach Rentry.
        - `ProtocolError` when the response does not follow the Rentry API protocol.
        - `APIError` when the Rentry API rejects the request.
        - `RentryError` when the client is closed.
        - `TypeError` when an argument has an invalid type.
        """

        page_slug, payload = _replace_request(
            slug,
            edit_code,
            text=text,
            metadata=metadata,
            allow_secret_metadata_changes=allow_secret_metadata_changes,
        )

        self._request("POST", f"/api/edit/{page_slug}", data=payload)

    def delete(self, slug: str, edit_code: str) -> None:
        """---
        Delete a page.

        #### Arguments
        - slug: `str` — The page's slug or full Rentry URL.
        - edit_code: `str` — The page's full edit code.

        #### Raises
        - `InvalidSlugError` when `slug` is invalid.
        - `InvalidEditCodeError` when `edit_code` is invalid or is a modify code.
        - `TransportError` when the request cannot reach Rentry.
        - `ProtocolError` when the response does not follow the Rentry API protocol.
        - `APIError` when the Rentry API rejects the request.
        - `RentryError` when the client is closed.
        - `TypeError` when an argument has an invalid type.
        """

        page_slug, code = _page_credentials(slug, edit_code, allow_modify=False)
        self._request("POST", f"/api/delete/{page_slug}", data={"edit_code": code})


class AsyncClient:
    """---
    Asynchronous Rentry API client.

    #### Attributes
    - domain: `RentryDomain` — The Rentry domain used for requests.
    - timeout: `float` — The request timeout in seconds.
    - user_agent: `str` — The User-Agent sent with requests.

    #### Methods
    - `create()` — Create a page.
    - `fetch()` — Fetch a page.
    - `exists()` — Return whether a page exists.
    - `raw()` — Return a page's raw Markdown.
    - `update()` — Update a page.
    - `replace()` — Replace a page's text and metadata.
    - `delete()` — Delete a page.
    - `aclose()` — Close the client.

    #### Raises
    - `InvalidSlugError` when a page slug or URL is invalid.
    - `InvalidEditCodeError` when an edit or modify code is invalid.
    - `InvalidMetadataError` when metadata is invalid.
    - `TransportError` when a request cannot reach Rentry.
    - `ProtocolError` when a response does not follow the Rentry API protocol.
    - `APIError` when the Rentry API rejects a request.
    - `RentryError` when the client is used after being closed.
    - `TypeError` when an argument has an invalid type.
    - `ValueError` when the domain or requested update is invalid.
    """

    def __init__(
        self,
        domain: RentryDomain = DEFAULT_DOMAIN,
        *,
        timeout: float = 30.0,
        user_agent: str | None = None,
        session: niquests.AsyncSession | None = None,
    ) -> None:
        self.domain = _normalise_domain(domain)
        self._origin = f"https://{self.domain}"
        self.timeout = timeout
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self._session = session if session is not None else niquests.AsyncSession()
        self._owns_session = session is None
        self._closed = False

    async def __aenter__(self) -> AsyncClient:
        """Enter the asynchronous context manager."""
        return self

    async def __aexit__(self, *_: object) -> None:
        """Exit the asynchronous context manager."""
        await self.aclose()

    async def aclose(self) -> None:
        """Close the client."""

        if self._closed:
            return

        if self._owns_session:
            await self._session.close()

        self._closed = True

    async def _request(
        self,
        method: str,
        path: str,
        *,
        data: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]:
        if self._closed:
            raise RentryError("This client is closed.")

        request_headers = {"User-Agent": self.user_agent}

        if headers:
            request_headers.update(headers)

        try:
            response = await self._session.request(
                method,
                f"{self._origin}{path}",
                data=data,
                headers=request_headers,
                timeout=self.timeout,
            )
        except RequestException as exc:
            raise TransportError(f"Rentry request failed: {exc}") from exc

        return parse_api_response(cast(ResponseLike, response))

    async def create(
        self,
        text: str,
        *,
        metadata: MetadataInput | UnsetType = UNSET,
        slug: str | None = None,
        edit_code: str | None = None,
    ) -> CreatedPage:
        """---
        Create a page.

        #### Arguments
        - text: `str` — The page's Markdown text.
        - metadata: `MetadataInput | UnsetType = UNSET` — The page's metadata. Omit to use Rentry's defaults.
        - slug: `str | None = None` — The requested page slug. If `None`, Rentry generates one.
        - edit_code: `str | None = None` — The requested full edit code. If `None`, Rentry generates one.

        #### Returns
        - A `CreatedPage` containing the page's slug, URLs, and full edit code.

        #### Raises
        - `InvalidSlugError` when `slug` is invalid.
        - `InvalidEditCodeError` when `edit_code` is invalid.
        - `InvalidMetadataError` when `metadata` is invalid.
        - `TransportError` when the request cannot reach Rentry.
        - `ProtocolError` when the response does not follow the Rentry API protocol.
        - `APIError` when the Rentry API rejects the request.
        - `RentryError` when the client is closed.
        - `TypeError` when an argument has an invalid type.
        """

        payload = _create_payload(
            text,
            metadata=metadata,
            slug=slug,
            edit_code=edit_code,
        )

        response = await self._request("POST", "/api/new", data=payload)

        return _created_page(response, origin=self._origin)

    async def fetch(self, slug: str, edit_code: str) -> Page:
        """---
        Fetch a page.

        #### Arguments
        - slug: `str` — The page's slug or full Rentry URL.
        - edit_code: `str` — The page's full edit code or modify code.

        #### Returns
        - A `Page` containing the page's text, metadata, and available details.

        #### Raises
        - `InvalidSlugError` when `slug` is invalid.
        - `InvalidEditCodeError` when `edit_code` is invalid.
        - `TransportError` when the request cannot reach Rentry.
        - `ProtocolError` when the response does not follow the Rentry API protocol.
        - `APIError` when the Rentry API rejects the request.
        - `RentryError` when the client is closed.
        - `TypeError` when an argument has an invalid type.
        """

        page_slug, code = _page_credentials(slug, edit_code, allow_modify=True)
        response = await self._request("POST", f"/api/fetch/{page_slug}", data={"edit_code": code})

        return page_from_content(_response_content(response), slug=page_slug, origin=self._origin)

    async def exists(self, slug: str) -> bool:
        """---
        Return whether a page exists.

        #### Arguments
        - slug: `str` — The page's slug or full Rentry URL.

        #### Returns
        - `True` when the page exists, otherwise `False`.

        #### Raises
        - `InvalidSlugError` when `slug` is invalid.
        - `TransportError` when the request cannot reach Rentry.
        - `ProtocolError` when the response does not follow the Rentry API protocol.
        - `RentryError` when the client is closed.
        - `TypeError` when `slug` has an invalid type.
        """

        page_slug = _normalise_slug(slug).lower()

        if self._closed:
            raise RentryError("This client is closed.")

        try:
            response = await self._session.get(
                f"{self._origin}/{page_slug}/exists",
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout,
            )
        except RequestException as exc:
            raise TransportError(f"Rentry request failed: {exc}") from exc

        return _parse_exists(cast(ResponseLike, response))

    async def raw(self, slug: str, *, access_code: str | None = None) -> str:
        """---
        Return a page's raw Markdown.

        #### Arguments
        - slug: `str` — The page's slug or full Rentry URL.
        - access_code: `str | None = None` — A Rentry-issued raw access code.

        #### Returns
        - The page's raw Markdown text.

        #### Raises
        - `InvalidSlugError` when `slug` is invalid.
        - `TransportError` when the request cannot reach Rentry.
        - `ProtocolError` when the response does not follow the Rentry API protocol.
        - `APIError` when the Rentry API rejects the request.
        - `RentryError` when the client is closed.
        - `TypeError` when `slug` has an invalid type.
        """

        page_slug = _normalise_slug(slug).lower()
        headers = {"rentry-auth": access_code} if access_code is not None else None
        response = await self._request("GET", f"/api/raw/{page_slug}", headers=headers)

        return _raw_text(response)

    async def update(
        self,
        slug: str,
        edit_code: str,
        *,
        text: str | UnsetType = UNSET,
        metadata: MetadataPatch | UnsetType = UNSET,
        new_slug: str | UnsetType = UNSET,
        new_edit_code: str | UnsetType = UNSET,
        new_modify_code: str | None | UnsetType = UNSET,
        allow_secret_metadata_changes: bool = False,
    ) -> None:
        """---
        Update a page without changing omitted fields.

        #### Arguments
        - slug: `str` — The page's slug or full Rentry URL.
        - edit_code: `str` — The page's full edit code or modify code.
        - text: `str | UnsetType = UNSET` — New Markdown text. Omit to preserve the current text or pass an empty string to clear it.
        - metadata: `MetadataPatch | UnsetType = UNSET` — Metadata changes. Omit to preserve all metadata or use `None` values to remove individual options.
        - new_slug: `str | UnsetType = UNSET` — A new page slug.
        - new_edit_code: `str | UnsetType = UNSET` — A new full edit code.
        - new_modify_code: `str | None | UnsetType = UNSET` — A new modify code. Omit to preserve the current code or pass `None` to remove it.
        - allow_secret_metadata_changes: `bool = False` — Allow changes to `SECRET_*` metadata options.

        #### Raises
        - `InvalidSlugError` when `slug` or `new_slug` is invalid.
        - `InvalidEditCodeError` when a supplied edit or modify code is invalid, or when a modify code attempts to rotate a slug or code.
        - `InvalidMetadataError` when `metadata` is invalid.
        - `TransportError` when the request cannot reach Rentry.
        - `ProtocolError` when the response does not follow the Rentry API protocol.
        - `APIError` when the Rentry API rejects the request.
        - `RentryError` when the client is closed.
        - `TypeError` when an argument has an invalid type.
        - `ValueError` when no changes are provided.
        """

        page_slug, payload = _update_request(
            slug,
            edit_code,
            text=text,
            metadata=metadata,
            new_slug=new_slug,
            new_edit_code=new_edit_code,
            new_modify_code=new_modify_code,
            allow_secret_metadata_changes=allow_secret_metadata_changes,
        )

        await self._request("POST", f"/api/edit/{page_slug}", data=payload)

    async def replace(
        self,
        slug: str,
        edit_code: str,
        *,
        text: str,
        metadata: MetadataInput,
        allow_secret_metadata_changes: bool = False,
    ) -> None:
        """---
        Replace a page's complete text and metadata set.

        #### Arguments
        - slug: `str` — The page's slug or full Rentry URL.
        - edit_code: `str` — The page's full edit code or modify code.
        - text: `str` — The complete replacement Markdown text.
        - metadata: `MetadataInput` — The complete replacement metadata set.
        - allow_secret_metadata_changes: `bool = False` — Allow changes to `SECRET_*` metadata options.

        #### Raises
        - `InvalidSlugError` when `slug` is invalid.
        - `InvalidEditCodeError` when `edit_code` is invalid.
        - `InvalidMetadataError` when `metadata` is invalid.
        - `TransportError` when the request cannot reach Rentry.
        - `ProtocolError` when the response does not follow the Rentry API protocol.
        - `APIError` when the Rentry API rejects the request.
        - `RentryError` when the client is closed.
        - `TypeError` when an argument has an invalid type.
        """

        page_slug, payload = _replace_request(
            slug,
            edit_code,
            text=text,
            metadata=metadata,
            allow_secret_metadata_changes=allow_secret_metadata_changes,
        )

        await self._request("POST", f"/api/edit/{page_slug}", data=payload)

    async def delete(self, slug: str, edit_code: str) -> None:
        """---
        Delete a page.

        #### Arguments
        - slug: `str` — The page's slug or full Rentry URL.
        - edit_code: `str` — The page's full edit code.

        #### Raises
        - `InvalidSlugError` when `slug` is invalid.
        - `InvalidEditCodeError` when `edit_code` is invalid or is a modify code.
        - `TransportError` when the request cannot reach Rentry.
        - `ProtocolError` when the response does not follow the Rentry API protocol.
        - `APIError` when the Rentry API rejects the request.
        - `RentryError` when the client is closed.
        - `TypeError` when an argument has an invalid type.
        """

        page_slug, code = _page_credentials(slug, edit_code, allow_modify=False)
        await self._request("POST", f"/api/delete/{page_slug}", data={"edit_code": code})
