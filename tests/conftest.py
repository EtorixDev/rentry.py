from __future__ import annotations

from typing import Any, cast

import niquests


class FakeResponse:
    def __init__(self, payload: object = None, *, status_code: int = 200, text: str = "") -> None:
        self.payload = payload
        self.status_code = status_code
        self.text = text

    def json(self) -> object:
        if isinstance(self.payload, Exception):
            raise self.payload

        return self.payload


class _FakeSessionBase:
    def __init__(self, *responses: FakeResponse) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, Any]] = []
        self.close_calls = 0

    def _respond(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.requests.append({"method": method, "url": url, **kwargs})

        return self.responses.pop(0)


class FakeSession(_FakeSessionBase):
    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        return self._respond(method, url, **kwargs)

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        return self._respond("GET", url, **kwargs)

    def close(self) -> None:
        self.close_calls += 1


class FakeAsyncSession(_FakeSessionBase):
    async def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        return self._respond(method, url, **kwargs)

    async def get(self, url: str, **kwargs: Any) -> FakeResponse:
        return self._respond("GET", url, **kwargs)

    async def close(self) -> None:
        self.close_calls += 1


def session_for_client(session: FakeSession) -> niquests.Session:
    """Adapt a synchronous test session to the public client boundary."""
    return cast(niquests.Session, session)


def session_for_async_client(session: FakeAsyncSession) -> niquests.AsyncSession:
    """Adapt an asynchronous test session to the public client boundary."""
    return cast(niquests.AsyncSession, session)
