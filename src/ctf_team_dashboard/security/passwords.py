"""Password hashing utilities based on PBKDF2-HMAC-SHA256.

The standard library is sufficient for password hashing which keeps the
deployment footprint at zero additional native dependencies.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 240_000
SALT_BYTES = 16
KEY_LENGTH = 32


def generate_salt() -> bytes:
    """Return a cryptographically secure random salt."""
    return secrets.token_bytes(SALT_BYTES)


def hash_password(
    password: str,
    *,
    salt: bytes | None = None,
    iterations: int = DEFAULT_ITERATIONS,
) -> str:
    """Hash a password into a self describing string.

    Args:
        password: The plain text password.
        salt: Optional salt, generated when omitted.
        iterations: The PBKDF2 iteration count.

    Returns:
        A string of the form ``pbkdf2_sha256$iterations$salt$hash``.
    """
    if not password:
        raise ValueError("Password must not be empty")
    resolved_salt = salt if salt is not None else generate_salt()
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), resolved_salt, iterations)
    return "$".join(
        (
            ALGORITHM,
            str(iterations),
            _b64encode(resolved_salt),
            _b64encode(derived),
        )
    )


def verify_password(password: str, encoded: str) -> bool:
    """Verify a plain text password against an encoded hash.

    Args:
        password: The plain text password to verify.
        encoded: The stored hash produced by :func:`hash_password`.

    Returns:
        ``True`` when the password matches, ``False`` otherwise.
    """
    try:
        algorithm, raw_iterations, raw_salt, raw_hash = encoded.split("$")
        if algorithm != ALGORITHM:
            return False
        iterations = int(raw_iterations)
        salt = _b64decode(raw_salt)
        expected = _b64decode(raw_hash)
    except (ValueError, TypeError):
        return False

    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations, len(expected)
    )
    return hmac.compare_digest(candidate, expected)


def needs_rehash(encoded: str, *, iterations: int = DEFAULT_ITERATIONS) -> bool:
    """Return whether a stored hash should be upgraded to a newer cost."""
    try:
        algorithm, raw_iterations, _, _ = encoded.split("$")
    except ValueError:
        return True
    if algorithm != ALGORITHM:
        return True
    try:
        return int(raw_iterations) < iterations
    except ValueError:
        return True


def _b64encode(raw: bytes) -> str:
    """Base64 encode bytes using the URL safe alphabet without padding."""
    import base64

    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(raw: str) -> bytes:
    """Base64 decode a URL safe string, restoring the removed padding."""
    import base64

    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)
