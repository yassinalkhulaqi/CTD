"""Stateless JSON Web Token implementation using the HS256 algorithm.

Implementing the small subset of RFC 7519 that the dashboard needs keeps the
runtime free of extra dependencies while remaining fully interoperable with
any standard JWT verifier.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any

from ctf_team_dashboard.errors import AuthenticationError

ALGORITHM = "HS256"
HEADER = {"alg": ALGORITHM, "typ": "JWT"}


class TokenError(AuthenticationError):
    """Raised when a token cannot be decoded or has been tampered with."""

    code = "invalid_token"


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """Decoded payload of a dashboard token."""

    subject: str
    role: str
    team_id: str | None
    token_type: str
    issued_at: int
    expires_at: int
    token_id: str

    @property
    def is_expired(self) -> bool:
        """Return whether the token expiry has passed."""
        return self.expires_at <= int(time.time())

    def to_payload(self) -> dict[str, Any]:
        """Return the claims as a JSON serialisable dictionary."""
        return {
            "sub": self.subject,
            "role": self.role,
            "team_id": self.team_id,
            "typ": self.token_type,
            "iat": self.issued_at,
            "exp": self.expires_at,
            "jti": self.token_id,
        }


def _b64encode(raw: bytes) -> str:
    """Base64url encode bytes without padding."""
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(raw: str) -> bytes:
    """Base64url decode a string, restoring the removed padding."""
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def _sign(signing_input: bytes, secret: str) -> bytes:
    """Compute the HMAC-SHA256 signature for the signing input."""
    return hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()


def encode_token(
    *,
    subject: str,
    role: str,
    secret: str,
    ttl_seconds: int,
    team_id: str | None = None,
    token_type: str = "access",
    issued_at: int | None = None,
    token_id: str | None = None,
) -> str:
    """Encode a signed JWT for the given subject.

    Args:
        subject: The user identifier.
        role: The role claim.
        secret: The signing secret.
        ttl_seconds: Lifetime of the token in seconds.
        team_id: Optional team scope.
        token_type: Either ``access`` or ``refresh``.
        issued_at: Override for the issued-at claim.
        token_id: Override for the unique token identifier claim.

    Returns:
        The encoded token.
    """
    now = int(issued_at if issued_at is not None else time.time())
    claims = TokenClaims(
        subject=subject,
        role=role,
        team_id=team_id,
        token_type=token_type,
        issued_at=now,
        expires_at=now + max(1, ttl_seconds),
        token_id=token_id if token_id is not None else secrets.token_hex(12),
    )
    header_segment = _b64encode(json.dumps(HEADER, separators=(",", ":")).encode("utf-8"))
    payload_segment = _b64encode(
        json.dumps(claims.to_payload(), separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = _b64encode(_sign(signing_input, secret))
    return f"{header_segment}.{payload_segment}.{signature}"


def decode_token(token: str, *, secret: str, verify_exp: bool = True) -> TokenClaims:
    """Decode and verify a signed JWT.

    Args:
        token: The encoded token.
        secret: The signing secret.
        verify_exp: Whether the expiry claim should be enforced.

    Returns:
        The decoded claims.

    Raises:
        TokenError: When the token is malformed, tampered with or expired.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenError("Token is malformed")

    header_segment, payload_segment, signature_segment = parts
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    expected = _b64encode(_sign(signing_input, secret))
    if not hmac.compare_digest(expected, signature_segment):
        raise TokenError("Token signature verification failed")

    try:
        payload = json.loads(_b64decode(payload_segment))
    except (ValueError, TypeError) as exc:
        raise TokenError("Token payload is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise TokenError("Token payload must be an object")

    try:
        claims = TokenClaims(
            subject=str(payload["sub"]),
            role=str(payload["role"]),
            team_id=payload.get("team_id"),
            token_type=str(payload.get("typ", "access")),
            issued_at=int(payload["iat"]),
            expires_at=int(payload["exp"]),
            token_id=str(payload["jti"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise TokenError("Token payload is missing required claims") from exc

    if verify_exp and claims.is_expired:
        raise TokenError("Token has expired")

    return claims


def token_expiry(token: str) -> int:
    """Return the expiry timestamp of a token without verifying it."""
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenError("Token is malformed")
    payload = json.loads(_b64decode(parts[1]))
    return int(payload["exp"])


def peek_subject(token: str) -> str:
    """Return the subject claim of a token without verifying it."""
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenError("Token is malformed")
    payload = json.loads(_b64decode(parts[1]))
    return str(payload.get("sub", ""))
