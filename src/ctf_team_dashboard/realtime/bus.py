"""In-process publish and subscribe bus backing the realtime gateway."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from ctf_team_dashboard.realtime.protocol import Subscription

MAX_QUEUE_SIZE = 256


@dataclass(slots=True)
class Subscriber:
    """A client subscribed to the event bus."""

    identifier: str
    queue: asyncio.Queue[dict[str, Any]] = field(
        default_factory=lambda: asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
    )
    subscription: Subscription = field(default_factory=Subscription)
    dropped: int = 0

    def offer(self, event: dict[str, Any]) -> bool:
        """Push an event into the subscriber queue.

        The event is dropped when the queue is full so a slow client can never
        block the publisher.

        Args:
            event - The event to deliver.

        Returns:
            ``True`` when the event was queued, ``False`` when it was dropped.
        """
        if not self.subscription.accepts(event):
            return True
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            self.dropped += 1
            with contextlib.suppress(asyncio.QueueEmpty):
                self.queue.get_nowait()
            with contextlib.suppress(asyncio.QueueFull):
                self.queue.put_nowait(event)
            return False
        return True


class EventBus:
    """Fan out events to every subscribed client."""

    def __init__(self) -> None:
        self._subscribers: dict[str, Subscriber] = {}
        self._lock = asyncio.Lock()
        self._published = 0
        self._dropped = 0

    async def subscribe(
        self, identifier: str, subscription: Subscription | None = None
    ) -> Subscriber:
        """Register a new subscriber.

        Args:
            identifier: The unique identifier of the subscriber.
            subscription: The initial filter of the subscriber.

        Returns:
            The registered subscriber.
        """
        async with self._lock:
            subscriber = Subscriber(
                identifier=identifier,
                subscription=subscription or Subscription(),
            )
            self._subscribers[identifier] = subscriber
            return subscriber

    async def unsubscribe(self, identifier: str) -> None:
        """Remove a subscriber.

        Args:
            identifier: The unique identifier of the subscriber.
        """
        async with self._lock:
            self._subscribers.pop(identifier, None)

    async def update_subscription(
        self, identifier: str, subscription: Subscription
    ) -> Subscriber | None:
        """Replace the filter of a subscriber.

        Args:
            identifier: The unique identifier of the subscriber.
            subscription: The new filter.

        Returns:
            The updated subscriber, or ``None`` when it is unknown.
        """
        async with self._lock:
            subscriber = self._subscribers.get(identifier)
            if subscriber is None:
                return None
            subscriber.subscription = subscription
            return subscriber

    async def publish(self, event: dict[str, Any]) -> int:
        """Deliver an event to every matching subscriber.

        Args:
            event: The event to deliver.

        Returns:
            The number of subscribers the event was delivered to.
        """
        async with self._lock:
            subscribers = list(self._subscribers.values())

        delivered = 0
        for subscriber in subscribers:
            if subscriber.offer(event):
                delivered += 1
            else:
                self._dropped += 1

        self._published += 1
        return delivered

    async def publish_many(self, events: Iterable[dict[str, Any]]) -> int:
        """Deliver a batch of events.

        Args:
            events: The events to deliver.

        Returns:
            The number of subscribers the batch was delivered to.
        """
        delivered = 0
        for event in events:
            delivered += await self.publish(event)
        return delivered

    async def subscriber_count(self) -> int:
        """Return the number of active subscribers."""
        async with self._lock:
            return len(self._subscribers)

    async def snapshot(self) -> dict[str, Any]:
        """Return the runtime counters of the bus."""
        async with self._lock:
            return {
                "subscribers": len(self._subscribers),
                "published": self._published,
                "dropped": self._dropped,
            }


_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Return the process wide event bus."""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus


def reset_event_bus() -> None:
    """Replace the process wide event bus (used by the tests)."""
    global _bus
    _bus = None
