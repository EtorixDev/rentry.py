from __future__ import annotations

from importlib.metadata import version

import rentry
from rentry import AsyncClient, Client, Metadata, Page


def main() -> None:
    assert rentry.__version__ == version("rentry.py")
    assert Client.__name__ == "Client"
    assert AsyncClient.__name__ == "AsyncClient"
    assert Metadata.__name__ == "Metadata"
    assert Page.__name__ == "Page"


if __name__ == "__main__":
    main()
