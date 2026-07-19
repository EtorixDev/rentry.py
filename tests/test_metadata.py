from __future__ import annotations

import pytest

from rentry import InvalidMetadataError, ProtocolError
from rentry.metadata import decode_metadata, encode_metadata


def test_metadata_accepts_json_and_native_syntax() -> None:
    assert encode_metadata('{"PAGE_TITLE":"Hello"}') == '{"PAGE_TITLE":"Hello"}'
    assert encode_metadata("PAGE_TITLE = Hello\nCONTAINER_MAX_WIDTH = 600px") == ("PAGE_TITLE = Hello\nCONTAINER_MAX_WIDTH = 600px")


def test_metadata_does_not_mutate_sequence_inputs() -> None:
    colors = ["grey", "red"]

    assert encode_metadata({"CONTENT_TEXT_COLOR": colors}) == '{"CONTENT_TEXT_COLOR":["grey","red"]}'
    assert colors == ["grey", "red"]


@pytest.mark.parametrize(
    "metadata",
    [
        "{broken",
        "[]",
        {"PAGE_TITLE": None},
        {"CONTENT_TEXT_COLOR": ["red", 3]},
        {"PAGE_TITLE": object()},
        {"": "value"},
        object(),
    ],
)
def test_invalid_metadata_is_rejected(metadata: object) -> None:
    with pytest.raises(InvalidMetadataError):
        encode_metadata(metadata)  # type: ignore[arg-type]


def test_fetch_metadata_accepts_json_strings() -> None:
    assert decode_metadata('{"PAGE_TITLE":"Hello"}') == {"PAGE_TITLE": "Hello"}


def test_metadata_removal_is_encoded_only_for_updates() -> None:
    assert encode_metadata({"PAGE_TITLE": None}, allow_removal=True) == '{"PAGE_TITLE":""}'
    assert encode_metadata('{"PAGE_TITLE":null}', allow_removal=True) == '{"PAGE_TITLE":""}'


def test_fetch_metadata_accepts_null_and_rejects_malformed_values() -> None:
    assert decode_metadata(None) == {}

    malformed_values: tuple[object, ...] = ("{broken", [], {1: "value"})

    for value in malformed_values:
        with pytest.raises(ProtocolError):
            decode_metadata(value)
