from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Literal, TypedDict, cast

from .exceptions import InvalidMetadataError, ProtocolError

MetadataValue = str | bool | Sequence[str]
MetadataPatchValue = MetadataValue | None


class Metadata(TypedDict, total=False):
    """Known Rentry metadata options."""

    PAGE_TITLE: str
    PAGE_DESCRIPTION: str
    PAGE_IMAGE: str
    PAGE_ICON: str
    SHARE_TITLE: str
    SHARE_DESCRIPTION: str
    SHARE_IMAGE: str
    SHARE_TWITTER_TITLE: str
    SHARE_TWITTER_DESCRIPTION: str
    SHARE_TWITTER_IMAGE: str
    OPTION_DISABLE_VIEWS: bool
    OPTION_DISABLE_SEARCH_ENGINE: bool
    OPTION_USE_ORIGINAL_PUB_DATE: bool
    ACCESS_RECOMMENDED_THEME: Literal["dark", "light"]
    ACCESS_EASY_READ: str
    SECRET_VERIFY: str
    SECRET_RAW_ACCESS_CODE: str
    SECRET_EMAIL_ADDRESS: str
    CONTAINER_PADDING: list[str]
    CONTAINER_MAX_WIDTH: str
    CONTAINER_INNER_FOREGROUND_COLOR: list[str]
    CONTAINER_INNER_BACKGROUND_COLOR: list[str]
    CONTAINER_INNER_BACKGROUND_IMAGE: str
    CONTAINER_INNER_BACKGROUND_IMAGE_REPEAT: Literal["no-repeat", "repeat-x", "repeat-y", "round", "space"]
    CONTAINER_INNER_BACKGROUND_IMAGE_POSITION: Literal["center", "left", "right", "top", "bottom"]
    CONTAINER_INNER_BACKGROUND_IMAGE_SIZE: str
    CONTAINER_OUTER_FOREGROUND_COLOR: list[str]
    CONTAINER_OUTER_BACKGROUND_COLOR: list[str]
    CONTAINER_OUTER_BACKGROUND_IMAGE: str
    CONTAINER_OUTER_BACKGROUND_IMAGE_REPEAT: Literal["no-repeat", "repeat-x", "repeat-y", "round", "space"]
    CONTAINER_OUTER_BACKGROUND_IMAGE_POSITION: Literal["center", "left", "right", "top", "bottom"]
    CONTAINER_OUTER_BACKGROUND_IMAGE_SIZE: str
    CONTAINER_BORDER_IMAGE: str
    CONTAINER_BORDER_IMAGE_SLICE: list[str]
    CONTAINER_BORDER_IMAGE_WIDTH: list[str]
    CONTAINER_BORDER_IMAGE_OUTSET: list[str]
    CONTAINER_BORDER_IMAGE_REPEAT: list[str]
    CONTAINER_BORDER_COLOR: list[str]
    CONTAINER_BORDER_WIDTH: list[str]
    CONTAINER_BORDER_STYLE: list[Literal["dotted", "dashed", "solid", "double", "groove", "ridge", "inset", "outset"]]
    CONTAINER_BORDER_RADIUS: list[str]
    CONTAINER_SHADOW_COLOR: str
    CONTAINER_SHADOW_OFFSET: list[str]
    CONTAINER_SHADOW_SPREAD: str
    CONTAINER_SHADOW_BLUR: str
    CONTENT_FONT: list[str]
    CONTENT_FONT_WEIGHT: list[Literal["bold", "bolder", "lighter", "normal", "100", "200", "300", "400", "500", "600", "700", "800", "900"]]
    CONTENT_TEXT_DIRECTION: Literal["ltr", "rtl"]
    CONTENT_TEXT_SIZE: list[str]
    CONTENT_TEXT_ALIGN: Literal["right", "center", "justify"]
    CONTENT_TEXT_SHADOW_COLOR: str
    CONTENT_TEXT_SHADOW_OFFSET: list[str]
    CONTENT_TEXT_SHADOW_BLUR: str
    CONTENT_TEXT_COLOR: list[str]
    CONTENT_LINK_COLOR: list[str]
    CONTENT_BULLET_COLOR: list[str]
    CONTENT_LINK_BEHAVIOR: list[Literal["same", "new"]]
    SAFETY_PAGE_WARNING: list[Literal["adult", "sensitive", "epilepsy", "custom"]]
    SAFETY_PAGE_WARNING_DESCRIPTION: str
    SAFETY_MEDIA_BLUR: bool
    SAFETY_LINK_WARNING: list[Literal["adult", "epilepsy", "sensitive"]]
    SAFETY_LINK_WARNING_DESCRIPTION: str
    SAFETY_PAGE_FLAG: list[Literal["adult", "epilepsy", "sensitive"]]


