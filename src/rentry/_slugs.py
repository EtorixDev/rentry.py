from __future__ import annotations

import re
from typing import Final
from urllib.parse import urlsplit

from .exceptions import InvalidSlugError

RENTRY_DOMAINS: Final = frozenset({"rentry.co", "rentry.org"})
_SLUG_PATTERN = re.compile(r"^[A-Za-z0-9_-]{2,100}$")


def normalise_slug(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("slug must be a string.")

    candidate = value.strip()
    parsed = urlsplit(candidate)

    if parsed.scheme or parsed.netloc:
        if parsed.scheme.lower() != "https" or parsed.netloc.lower() not in RENTRY_DOMAINS or parsed.query or parsed.fragment:
            raise InvalidSlugError("Page URLs must use https://rentry.co or https://rentry.org without a query or fragment.")

        candidate = parsed.path.strip("/")
    else:
        candidate = candidate.strip("/")

    if not _SLUG_PATTERN.fullmatch(candidate):
        raise InvalidSlugError("Slugs must contain 2 to 100 letters, numbers, underscores, or hyphens.")

    return candidate
