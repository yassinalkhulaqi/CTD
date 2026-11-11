"""Message protocol shared by the realtime gateway and the clients."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

PROTOCOL_VERSION = 1


class MessageType(str, Enum):
    """The kinds of messages exchanged over the realtime channel."""

    HELLO = "hello"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    EVENT = "event"
    SNAPSHOT = "snapshot"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    BYE = "bye"


@dataclass(frozen=True, slots=True)
class Message:
    """A single frame exchanged over the realtime channel."""

    type: MessageType
    payload: dict[str, Any] = field(default_factory=dict)
    identifier: str | None = None
    sent_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON serialisable representation of the message."""
        return {
            "v": PROTOCOL_VERSION,
            "type": self.type.value,
            "id": self.identifier,
            "ts": self.sent_at.isoformat(),
            "payload": self.payload,
        }

    def to_json(self) -> str:
        """Return the message encoded as a JSON frame."""
        return json.dumps(self.to_dict(), separators=(",", ":"), default=str)

    @classmethod
    def from_json(cls, raw: str) -> Message:
        """Decode a JSON frame into a message.

        Args:
            raw: The raw frame received from a client.

        Returns:
            The decoded message.

        Raises:
            ValueError: When the frame is not a valid message.
        """
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Frame is not valid JSON") from exc

        if not isinstance(decoded, dict):
            raise ValueError("Frame must be a JSON object")

        raw_type = str(decoded.get("type", ""))
        try:
            message_type = MessageType(raw_type)
        except ValueError as exc:
            raise ValueError(f"Unknown message type {raw_type!r}") from exc

        payload = decoded.get("payload")
        identifier = decoded.get("id")
        return cls(
            type=message_type,
            payload=payload if isinstance(payload, dict) else {},
            identifier=str(identifier) if identifier is not None else None,
        )


@dataclass(frozen=True, slots=True)
class Subscription:
    """The filter applied to the events delivered to a client."""

    team_id: str | None = None
    kinds: frozenset[str] = frozenset()

    def accepts(self, event: dict[str, Any]) -> bool:
        """Return whether an event matches the subscription.

        Args:
            event: The event payload.

        Returns:
            ``True`` when the event should be delivered.
        """
        if self.team_id is not None:
            event_team = event.get("team_id")
            if event_team is not None and str(event_team) != self.team_id:
                return False
        if self.kinds:
            kind = str(event.get("kind", ""))
            if kind not in self.kinds:
                return False
        return True

    def to_payload(self) -> dict[str, Any]:
        """Return the JSON serialisable representation of the subscription."""
        return {
            "team_id": self.team_id,
            "kinds": sorted(self.kinds),
        }
