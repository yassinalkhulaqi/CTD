"""Caching middleware adding entity tags and conditional responses."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from ctf_team_dashboard.services.caching import ResponseCache, get_response_cache

CACHEABLE_PREFIXES = ("/api/stats/", "/api/dashboard", "/api/teams", "/api/challenges")


class CacheMiddleware:
    """A pure ASGI middleware caching the read only API responses.

    The middleware buffers the response of a cacheable route, computes its
    entity tag and answers a conditional request with a ``304`` status.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        cache: ResponseCache | None = None,
        prefixes: tuple[str, ...] = CACHEABLE_PREFIXES,
    ) -> None:
        self.app = app
        self.cache = cache or get_response_cache()
        self.prefixes = prefixes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Serve the cached response when the client already holds it."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        if request.method != "GET" or not self._is_cacheable(request.url.path):
            await self.app(scope, receive, send)
            return

        key = request.url.path
        if request.url.query:
            key = f"{key}?{request.url.query}"

        status, headers, body = await self._capture(scope, receive)

        if status != 200:
            await self._forward(send, status, headers, body)
            return

        entry = self.cache.set(key, body)

        if_none_match = request.headers.get("if-none-match")
        if if_none_match and if_none_match == entry.etag:
            await send(
                {
                    "type": "http.response.start",
                    "status": 304,
                    "headers": [
                        (b"etag", entry.etag.encode("latin-1")),
                        (
                            b"cache-control",
                            f"private, max-age={int(self.cache.ttl_seconds)}".encode(),
                        ),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": b""})
            return

        enriched = [
            *headers,
            (b"etag", entry.etag.encode("latin-1")),
            (b"cache-control", f"private, max-age={int(self.cache.ttl_seconds)}".encode()),
        ]
        await self._forward(send, status, enriched, body)

    def _is_cacheable(self, path: str) -> bool:
        """Return whether a path may be cached."""
        return any(path.startswith(prefix) for prefix in self.prefixes)

    async def _capture(
        self, scope: Scope, receive: Receive
    ) -> tuple[int, list[tuple[bytes, bytes]], bytes]:
        """Run the application and capture its response."""
        status = 200
        headers: list[tuple[bytes, bytes]] = []
        chunks: list[bytes] = []

        async def capture(message: MutableMapping[str, Any]) -> None:
            """Record the response without forwarding it."""
            nonlocal status, headers
            if message["type"] == "http.response.start":
                status = int(message["status"])
                headers = list(message.get("headers", []))
            elif message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))

        await self.app(scope, receive, capture)
        return status, headers, b"".join(chunks)

    async def _forward(
        self,
        send: Send,
        status: int,
        headers: list[tuple[bytes, bytes]],
        body: bytes,
    ) -> None:
        """Send a captured response to the client."""
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": headers,
            }
        )
        await send({"type": "http.response.body", "body": body})


def make_cache_middleware(app: ASGIApp) -> ASGIApp:
    """Return an application wrapped with the cache middleware.

    Args:
        app - The application to wrap.

    Returns:
        The wrapped application.
    """
    return CacheMiddleware(app)


__all__ = ["CACHEABLE_PREFIXES", "CacheMiddleware", "make_cache_middleware"]
