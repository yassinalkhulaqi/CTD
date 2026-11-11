"""Activity event repository backing the realtime feed."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from ctf_team_dashboard.domain.enums import EventKind
from ctf_team_dashboard.domain.models import ActivityEvent, utcnow
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    format_datetime,
    parse_datetime,
    parse_payload,
    row_to_dict,
)


class EventRepository(BaseRepository):
    """Append-only persistence for realtime activity events."""

    table = "events"

    @staticmethod
    def to_model(row: sqlite3.Row) -> ActivityEvent:
        """Map a database row onto the domain model."""
        data = row_to_dict(row)
        occurred_at = parse_datetime(str(data["occurred_at"]))
        team_id = data["team_id"]
        return ActivityEvent(
            id=int(data["id"]),
            team_id=str(team_id) if team_id else None,
            kind=EventKind.parse(str(data["kind"]), EventKind.HEARTBEAT),
            payload=parse_payload(data["payload"]),
            occurred_at=occurred_at if occurred_at is not None else utcnow(),
        )

    def append(
        self,
        kind: EventKind,
        *,
        team_id: str | None = None,
        payload: dict[str, Any] | None = None,
        occurred_at: datetime | None = None,
    ) -> ActivityEvent:
        """Persist a new activity event and return the stored record."""
        moment = occurred_at or utcnow()
        serialised = json.dumps(payload or {}, separators=(",", ":"), default=str)
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """
                INSERT INTO events (team_id, kind, payload, occurred_at)
                VALUES (?, ?, ?, ?)
                """,
                (team_id, kind.value, serialised, format_datetime(moment)),
            )
            event_id = int(cursor.lastrowid or 0)
        return ActivityEvent(
            id=event_id,
            team_id=team_id,
            kind=kind,
            payload=payload or {},
            occurred_at=moment,
        )

    def recent(
        self,
        *,
        team_id: str | None = None,
        limit: int = 50,
        kinds: Sequence[EventKind] | None = None,
    ) -> list[ActivityEvent]:
        """Return the most recent events, newest first."""
        clauses: list[str] = []
        params: list[Any] = []
        if team_id is not None:
            clauses.append("team_id = ?")
            params.append(team_id)
        if kinds:
            clauses.append(f"kind IN ({', '.join('?' for _ in kinds)})")
            params.extend(kind.value for kind in kinds)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(max(1, min(limit, 500)))
        rows = self.fetch_all(
            f"SELECT * FROM events{where} ORDER BY occurred_at DESC, id DESC LIMIT ?", params
        )
        return [self.to_model(row) for row in rows]

    def since(self, event_id: int, *, team_id: str | None = None) -> list[ActivityEvent]:
        """Return events recorded after ``event_id`` for stream resumption."""
        clauses = ["id > ?"]
        params: list[Any] = [event_id]
        if team_id is not None:
            clauses.append("team_id = ?")
            params.append(team_id)
        where = " AND ".join(clauses)
        rows = self.fetch_all(
            f"SELECT * FROM events WHERE {where} ORDER BY id ASC LIMIT 500", params
        )
        return [self.to_model(row) for row in rows]

    def count_matching(self, where: str = "", params: Sequence[Any] = ()) -> int:
        """Return the number of events matching the optional filter."""
        clause = f" WHERE {where}" if where else ""
        value = self.fetch_value(f"SELECT COUNT(*) FROM events{clause}", params, 0)
        return int(value or 0)

    def prune(self, keep: int = 2000) -> int:
        """Trim the event log, keeping the most recent ``keep`` entries."""
        total = self.count()
        if total <= keep:
            return 0
        rows = self.fetch_all(
            "SELECT id FROM events ORDER BY id DESC LIMIT 1 OFFSET ?", (keep - 1,)
        )
        if not rows:
            return 0
        boundary = int(rows[0]["id"])
        return self.execute("DELETE FROM events WHERE id < ?", (boundary,))
