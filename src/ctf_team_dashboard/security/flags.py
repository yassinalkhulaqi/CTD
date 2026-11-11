"""Flag parsing and validation helpers."""

from __future__ import annotations

import re

FLAG_PATTERN = re.compile(r"^[A-Za-z0-9_]{1,32}\{[^{}]{1,200}\}$")


class FlagFormatError(ValueError):
    """Raised when a flag does not follow the expected format."""


def normalise_flag(raw: str) -> str:
    """Return the canonical representation of a flag.

    Args:
        raw: The flag submitted by the analyst.

    Returns:
        The trimmed flag.

    Raises:
        FlagFormatError: When the flag does not follow the expected format.
    """
    cleaned = raw.strip()
    if not cleaned:
        raise FlagFormatError("A flag must not be empty")
    if len(cleaned) > 256:
        raise FlagFormatError("A flag must not exceed 256 characters")
    if not FLAG_PATTERN.match(cleaned):
        raise FlagFormatError("A flag must look like prefix{content}")
    return cleaned


def is_valid_flag(raw: str) -> bool:
    """Return whether a flag follows the expected format.

    Args:
        raw: The flag to validate.

    Returns:
        ``True`` when the format is valid.
    """
    try:
        normalise_flag(raw)
    except FlagFormatError:
        return False
    return True


def mask_flag(raw: str) -> str:
    """Return a redacted representation of a flag.

    Args:
        raw: The flag to redact.

    Returns:
        The redacted flag, keeping the prefix and the last characters.
    """
    cleaned = raw.strip()
    prefix, separator, _ = cleaned.partition("{")
    if separator:
        return f"{prefix}{{****}}"
    if len(cleaned) <= 8:
        return "*" * len(cleaned)
    return f"{cleaned[:4]}{'*' * (len(cleaned) - 6)}{cleaned[-2:]}"
