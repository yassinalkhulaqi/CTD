"""Token bucket rate limiting for the API."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field

from ctf_team_dashboard.errors import RateLimitError


@dataclass(slots=True)
class Bucket:
    """A sliding window rate limiter bucket."""

    limit: int
    window_seconds: float
    timestamps: deque[float] = field(default_factory=deque)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    async def consume(self, *, now: float | None = None) -> bool:
        """Consume a token from the bucket.

        Args:
            now: The current timestamp, defaults to the monotonic clock.

        Returns:
            ``True`` when a token was available.
        """
        moment = now if now is not None else time.monotonic()
        async with self._lock:
            threshold = moment - self.window_seconds
            while self.timestamps and self.timestamps[0] <= threshold:
                self.timestamps.popleft()
            if len(self.timestamps) >= self.limit:
                return False
            self.timestamps.append(moment)
            return True

    async def retry_after(self, *, now: float | None = None) -> float:
        """Return the number of seconds before a token becomes available.

        Args:
            now: The current timestamp, defaults to the monotonic clock.

        Returns:
            The delay in seconds, zero when a token is available.
        """
        moment = now if now is not None else time.monotonic()
        async with self._lock:
            if len(self.timestamps) < self.limit:
                return 0.0
            threshold = moment - self.window_seconds
            while self.timestamps and self.timestamps[0] <= threshold:
                self.timestamps.popleft()
            if len(self.timestamps) < self.limit:
                return 0.0
            oldest = self.timestamps[0]
            return max(0.0, oldest + self.window_seconds - moment)

    @property
    def used(self) -> int:
        """Return the number of tokens consumed inside the window."""
        return len(self.timestamps)


class RateLimiter:
    """A per key rate limiter built on top of sliding window buckets."""

    def __init__(self, *, limit: int = 240, window_seconds: float = 60.0) -> None:
        self.limit = max(1, limit)
        self.window_seconds = max(0.1, window_seconds)
        self._buckets: dict[str, Bucket] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> None:
        """Consume a token for a key, raising when the budget is exhausted.

        Args:
            key: The identity of the caller.

        Raises:
            RateLimitError: When the caller exceeded the request budget.
        """
        if not await self._consume(key):
            retry_after = await self.retry_after(key)
            raise RateLimitError(
                "Rate limit exceeded, slow down",
                retry_after=round(retry_after, 3),
                details={"limit": self.limit, "window_seconds": self.window_seconds},
            )

    async def _consume(self, key: str) -> bool:
        bucket = await self._bucket(key)
        return await bucket.consume()

    async def retry_after(self, key: str) -> float:
        """Return the delay before the caller may retry."""
        bucket = await self._bucket(key)
        return await bucket.retry_after()

    async def _bucket(self, key: str) -> Bucket:
        async with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = Bucket(limit=self.limit, window_seconds=self.window_seconds)
                self._buckets[key] = bucket
            return bucket

    async def used(self, key: str) -> int:
        """Return the number of tokens consumed by a key."""
        bucket = await self._bucket(key)
        return bucket.used

    async def reset(self, key: str | None = None) -> None:
        """Reset the limiter, either entirely or for a single key."""
        async with self._lock:
            if key is None:
                self._buckets.clear()
                return
            self._buckets.pop(key, None)

    async def prune(self, *, max_buckets: int = 10_000) -> int:
        """Drop the buckets that fell outside of the window.

        Args:
            max_buckets: The maximum number of buckets kept in memory.

        Returns:
            The number of removed buckets.
        """
        async with self._lock:
            if len(self._buckets) <= max_buckets:
                return 0
            stale = [
                key
                for key, bucket in self._buckets.items()
                if bucket.used == 0 or not bucket.timestamps
            ]
            for key in stale:
                self._buckets.pop(key, None)
            return len(stale)
