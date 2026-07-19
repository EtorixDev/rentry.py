from __future__ import annotations

import argparse
import json
import runpy
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from types import MappingProxyType
from typing import Any, ClassVar, cast

import pytest

import rentry.cli as cli
from rentry import Client, CreatedPage, Page, RentryError


class FakeClient:
    instances: ClassVar[list[FakeClient]] = []

    def __init__(self, domain: str, **kwargs: Any) -> None:
        self.domain = domain
        self.kwargs = kwargs
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []
        self.instances.append(self)

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, *_: object) -> None:
        pass

    def create(self, *args: object, **kwargs: object) -> CreatedPage:
        self.calls.append(("create", args, kwargs))

        return CreatedPage("example", "https://rentry.co/example", "example", "secret")

    def fetch(self, *args: object, **kwargs: object) -> Page:
        self.calls.append(("fetch", args, kwargs))

        return Page(
            slug="example",
            url="https://rentry.co/example",
            text="markdown",
            metadata=MappingProxyType({"COLORS": ("red", "blue")}),
            views=3,
            published_at=datetime(2026, 7, 18, 1, 2, 3),
        )

    def exists(self, *args: object, **kwargs: object) -> bool:
        self.calls.append(("exists", args, kwargs))

        return True

    def raw(self, *args: object, **kwargs: object) -> str:
        self.calls.append(("raw", args, kwargs))

        return "raw markdown"

    def update(self, *args: object, **kwargs: object) -> None:
        self.calls.append(("update", args, kwargs))

    def replace(self, *args: object, **kwargs: object) -> None:
        self.calls.append(("replace", args, kwargs))

    def delete(self, *args: object, **kwargs: object) -> None:
        self.calls.append(("delete", args, kwargs))


class TTYStringIO(StringIO):
    def isatty(self) -> bool:
        return True


