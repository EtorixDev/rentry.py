from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn, cast

from .client import DEFAULT_DOMAIN, UNSET, Client, UnsetType
from .exceptions import RentryError
from .models import CreatedPage, Page


def _punctuate(message: str) -> str:
    message = message.rstrip()

    return message if message.endswith((".", "!", "?")) else f"{message}."


class _ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["add_help"] = False
        super().__init__(*args, **kwargs)
        self.add_argument("-h", "--help", action="help", help="Show this help message and exit.")

    def error(self, message: str) -> NoReturn:
        super().error(_punctuate(message))


def _add_text_input(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("text", nargs="?", help="Markdown text; reads stdin when omitted.")
    parser.add_argument("--file", type=Path, help="Read Markdown from a UTF-8 file; use - for stdin.")


def _add_metadata_input(parser: argparse.ArgumentParser, *, required: bool = False) -> None:
    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument("--metadata", help="Metadata as JSON or newline-separated KEY = value pairs.")
    group.add_argument("--metadata-file", type=Path, help="Read metadata from a UTF-8 file.")


def _add_page_credentials(parser: argparse.ArgumentParser, *, allow_modify: bool = True) -> None:
    parser.add_argument("slug", help="Bare page slug or full Rentry URL.")
    code_help = "Full edit code or modify code." if allow_modify else "Full edit code."
    parser.add_argument("--edit-code", required=True, help=code_help)


def build_parser() -> argparse.ArgumentParser:
    """
    Build the Rentry command-line argument parser.

    #### Returns
    - The configured argument parser.
    """

    parser = _ArgumentParser(prog="rentry", description="Create and manage Rentry pages.")
    parser.add_argument("--domain", choices=("rentry.co", "rentry.org"), default=DEFAULT_DOMAIN, help="Rentry domain.")
    parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout in seconds.")
    parser.add_argument("--user-agent", help="Custom User-Agent value.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create", aliases=["new"], help="Create a page.")
    _add_text_input(create)
    _add_metadata_input(create)
    create.add_argument("--slug", help="Requested custom slug.")
    create.add_argument("--edit-code", help="Requested custom edit code.")
    fetch = subparsers.add_parser("fetch", help="Fetch a page using an edit or modify code.")
    _add_page_credentials(fetch)
    exists = subparsers.add_parser("exists", help="Check whether a page exists.")
    exists.add_argument("slug", help="Bare page slug or full Rentry URL.")
    raw = subparsers.add_parser("raw", help="Read a page's raw Markdown.")
    raw.add_argument("slug", help="Bare page slug or full Rentry URL.")
    raw.add_argument("--access-code", help="Rentry-issued raw access code.")
    update = subparsers.add_parser("update", help="Partially update a page without clearing omitted fields.")
    _add_page_credentials(update)
    update.add_argument("--text", default=UNSET, help="New Markdown text; an empty string clears it.")
    update.add_argument("--text-file", type=Path, help="Read new Markdown from a UTF-8 file; use - for stdin.")
    _add_metadata_input(update)
    update.add_argument("--new-slug", default=UNSET, help="New page slug.")
    update.add_argument("--new-edit-code", default=UNSET, help="New full edit code.")
    modify_group = update.add_mutually_exclusive_group()
    modify_group.add_argument("--new-modify-code", default=UNSET, help="New modify code with the required m: prefix.")
    modify_group.add_argument("--clear-modify-code", action="store_true", help="Remove the modify code.")
    update.add_argument("--allow-secret-metadata-changes", action="store_true", help="Allow changes to SECRET_* metadata options.")
    replace = subparsers.add_parser("replace", help="Replace all page text and metadata explicitly.")
    _add_page_credentials(replace)
    _add_text_input(replace)
    _add_metadata_input(replace, required=True)
    replace.add_argument("--allow-secret-metadata-changes", action="store_true", help="Allow changes to SECRET_* metadata options.")
    delete = subparsers.add_parser("delete", help="Delete a page.")
    _add_page_credentials(delete, allow_modify=False)

    return parser


def _read_path(path: Path) -> str:
    if str(path) == "-":
        return sys.stdin.read()

    return path.read_text(encoding="utf-8")


def _read_text(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    text = getattr(args, "text", None)
    path = getattr(args, "file", None)

    if text is not None and path is not None:
        parser.error("Markdown text and --file cannot be used together.")

    if path is not None:
        return _read_path(path)

    if text is not None:
        return text

    if sys.stdin.isatty():
        parser.error("Provide Markdown text, --file, or piped stdin.")

    return sys.stdin.read()


def _read_metadata(args: argparse.Namespace) -> str | UnsetType:
    metadata = getattr(args, "metadata", None)
    path = getattr(args, "metadata_file", None)

    if path is not None:
        return _read_path(path)

    return metadata if metadata is not None else UNSET


def _json_default(value: object) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()

    raise TypeError(f"Cannot serialize {type(value).__name__}.")


def _print_created(page: CreatedPage) -> None:
    print(
        json.dumps(
            {"slug": page.slug, "url": page.url, "short_url": page.short_url, "edit_code": page.edit_code},
            ensure_ascii=False,
        )
    )


def _print_page(page: Page) -> None:
    print(
        json.dumps(
            {
                "slug": page.slug,
                "url": page.url,
                "text": page.text,
                "metadata": dict(page.metadata),
                "views": page.views,
                "published_at": page.published_at,
                "activated_at": page.activated_at,
                "edited_at": page.edited_at,
                "modify_code_set": page.modify_code_set,
                "metadata_version": page.metadata_version,
            },
            ensure_ascii=False,
            default=_json_default,
        )
    )


def _run_command(args: argparse.Namespace, parser: argparse.ArgumentParser, client: Client) -> None:
    if args.command in {"create", "new"}:
        text = _read_text(args, parser)
        metadata = _read_metadata(args)
        page = client.create(text, metadata=metadata, slug=args.slug, edit_code=args.edit_code)
        _print_created(page)

        return

    if args.command == "fetch":
        _print_page(client.fetch(args.slug, args.edit_code))

        return

    if args.command == "exists":
        print(json.dumps(client.exists(args.slug)))

        return

    if args.command == "raw":
        sys.stdout.write(client.raw(args.slug, access_code=args.access_code))

        return

    if args.command == "update":
        if args.text_file is not None and args.text is not UNSET:
            parser.error("--text and --text-file cannot be used together.")

        text = _read_path(args.text_file) if args.text_file is not None else args.text
        metadata = _read_metadata(args)
        new_modify_code = None if args.clear_modify_code else args.new_modify_code

        client.update(
            args.slug,
            args.edit_code,
            text=text,
            metadata=metadata,
            new_slug=args.new_slug,
            new_edit_code=args.new_edit_code,
            new_modify_code=new_modify_code,
            allow_secret_metadata_changes=args.allow_secret_metadata_changes,
        )

        print('{"ok": true}')

        return

    if args.command == "replace":
        text = _read_text(args, parser)
        metadata = _read_metadata(args)

        client.replace(
            args.slug,
            args.edit_code,
            text=text,
            metadata=cast(str, metadata),
            allow_secret_metadata_changes=args.allow_secret_metadata_changes,
        )

        print('{"ok": true}')

        return

    if args.command == "delete":
        client.delete(args.slug, args.edit_code)
        print('{"ok": true}')

        return

    parser.error(f"Unknown command: {args.command}.")


def main(argv: list[str] | None = None) -> int:
    """---
    Run the Rentry command-line client.

    #### Arguments
    - argv: `list[str] | None = None` — Arguments to parse instead of `sys.argv`.

    #### Returns
    - `0` when the command succeeds, otherwise `1`.
    """

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        with Client(
            args.domain,
            timeout=args.timeout,
            user_agent=args.user_agent,
        ) as client:
            _run_command(args, parser, client)
    except (OSError, RentryError, ValueError) as exc:
        print(f"rentry: {_punctuate(str(exc))}", file=sys.stderr)

        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
