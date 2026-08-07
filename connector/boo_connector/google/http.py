"""Tiny HTTP abstraction so the live Google client is testable without network.

`HttpClient` is the interface the live code depends on. `HttpxClient` is the real
implementation (needs `httpx`); tests inject a `FakeHttpClient` with canned responses.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


class HttpError(Exception):
    def __init__(self, status: int, body: Any, message: str = ""):
        super().__init__(message or f"HTTP {status}")
        self.status = status
        self.body = body


@dataclass
class Response:
    status: int
    body: Dict[str, Any]

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class HttpClient:
    def request(self, method: str, url: str, *, headers: Optional[Dict[str, str]] = None,
                params: Optional[Dict[str, Any]] = None, form: Optional[Dict[str, Any]] = None,
                json_body: Optional[Dict[str, Any]] = None) -> Response:
        raise NotImplementedError


class HttpxClient(HttpClient):  # pragma: no cover - exercised only with httpx + network installed
    def __init__(self, timeout: float = 20.0):
        import httpx  # deferred so the package imports without the dependency
        self._httpx = httpx
        self._client = httpx.Client(timeout=timeout)

    def request(self, method, url, *, headers=None, params=None, form=None, json_body=None) -> Response:
        resp = self._client.request(method, url, headers=headers, params=params, data=form, json=json_body)
        try:
            body = resp.json() if resp.content else {}
        except Exception:
            body = {"_raw": resp.text}
        return Response(status=resp.status_code, body=body)


class FakeHttpClient(HttpClient):
    """Test double. `handler(method, url, params, form, json_body, headers) -> Response`."""

    def __init__(self, handler: Callable[..., Response]):
        self._handler = handler
        self.calls = []

    def request(self, method, url, *, headers=None, params=None, form=None, json_body=None) -> Response:
        self.calls.append({"method": method, "url": url, "params": params, "form": form,
                           "json_body": json_body, "headers": headers})
        return self._handler(method=method, url=url, params=params, form=form,
                             json_body=json_body, headers=headers)
