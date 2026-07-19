from __future__ import annotations

import importlib
import importlib.metadata
from importlib.metadata import PackageNotFoundError

import pytest

import rentry


def test_version_falls_back_when_distribution_metadata_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_version(_: str) -> str:
        raise PackageNotFoundError

    with monkeypatch.context() as patch:
        patch.setattr(importlib.metadata, "version", missing_version)
        importlib.reload(rentry)

        assert rentry.__version__ == "1.0.0"

    importlib.reload(rentry)
