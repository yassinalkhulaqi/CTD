"""Security headers and the middleware applying them."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from starlette.responses import Response
from starlette.types import ASGIApp, Scope

DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self' data:; "
    "connect-src 'self' ws: wss:; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "object-src 'none'"
)

SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "X-Permitted-Cross-Domain-Policies": "none",
}

HSTS_HEADER = "Strict-Transport-Security"


class SecurityHeadersMiddleware:
    """A pure ASGI middleware attaching the security headers to every response."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        content_security_policy: str = DEFAULT_CSP,
        enable_hsts: bool = False,
    ) -> None:
        self.app = app
        self.content_security_policy = content_security_policy
        self.enable_hsts = enable_hsts

    async def __call__(
        self,
        scope: Scope,
        receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
        send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
    ) -> None:
        """Attach the security headers to the outgoing response."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: MutableMapping[str, Any]) -> None:
            """Decorate the response headers before they are sent."""
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                existing = {key.lower() for key, _ in headers}
                for header, value in SECURITY_HEADERS.items():
                    encoded = header.lower().encode("latin-1")
                    if encoded not in existing:
                        headers.append((encoded, value.encode("latin-1")))
                if b"content-security-policy" not in existing:
                    headers.append(
                        (
                            b"content-security-policy",
                            self.content_security_policy.encode("latin-1"),
                        )
                    )
                if self.enable_hsts and b"strict-transport-security" not in existing:
                    headers.append(
                        (
                            b"strict-transport-security",
                            b"max-age=31536000; includeSubDomains",
                        )
                    )
            await send(message)

        await self.app(scope, receive, send_wrapper)


def apply_security_headers(response: Response, *, enable_hsts: bool = False) -> Response:
    """Attach the security headers to a response.

    Args:
        response: The response to decorate.
        enable_hsts: Whether the strict transport security header is added.

    Returns:
        The decorated response.
    """
    for header, value in SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    response.headers.setdefault("Content-Security-Policy", DEFAULT_CSP)
    if enable_hsts:
        response.headers.setdefault(HSTS_HEADER, "max-age=31536000; includeSubDomains")
    return response