def test_help_is_parsed_before_a_client_is_constructed(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_constructed(*_: object, **__: object) -> None:
        raise AssertionError("Client should not be constructed for --help.")

    monkeypatch.setattr(cli, "Client", fail_if_constructed)

    with pytest.raises(SystemExit) as raised:
        cli.main(["--help"])

    assert raised.value.code == 0


def test_help_and_parser_errors_use_punctuation(capsys: pytest.CaptureFixture[str]) -> None:
    parser = cli.build_parser()

    assert "Create and manage Rentry pages." in parser.format_help()
    assert "Show this help message and exit." in parser.format_help()

    with pytest.raises(SystemExit, match="2"):
        parser.parse_args(["--domain", "example", "exists", "example"])

    assert capsys.readouterr().err.rstrip().endswith(".")


def test_create_cli_preserves_text_and_prints_machine_readable_output(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    FakeClient.instances.clear()
    monkeypatch.setattr(cli, "Client", FakeClient)
    result = cli.main(["--timeout", "12", "create", "  exact text  ", "--metadata", '{"PAGE_TITLE":"Hi"}'])
    output = json.loads(capsys.readouterr().out)
    instance = FakeClient.instances[0]

    assert result == 0
    assert output == {
        "slug": "example",
        "url": "https://rentry.co/example",
        "short_url": "example",
        "edit_code": "secret",
    }
    assert instance.kwargs["timeout"] == 12
    assert instance.calls == [
        (
            "create",
            ("  exact text  ",),
            {"metadata": '{"PAGE_TITLE":"Hi"}', "slug": None, "edit_code": None},
        )
    ]


def test_create_alias_reads_text_and_metadata_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    text_path = tmp_path / "page.md"
    metadata_path = tmp_path / "metadata.txt"
    text_path.write_text("  from file\n", encoding="utf-8")
    metadata_path.write_text("PAGE_TITLE = File", encoding="utf-8")
    FakeClient.instances.clear()
    monkeypatch.setattr(cli, "Client", FakeClient)
    result = cli.main(["new", "--file", str(text_path), "--metadata-file", str(metadata_path)])

    assert result == 0
    assert FakeClient.instances[0].calls[0] == (
        "create",
        ("  from file\n",),
        {"metadata": "PAGE_TITLE = File", "slug": None, "edit_code": None},
    )


def test_create_reads_piped_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeClient.instances.clear()
    monkeypatch.setattr(cli, "Client", FakeClient)
    monkeypatch.setattr(sys, "stdin", StringIO("piped markdown\n"))

    assert cli.main(["create"]) == 0
    assert FakeClient.instances[0].calls[0][1] == ("piped markdown\n",)


def test_dash_file_reads_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeClient.instances.clear()
    monkeypatch.setattr(cli, "Client", FakeClient)
    monkeypatch.setattr(sys, "stdin", StringIO("dash markdown"))

    assert cli.main(["create", "--file", "-"]) == 0
    assert FakeClient.instances[0].calls[0][1] == ("dash markdown",)


@pytest.mark.parametrize(
    ("argv", "operation", "expected_output"),
    [
        (["exists", "example"], "exists", "true\n"),
        (["raw", "example", "--access-code", "raw-code"], "raw", "raw markdown"),
        (["delete", "example", "--edit-code", "edit"], "delete", '{"ok": true}\n'),
    ],
)
def test_simple_commands(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
    operation: str,
    expected_output: str,
) -> None:
    FakeClient.instances.clear()
    monkeypatch.setattr(cli, "Client", FakeClient)

    assert cli.main(argv) == 0
    assert capsys.readouterr().out == expected_output
    assert FakeClient.instances[0].calls[0][0] == operation


def test_fetch_prints_the_complete_snapshot(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    FakeClient.instances.clear()
    monkeypatch.setattr(cli, "Client", FakeClient)

    assert cli.main(["fetch", "example", "--edit-code", "edit"]) == 0

    output = json.loads(capsys.readouterr().out)

    assert output == {
        "slug": "example",
        "url": "https://rentry.co/example",
        "text": "markdown",
        "metadata": {"COLORS": ["red", "blue"]},
        "views": 3,
        "published_at": "2026-07-18T01:02:03",
        "activated_at": None,
        "edited_at": None,
        "modify_code_set": None,
        "metadata_version": None,
    }


def test_update_reads_files_and_forwards_every_option(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    text_path = tmp_path / "page.md"
    metadata_path = tmp_path / "metadata.json"
    text_path.write_text("replacement", encoding="utf-8")
    metadata_path.write_text("{}", encoding="utf-8")
    FakeClient.instances.clear()
    monkeypatch.setattr(cli, "Client", FakeClient)

    result = cli.main(
        [
            "update",
            "example",
            "--edit-code",
            "edit",
            "--text-file",
            str(text_path),
            "--metadata-file",
            str(metadata_path),
            "--new-slug",
            "renamed",
            "--new-edit-code",
            "new-edit",
            "--clear-modify-code",
            "--allow-secret-metadata-changes",
        ]
    )

    assert result == 0
    assert FakeClient.instances[0].calls[0] == (
        "update",
        ("example", "edit"),
        {
            "text": "replacement",
            "metadata": "{}",
            "new_slug": "renamed",
            "new_edit_code": "new-edit",
            "new_modify_code": None,
            "allow_secret_metadata_changes": True,
        },
    )


def test_update_forwards_direct_values(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeClient.instances.clear()
    monkeypatch.setattr(cli, "Client", FakeClient)

    result = cli.main(
        [
            "update",
            "example",
            "--edit-code",
            "edit",
            "--text",
            "replacement",
            "--new-modify-code",
            "m:shared",
        ]
    )

    assert result == 0
    assert FakeClient.instances[0].calls[0][2]["text"] == "replacement"
    assert FakeClient.instances[0].calls[0][2]["new_modify_code"] == "m:shared"


def test_replace_forwards_complete_content(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeClient.instances.clear()
    monkeypatch.setattr(cli, "Client", FakeClient)

    result = cli.main(
        [
            "replace",
            "example",
            "new text",
            "--edit-code",
            "edit",
            "--metadata",
            "{}",
            "--allow-secret-metadata-changes",
        ]
    )

    assert result == 0
    assert FakeClient.instances[0].calls[0] == (
        "replace",
        ("example", "edit"),
        {"text": "new text", "metadata": "{}", "allow_secret_metadata_changes": True},
    )


def test_text_input_conflicts_and_missing_tty_input_are_parser_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    text_path = tmp_path / "page.md"
    text_path.write_text("file", encoding="utf-8")

    with pytest.raises(SystemExit, match="2"):
        cli.main(["create", "direct", "--file", str(text_path)])

    stdin = TTYStringIO()
    monkeypatch.setattr(sys, "stdin", stdin)

    with pytest.raises(SystemExit, match="2"):
        cli.main(["create"])


def test_update_text_input_conflict_is_a_parser_error(tmp_path: Path) -> None:
    text_path = tmp_path / "page.md"
    text_path.write_text("file", encoding="utf-8")

    with pytest.raises(SystemExit, match="2"):
        cli.main(["update", "example", "--edit-code", "edit", "--text", "direct", "--text-file", str(text_path)])


def test_main_reports_expected_operational_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class FailingClient(FakeClient):
        def exists(self, *args: object, **kwargs: object) -> bool:
            raise RentryError("service failure")

    monkeypatch.setattr(cli, "Client", FailingClient)

    assert cli.main(["exists", "example"]) == 1
    assert capsys.readouterr().err == "rentry: service failure.\n"


def test_helpers_reject_unknown_values() -> None:
    with pytest.raises(TypeError, match="Cannot serialize object"):
        cli._json_default(object())  # pyright: ignore[reportPrivateUsage]

    parser = cli.build_parser()
    args = argparse.Namespace(command="unknown")
    client = cast(Client, FakeClient("rentry.co"))

    with pytest.raises(SystemExit, match="2"):
        cli._run_command(args, parser, client)  # pyright: ignore[reportPrivateUsage]


def test_main_uses_process_arguments_and_module_entrypoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["rentry", "--help"])

    with pytest.warns(RuntimeWarning, match="found in sys.modules"), pytest.raises(SystemExit) as raised:
        runpy.run_module("rentry.cli", run_name="__main__")

    assert raised.value.code == 0
