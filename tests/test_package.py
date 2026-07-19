from __future__ import annotations

import importlib
import importlib.metadata
import tomllib
from importlib.metadata import PackageNotFoundError
from pathlib import Path

import pytest

import rentry

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_version_falls_back_when_distribution_metadata_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_version(_: str) -> str:
        raise PackageNotFoundError

    with monkeypatch.context() as patch:
        patch.setattr(importlib.metadata, "version", missing_version)
        importlib.reload(rentry)

        assert rentry.__version__ == "1.0.0"

    importlib.reload(rentry)


def test_public_project_metadata_remains_intentional() -> None:
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert project["description"] == "A synchronous and asynchronous Python client for Rentry."
    assert project["urls"]["Sponsor"] == "https://github.com/sponsors/EtorixDev"
    assert project["urls"]["Donate"] == "https://ko-fi.com/Etorix"
    assert project["license-files"] == ["LICENSE"]
    assert (PROJECT_ROOT / ".github" / "FUNDING.yml").read_text(encoding="utf-8") == ("github: EtorixDev\nko_fi: Etorix\n")
    assert project["classifiers"] == [
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Typing :: Typed",
    ]
    assert (PROJECT_ROOT / "src" / "rentry" / "py.typed").read_bytes() == b""
