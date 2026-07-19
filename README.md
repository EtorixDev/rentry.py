# rentry.py

[![PyPI](https://img.shields.io/pypi/v/rentry.py.svg?style=flat-square&color=5677a6)](https://pypi.org/project/rentry.py/)
[![Python](https://img.shields.io/pypi/pyversions/rentry.py.svg?style=flat-square&color=5677a6)](https://pypi.org/project/rentry.py/)
[![Downloads](https://img.shields.io/pypi/dm/rentry.py.svg?style=flat-square&color=5677a6)](https://pypi.org/project/rentry.py/)
[![Build](https://img.shields.io/github/actions/workflow/status/EtorixDev/rentry.py/tests.yml?branch=main&style=flat-square&color=51a851)](https://github.com/EtorixDev/rentry.py/actions/workflows/tests.yml)
[![License](https://img.shields.io/pypi/l/rentry.py.svg?style=flat-square&color=51a851)](https://pypi.org/project/rentry.py/)

A typed synchronous and asynchronous Python client for the [Rentry](https://rentry.co/) Markdown publishing service.


## Installation

```console
pip install rentry.py
```

Or with uv:

```console
uv add rentry.py
```

## Library Usage

```python
from rentry import Client

with Client() as client:
    created = client.create(
        "# Hello\n",
        slug="my-page",
        metadata={"PAGE_TITLE": "Hello!"},
    )

    print(created.url)
    print(created.edit_code)

    client.update(
        created.slug,
        created.edit_code,
        text="# Updated\n",
        metadata={"PAGE_DESCRIPTION": "An updated page!"},
    )

    page = client.fetch(created.slug, created.edit_code)
    print(page.text)
```

```python
import asyncio

from rentry import AsyncClient


async def main() -> None:
    async with AsyncClient() as client:
        created = await client.create("# Hello!\n")
        page = await client.fetch(created.slug, created.edit_code)
        print(page.url)


asyncio.run(main())
```

### Operations

- `create(text, *, metadata=UNSET, slug=None, edit_code=None) -> CreatedPage`
- `fetch(slug, edit_code) -> Page`
- `exists(slug) -> bool`
- `raw(slug, *, access_code=None) -> str`
- `update(...) -> None` for partial, non-destructive upserts
- `replace(..., text=..., metadata=...) -> None` for explicit full replacement
- `delete(slug, edit_code) -> None`

Every operation accepts either a bare slug or a full `https://rentry.co`/`https://rentry.org` page URL. Pass `domain="rentry.org"` to `Client` or `AsyncClient` to use that domain instead of `rentry.co`.

### Safe Updates And Explicit Replacement

`update()` always sends Rentry's `upsert` mode. Omitted text and metadata remain unchanged, an empty text string clears the page text, and a metadata value of `None` removes that option.

```python
client.update(
    "my-page",
    "edit-code",
    metadata={
        "PAGE_TITLE": "New Title",
        "PAGE_DESCRIPTION": None,
    },
)
```

Use `replace()` when you intentionally want to replace the entire document. It requires both `text` and `metadata`, including when either is empty, so an omitted argument cannot silently clear a page.

```python
client.replace("my-page", "edit-code", text="", metadata={})
```

Previously set `SECRET_*` metadata is protected by Rentry. Pass `allow_secret_metadata_changes=True` only when an update should be allowed to change or remove those values.

Set `new_modify_code=None` in `update()` to remove a modify code. New modify codes must begin with `m:`. A modify code can update content and metadata, but the client rejects attempts to rotate the slug or codes with one. Deletion always requires the full edit code.

### Metadata

Known metadata keys are available through the `Metadata` `TypedDict`:

```python
from rentry import Metadata

metadata: Metadata = {
    "PAGE_TITLE": "Example",
    "OPTION_DISABLE_VIEWS": True,
    "CONTENT_TEXT_COLOR": ["black", "white"],
}
```

Mappings, JSON object strings, and Rentry's newline-separated `KEY = value` syntax are accepted. Unknown string keys are passed through deliberately so newly added Rentry options work before the next library release. Detailed option validation remains server-authoritative. See Rentry's [metadata reference](https://rentry.co/metadata-how).

### Errors

All library exceptions derive from `RentryError`. Local input errors use `InvalidSlugError`, `InvalidEditCodeError`, and `InvalidMetadataError`. Connection failures use `TransportError`, malformed server responses use `ProtocolError`, and documented Rentry application statuses map to structured `APIError` subclasses:

- `ValidationError` (`400`)
- `AccessDeniedError` (`403`)
- `NotFoundError` (`404`)
- `MethodNotAllowedError` (`405`)
- `RateLimitError` (`429`)
- `ServiceUnavailableError` (`503`)

`APIError` exposes the original `status`, `content`, and `errors` fields.

### Session Injection

Pass an existing `niquests.Session` or `niquests.AsyncSession` through `session=` to integrate with application-owned transport configuration. Injected sessions are never closed by the client. Sessions created by the client are closed by `close()`/`aclose()` or the context manager.

## Command Line

The installed `rentry` command provides the same service operations:

```console
rentry create "# Hello"
rentry create --file page.md --metadata-file metadata.json --slug my-page
rentry fetch my-page --edit-code EDIT_CODE
rentry exists my-page
rentry raw my-page --access-code ACCESS_CODE
rentry update my-page --edit-code EDIT_CODE --text "# Updated"
rentry replace my-page --edit-code EDIT_CODE --file page.md --metadata '{}'
rentry delete my-page --edit-code EDIT_CODE
```

Create and fetch results are JSON, mutation success is `{"ok": true}`, and errors go to stderr with a nonzero exit status. `create`, `update`, and `replace` support UTF-8 files and stdin. Use `rentry --help` or `rentry COMMAND --help` for all options.

Global options such as `--domain` and `--timeout` go before the command:

```console
rentry --domain rentry.org --timeout 15 exists my-page
```

## Development

Install the locked development environment and run the complete local gate:

```console
uv sync --frozen
uv run python scripts/verify.py
```

The verifier compiles every Python file, enforces custom styling, checks Ruff formatting and lint, runs strict Pyright, and executes the test suite.
