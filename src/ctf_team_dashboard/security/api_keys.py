"""API key generation, hashing and verification."""

from __future__ import annotations

import hashlib
import secrets

KEY_PREFIX = "ctfd"
PREFIX_LENGTH = 8
SECRET_BYTES = 32


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key.

    Returns:
        A tuple of ``(plaintext_key, lookup_prefix, secret_hash)``. The
        plaintext key is only ever shown once to the caller.
    """
    prefix = secrets.token_hex(PREFIX_LENGTH // 2)
    secret = secrets.token_hex(SECRET_BYTES)
    plaintext = f"{KEY_PREFIX}_{prefix}_{secret}"
    return plaintext, prefix, hash_secret(secret)


def hash_secret(secret: str) -> str:
    """Return the SHA-256 digest of the secret portion of an API key."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def split_key(plaintext: str) -> tuple[str, str]:
    """Split a plaintext API key into its prefix and secret.

    Args:
        plaintext: The API key presented by the caller.

    Returns:
        A tuple of ``(prefix, secret)``.

    Raises:
        ValueError: When the key does not follow the expected format.
    """
    parts = plaintext.strip().split("_", 2)
    if len(parts) != 3 or parts[0] != KEY_PREFIX or not parts[1] or not parts[2]:
        raise ValueError("Malformed API key")
    return parts[1], parts[2]


def verify_api_key(plaintext: str, expected_hash: str) -> bool:
    """Verify a plaintext API key against a stored digest."""
    try:
        _, secret = split_key(plaintext)
    except ValueError:
        return False
    return secrets.compare_digest(hash_secret(secret), expected_hash)


def mask_key(prefix: str) -> str:
    """Return the display form of an API key."""
    return f"{KEY_PREFIX}_{prefix}_{'*' * 8}"
