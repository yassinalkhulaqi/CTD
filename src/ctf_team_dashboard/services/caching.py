"""Server side response caching with entity tags."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CacheEntry:
    """A cached response with its entity tag."""

    etag: str
    payload: bytes
    stored_at: float
    content_type: str = "application/json"


@dataclass(slots=True)
class ResponseCache:
    """An in-memory cache of API responses keyed by the request path."""

    ttl_seconds: float = 5.0
    max_entries: int = 256
    entries: dict[str, CacheEntry] = field(default_factory=dict)
    hits: int = 0
    misses: int = 0

    def key(self, path: str, params: dict[str, Any] | None = None) -> str:
        """Return the cache key of a request.

        Args:
            path - The path of the request.
            params - The query parameters of the request.

        Returns:
            The cache key.
        """
        if not params:
            return path
        encoded = json.dumps(params, sort_keys=True, separators=(",", ":"), default=str)
        return f"{path}?{encoded}"

    def compute_etag(self, payload: bytes) -> str:
        """Return the entity tag of a payload.

        Args:
            payload - The serialised response.

        Returns:
            The entity tag.
        """
        digest = hashlib.sha256(payload).hexdigest()[:32]
        return f'"{digest}"'

    def get(self, key: str) -> CacheEntry | None:
        """Return a fresh cache entry.

        Args:
            key - The cache key.

        Returns:
            The entry, or ``None`` when it is missing or stale.
        """
        entry = self.entries.get(key)
        if entry is None:
            self.misses += 1
            return None
        if time.monotonic() - entry.stored_at > self.ttl_seconds:
            self.entries.pop(key, None)
            self.misses += 1
            return None
        self.hits += 1
        return entry

    def set(
        self,
        key: str,
        payload: bytes,
        *,
        content_type: str = "application/json",
    ) -> CacheEntry:
        """Store a payload in the cache.

        Args:
            key - The cache key.
            payload - The serialised response.
            content_type - The content type of the response.

        Returns:
            The stored entry.
        """
        entry = CacheEntry(
            etag=self.compute_etag(payload),
            payload=payload,
            stored_at=time.monotonic(),
            content_type=content_type,
        )
        self.entries[key] = entry
        self.prune()
        return entry

    def invalidate(self, key: str) -> None:
        """Remove an entry from the cache."""
        self.entries.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove every entry whose key starts with a prefix.

        Args:
            prefix - The key prefix.

        Returns:
            The number of removed entries.
        """
        stale = [key for key in self.entries if key.startswith(prefix)]
        for key in stale:
            self.entries.pop(key, None)
        return len(stale)

    def clear(self) -> None:
        """Remove every entry from the cache."""
        self.entries.clear()

    def prune(self) -> int:
        """Drop the oldest entries when the cache is full.

        Returns:
            The number of removed entries.
        """
        if len(self.entries) <= self.max_entries:
            return 0
        ordered = sorted(self.entries.items(), key=lambda item: item[1].stored_at)
        excess = len(self.entries) - self.max_entries
        for key, _ in ordered[:excess]:
            self.entries.pop(key, None)
        return excess

    @property
    def hit_rate(self) -> float:
        """Return the ratio of the served entries."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total


def conditional_response(
    cache: ResponseCache,
    key: str,
    payload: bytes,
    *,
    if_none_match: str | None = None,
    content_type: str = "application/json",
) -> tuple[int, bytes, dict[str, str]]:
    """Return a conditional response for a cached payload.

    Args:
        cache: The response cache.
        key - The cache key of the request.
        payload: The serialised response.
        if_none_match: The entity tag sent by the client.
        content_type: The content type of the response.

    Returns:
        A tuple of the status code, the body and the headers.
    """
    entry = cache.get(key)
    if entry is None:
        entry = cache.set(key, payload, content_type=content_type)

    headers = {
        "ETag": entry.etag,
        "Cache-Control": f"private, max-age={int(cache.ttl_seconds)}",
    }

    if if_none_match and if_none_match == entry.etag:
        return 304, b"", headers

    return 200, entry.payload, headers


_cache: ResponseCache | None = None


def get_response_cache() -> ResponseCache:
    """Return the process wide response cache."""
    global _cache
    if _cache is None:
        _cache = ResponseCache()
    return _cache


def reset_response_cache() -> None:
    """Replace the process wide response cache (used by the tests)."""
    global _cache
    _cache = None


def make_cache_key(path: str, params: dict[str, Any] | None = None) -> str:
    """Return the cache key of a request.

    Args:
        path - The path of the request.
        params - The query parameters.

    Returns:
        The cache key.
    """
    return get_response_cache().key(path, params)


__all__ = [
    "CacheEntry",
    "ResponseCache",
    "conditional_response",
    "get_response_cache",
    "make_cache_key",
    "reset_response_cache",
]
