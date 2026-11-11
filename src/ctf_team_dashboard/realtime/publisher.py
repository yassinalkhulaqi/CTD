"""Background publisher tailing the persisted event log."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import Sequence
from typing import Any

from ctf_team_dashboard.db.engine import Database, get_database
from ctf_team_dashboard.domain.enums import EventKind
from ctf_team_dashboard.domain.models import ActivityEvent
from ctf_team_dashboard.realtime.bus import EventBus, get_event_bus
from ctf_team_dashboard.repositories import Repositories

logger = logging.getLogger("ctf_team_dashboard.realtime")

DEFAULT_POLL_INTERVAL = 0.5


def event_to_payload(event: ActivityEvent) -> dict[str, Any]:
    """Convert an activity event into the realtime payload.

    Args:
        event: The persisted event.

    Returns:
        The payload delivered to the clients.
    """
    return {
        "id": event.id,
        "team_id": event.team_id,
        "kind": event.kind.value,
        "payload": event.payload,
        "occurred_at": event.occurred_at.isoformat(),
    }


class EventPublisher:
    """Tail the event log and forward every new record to the bus."""

    def __init__(
        self,
        bus: EventBus | None = None,
        database: Database | None = None,
        *,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
    ) -> None:
        self.bus = bus or get_event_bus()
        self.database = database or get_database()
        self.poll_interval = poll_interval
        self._task: asyncio.Task[None] | None = None
        self._cursor = 0
        self._stopping = asyncio.Event()

    async def start(self, *, from_event_id: int | None = None) -> None:
        """Start tailing the event log.

        Args:
            from_event_id: Resume after this event identifier.
        """
        if self._task is not None:
            return
        if from_event_id is not None:
            self._cursor = from_event_id
        self._stopping.clear()
        self._task = asyncio.create_task(self._run(), name="ctfd-event-publisher")

    async def stop(self) -> None:
        """Stop tailing the event log."""
        self._stopping.set()
        task = self._task
        self._task = None
        if task is None:
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def _run(self) -> None:
        """Poll the event log and publish the new records."""
        while not self._stopping.is_set():
            try:
                published = await self.publish_once()
            except Exception:
                logger.exception("failed to publish the pending events")
                published = 0
            if published == 0:
                await asyncio.sleep(self.poll_interval)

    async def publish_once(self) -> int:
        """Publish every event recorded after the current cursor.

        Returns:
            The number of published events.
        """
        repositories = Repositories()
        events = repositories.events.since(self._cursor)
        if not events:
            return 0

        payloads = [event_to_payload(event) for event in events]
        await self.bus.publish_many(payloads)
        self._cursor = max(event.id for event in events)
        return len(payloads)

    async def publish_event(self, event: ActivityEvent) -> int:
        """Publish a single event immediately.

        Args:
            event - The event to publish.

        Returns:
            The number of subscribers the event was delivered to.
        """
        payload = event_to_payload(event)
        delivered = await self.bus.publish(payload)
        self._cursor = max(self._cursor, event.id)
        return delivered

    async def replay(self, limit: int = 50) -> Sequence[dict[str, Any]]:
        """Return the most recent events as realtime payloads.

        Args:
            limit - The maximum number of events.

        Returns:
            The payloads of the most recent events.
        """
        repositories = Repositories()
        events = repositories.events.recent(limit=limit)
        return [event_to_payload(event) for event in events]


def parse_event_payload(raw: str) -> dict[str, Any]:
    """Parse a stored event payload into a dictionary.

    Args:
        raw - The JSON encoded payload.

    Returns:
        The decoded payload.
    """
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


_publisher: EventPublisher | None = None


def get_publisher() -> EventPublisher:
    """Return the process wide event publisher."""
    global _publisher
    if _publisher is None:
        _publisher = EventPublisher()
    return _publisher


def reset_publisher() -> None:
    """Replace the process wide event publisher (used by the tests)."""
    global _publisher
    _publisher = None


__all__ = [
    "DEFAULT_POLL_INTERVAL",
    "EventKind",
    "EventPublisher",
    "event_to_payload",
    "get_publisher",
    "parse_event_payload",
    "reset_publisher",
]