MetadataInput = Metadata | Mapping[str, MetadataValue] | str
MetadataPatch = Metadata | Mapping[str, MetadataPatchValue] | str


def _normalise_mapping(metadata: Mapping[str, object], *, allow_removal: bool) -> dict[str, object]:
    normalised: dict[str, object] = {}

    for key, value in metadata.items():
        if not isinstance(key, str) or not key:
            raise InvalidMetadataError("Metadata keys must be non-empty strings.")

        if value is None:
            if not allow_removal:
                raise InvalidMetadataError("Metadata values cannot be None outside an upsert update.")

            normalised[key] = ""

            continue

        if isinstance(value, str | bool):
            normalised[key] = value

            continue

        if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
            items = list(cast(Sequence[object], value))

            if not all(isinstance(item, str) for item in items):
                raise InvalidMetadataError("Metadata sequence values may contain only strings.")

            normalised[key] = items

            continue

        raise InvalidMetadataError(f"Unsupported metadata value for {key!r}: {type(value).__name__}.")

    return normalised


def encode_metadata(metadata: MetadataInput | MetadataPatch, *, allow_removal: bool = False) -> str:
    """---
    Encode metadata for the Rentry API.

    #### Arguments
    - metadata: `MetadataInput | MetadataPatch` — Metadata options or an existing JSON object string.
    - allow_removal: `bool = False` — Whether `None` values should remove existing metadata options.

    #### Returns
    - The encoded metadata string.

    #### Raises
    - `InvalidMetadataError` when the supplied metadata is invalid.
    """

    if isinstance(metadata, str):
        if not metadata.lstrip().startswith(("{", "[")):
            return metadata

        try:
            decoded = json.loads(metadata)
        except (TypeError, ValueError) as exc:
            raise InvalidMetadataError("Metadata strings must contain valid JSON.") from exc

        if not isinstance(decoded, dict):
            raise InvalidMetadataError("Metadata JSON must contain an object.")

        normalised = _normalise_mapping(cast(dict[str, object], decoded), allow_removal=allow_removal)

        return json.dumps(normalised, ensure_ascii=False, separators=(",", ":"))

    if not isinstance(metadata, Mapping):
        raise InvalidMetadataError("Metadata must be a mapping or a JSON object string.")

    normalised = _normalise_mapping(metadata, allow_removal=allow_removal)

    return json.dumps(normalised, ensure_ascii=False, separators=(",", ":"))


def decode_metadata(value: object) -> dict[str, object]:
    """---
    Decode metadata from the Rentry API.

    #### Arguments
    - value: `object` — The metadata value returned by Rentry.

    #### Returns
    - The decoded metadata mapping.

    #### Raises
    - `ProtocolError` when the returned metadata is invalid.
    """

    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError) as exc:
            raise ProtocolError("The fetch response contains invalid metadata JSON.") from exc

    if value is None:
        return {}

    if not isinstance(value, dict):
        raise ProtocolError("The fetch response metadata must be an object.")

    metadata = cast(dict[object, object], value)

    if not all(isinstance(key, str) for key in metadata):
        raise ProtocolError("The fetch response metadata must be an object.")

    return dict(cast(dict[str, object], metadata))
