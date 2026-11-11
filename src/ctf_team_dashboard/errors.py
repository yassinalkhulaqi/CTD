"""Typed application errors with a stable HTTP mapping."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any


class DashboardError(Exception):
    """Base class for every error raised by the dashboard."""

    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    code: str = "internal_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}

    def to_payload(self) -> dict[str, Any]:
        """Return the JSON payload used by the API error envelope."""
        payload: dict[str, Any] = {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        if self.details:
            payload["error"]["details"] = self.details
        return payload


class NotFoundError(DashboardError):
    """Raised when a requested resource does not exist."""

    status_code = HTTPStatus.NOT_FOUND
    code = "not_found"


class ValidationError(DashboardError):
    """Raised when user supplied data fails validation."""

    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    code = "validation_error"


class ConflictError(DashboardError):
    """Raised when an operation conflicts with existing state."""

    status_code = HTTPStatus.CONFLICT
    code = "conflict"


class AuthenticationError(DashboardError):
    """Raised when a request lacks valid credentials."""

    status_code = HTTPStatus.UNAUTHORIZED
    code = "unauthenticated"


class PermissionDeniedError(DashboardError):
    """Raised when the caller lacks the required permission."""

    status_code = HTTPStatus.FORBIDDEN
    code = "permission_denied"


class RateLimitError(DashboardError):
    """Raised when a caller exceeds the configured request budget."""

    status_code = HTTPStatus.TOO_MANY_REQUESTS
    code = "rate_limited"

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        retry_after: float = 1.0,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged = {"retry_after": retry_after}
        merged.update(details or {})
        super().__init__(message, details=merged)
        self.retry_after = retry_after
