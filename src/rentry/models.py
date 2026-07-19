from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import cast

from ._slugs import normalise_slug
from .exceptions import InvalidSlugError, ProtocolError
from .metadata import decode_metadata


@dataclass(frozen=True, slots=True)
class CreatedPage:
    """---
    Represents a newly created Rentry page.

    #### Attributes
    - slug: `str` — The page slug.
    - url: `str` — The full page URL.
    - short_url: `str` — The shortened page URL.
    - edit_code: `str` — The full edit code.
    """

    slug: str
    url: str
    short_url: str
    edit_code: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class Page:
    """---
    Represents a Rentry page.

    #### Attributes
    - slug: `str` — The page slug.
    - url: `str` — The full page URL.
    - text: `str` — The page's Markdown text.
    - metadata: `Mapping[str, object]` — The decoded page metadata.
    - views: `int | None = None` — The available page view count.
    - published_at: `datetime | None = None` — When the page was published.
    - activated_at: `datetime | None = None` — When the page was activated.
    - edited_at: `datetime | None = None` — When the page was last edited.
    - modify_code_set: `bool | None = None` — Whether the page has a modify code.
    - metadata_version: `int | None = None` — The page metadata format version.
    """

    slug: str
    url: str
    text: str
    metadata: Mapping[str, object]
    views: int | None = None
    published_at: datetime | None = None
    activated_at: datetime | None = None
    edited_at: datetime | None = None
    modify_code_set: bool | None = None
    metadata_version: int | None = None


def _optional_datetime(value: object, field_name: str) -> datetime | None:
    if value in (None, ""):
        return None

    if not isinstance(value, str):
        raise ProtocolError(f"The fetch response {field_name!r} field must be a date string or null.")

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProtocolError(f"The fetch response contains an invalid {field_name!r} date.") from exc


def _freeze(value: object) -> object:
    if isinstance(value, dict):
        mapping = cast(dict[object, object], value)

        return MappingProxyType({key: _freeze(item) for key, item in mapping.items()})

    if isinstance(value, list):
        items = cast(list[object], value)

        return tuple(_freeze(item) for item in items)

    return value


def page_from_content(content: object, *, slug: str, origin: str) -> Page:
    """---
    Build a page from Rentry response content.

    #### Arguments
    - content: `object` — The response content to parse.
    - slug: `str` — The requested page slug.
    - origin: `str` — The Rentry origin used to build the page URL.

    #### Returns
    - The parsed page.

    #### Raises
    - `ProtocolError` when the response content is invalid.
    """

    if not isinstance(content, dict):
        raise ProtocolError("The fetch response content must be an object.")

    fields = cast(dict[str, object], content)
    text = fields.get("text")

    if not isinstance(text, str):
        raise ProtocolError("The fetch response is missing its text field.")

    views = fields.get("views")

    if views is not None and (not isinstance(views, int) or isinstance(views, bool)):
        raise ProtocolError("The fetch response views field must be an integer or null.")

    modify_code_set = fields.get("modify_code_set")

    if modify_code_set is not None and not isinstance(modify_code_set, bool):
        raise ProtocolError("The fetch response modify_code_set field must be a boolean or null.")

    metadata_version = fields.get("metadata_version")

    if metadata_version is not None and (not isinstance(metadata_version, int) or isinstance(metadata_version, bool)):
        raise ProtocolError("The fetch response metadata_version field must be an integer or null.")

    response_slug = fields.get("url", slug)

    if not isinstance(response_slug, str):
        raise ProtocolError("The fetch response url field must be a string.")

    try:
        canonical_slug = normalise_slug(response_slug.strip("/") or slug).lower()
    except (InvalidSlugError, TypeError) as exc:
        raise ProtocolError("The fetch response contains an invalid page slug.") from exc

    response_display_slug = fields.get("url_case", canonical_slug)

    if not isinstance(response_display_slug, str):
        raise ProtocolError("The fetch response url_case field must be a string.")

    try:
        display_slug = normalise_slug(response_display_slug.strip("/") or canonical_slug)
    except (InvalidSlugError, TypeError) as exc:
        raise ProtocolError("The fetch response contains an invalid display page slug.") from exc

    if display_slug.lower() != canonical_slug:
        raise ProtocolError("The fetch response page slugs do not match.")

    metadata = MappingProxyType({key: _freeze(value) for key, value in decode_metadata(fields.get("metadata")).items()})

    return Page(
        slug=canonical_slug,
        url=f"{origin}/{display_slug}",
        text=text,
        metadata=metadata,
        views=views,
        published_at=_optional_datetime(fields.get("pub_date"), "pub_date"),
        activated_at=_optional_datetime(fields.get("activated_date"), "activated_date"),
        edited_at=_optional_datetime(fields.get("edit_date"), "edit_date"),
        modify_code_set=modify_code_set,
        metadata_version=metadata_version,
    )
