"""SQLite persistence for the activity timeline feature.

All statements are parameterised, timestamps are stored as aware ISO-8601
strings and payloads are encoded as compact JSON. The module only maps rows to
domain entities; every business rule stays in the service layer.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from ctf_team_dashboard.db.engine import Database, get_database
from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.features.activity_timeline.models import (
    ActorSummary,
    TimelineEvent,
    TimelineFilter,
    TimelineKind,
    encode_payload,
    take_unique,
)
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    format_datetime,
    parse_datetime,
    row_to_dict,
)

_EVENT_COLUMNS = (
    "id, team_id, kind, actor_id, actor_name, summary, payload_json, importance, occurred_at"
)


def _datetime(data: dict[str, Any], key: str) -> datetime:
    """Parse a stored timestamp, falling back to the current time.

    Args:
        data: The decoded row.
        key: The timestamp column name.

    Returns:
        A timezone aware datetime.
    """
    parsed = parse_datetime(str(data[key]))
    return parsed if parsed is not None else utcnow()


class TimelineEventRepository(BaseRepository):
    """Insert, query and prune stored timeline events."""

    table = "v3_timeline_events"

    @staticmethod
    def to_model(row: sqlite3.Row) -> TimelineEvent:
        """Map a database row onto a :class:`TimelineEvent`."""
        data = row_to_dict(row)
        return TimelineEvent(
            id=str(data["id"]),
            team_id=str(data["team_id"]),
            kind=str(data["kind"]),
            actor_id=str(data["actor_id"]),
            actor_name=str(data["actor_name"]),
            summary=str(data["summary"]),
            payload_json=str(data["payload_json"]),
            importance=str(data["importance"]),
            occurred_at=_datetime(data, "occurred_at"),
        )

    @staticmethod
    def _clauses(
        timeline_filter: TimelineFilter,
    ) -> tuple[list[str], list[Any]]:
        """Translate a filter into SQL predicates and bound parameters.

        Args:
            timeline_filter: The filter to translate.

        Returns:
            A pair of clause strings and positional parameters.
        """
        clauses: list[str] = []
        params: list[Any] = []
        if timeline_filter.team_id:
            clauses.append("team_id = ?")
            params.append(timeline_filter.team_id)
        if timeline_filter.kinds:
            placeholders = ", ".join("?" for _ in timeline_filter.kinds)
            clauses.append(f"kind IN ({placeholders})")
            params.extend(timeline_filter.kinds)
        if timeline_filter.actors:
            placeholders = ", ".join("?" for _ in timeline_filter.actors)
            clauses.append(f"actor_id IN ({placeholders})")
            params.extend(timeline_filter.actors)
        if timeline_filter.importance:
            placeholders = ", ".join("?" for _ in timeline_filter.importance)
            clauses.append(f"importance IN ({placeholders})")
            params.extend(timeline_filter.importance)
        if timeline_filter.from_at is not None:
            clauses.append("occurred_at >= ?")
            params.append(format_datetime(timeline_filter.from_at))
        if timeline_filter.to_at is not None:
            clauses.append("occurred_at <= ?")
            params.append(format_datetime(timeline_filter.to_at))
        return clauses, params

    def get(self, event_id: str) -> TimelineEvent | None:
        """Return an event by identifier, or ``None`` when it is missing."""
        row = self.fetch_one(f"SELECT {_EVENT_COLUMNS} FROM {self.table} WHERE id = ?", (event_id,))
        return self.to_model(row) if row is not None else None

    def insert(self, event: TimelineEvent) -> TimelineEvent:
        """Insert one event and return the persisted entity."""
        self.execute(
            f"""
            INSERT INTO {self.table}
                (id, team_id, kind, actor_id, actor_name, summary,
                 payload_json, importance, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.team_id,
                event.kind,
                event.actor_id,
                event.actor_name,
                event.summary,
                event.payload_json,
                event.importance,
                format_datetime(event.occurred_at),
            ),
        )
        return event

    def matching(
        self,
        timeline_filter: TimelineFilter,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TimelineEvent]:
        """Return events matching a filter in chronological display order.

        Args:
            timeline_filter: The filter describing the desired rows.
            limit: Optional row cap; ``None`` returns every match.
            offset: Number of matching rows to skip.

        Returns:
            The matching events, newest first.
        """
        clauses, params = self._clauses(timeline_filter)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        sql = f"SELECT {_EVENT_COLUMNS} FROM {self.table}{where} "
        sql += "ORDER BY occurred_at DESC, id DESC"
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend((limit, max(0, offset)))
        rows = self.fetch_all(sql, params)
        return [self.to_model(row) for row in rows]

    def count_matching(self, timeline_filter: TimelineFilter) -> int:
        """Return the number of events matching a filter."""
        clauses, params = self._clauses(timeline_filter)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        value = self.fetch_value(f"SELECT COUNT(*) FROM {self.table}{where}", params, 0)
        return int(value or 0)

    def recent(self, limit: int = 10, team_id: str | None = None) -> list[TimelineEvent]:
        """Return the most recent events, optionally restricted to a team.

        Args:
            limit: Maximum number of events to return.
            team_id: Optional team restriction.

        Returns:
            The newest matching events.
        """
        timeline_filter = TimelineFilter(team_id=team_id, limit=max(0, limit))
        return self.matching(timeline_filter, limit=max(0, limit))

    def list_since(self, when: datetime, team_id: str | None = None) -> list[TimelineEvent]:
        """Return every event recorded at or after the given timestamp."""
        timeline_filter = TimelineFilter(team_id=team_id, from_at=when)
        return self.matching(timeline_filter)

    def count_since(self, when: datetime, team_id: str | None = None) -> int:
        """Count the events recorded at or after the given timestamp."""
        return self.count_matching(TimelineFilter(team_id=team_id, from_at=when))

    def delete(self, event_id: str) -> bool:
        """Delete one event and report whether a row was removed."""
        return self.execute(f"DELETE FROM {self.table} WHERE id = ?", (event_id,)) > 0

    def delete_before(self, cutoff: datetime) -> int:
        """Delete every event strictly older than the cutoff timestamp."""
        return self.execute(
            f"DELETE FROM {self.table} WHERE occurred_at < ?",
            (format_datetime(cutoff),),
        )

    def actor_summaries(self, team_id: str | None = None) -> list[ActorSummary]:
        """Aggregate event counts per actor using a grouped SQL query.

        Args:
            team_id: Optional team restriction.

        Returns:
            One summary per actor, ordered by activity then name.
        """
        where = "WHERE team_id = ?" if team_id else ""
        params: Sequence[Any] = (team_id,) if team_id else ()
        rows = self.fetch_all(
            f"""
            SELECT actor_id, actor_name,
                   COUNT(*) AS event_count,
                   SUM(CASE WHEN importance = 'critical' THEN 1 ELSE 0 END)
                       AS critical_count,
                   MAX(occurred_at) AS last_seen,
                   GROUP_CONCAT(DISTINCT kind) AS kinds
            FROM {self.table}
            {where}
            GROUP BY actor_id, actor_name
            ORDER BY event_count DESC, actor_name ASC
            """,
            params,
        )
        summaries: list[ActorSummary] = []
        for row in rows:
            data = row_to_dict(row)
            raw_kinds = str(data["kinds"] or "")
            kinds = take_unique(part.strip() for part in raw_kinds.split(",") if part.strip())
            summaries.append(
                ActorSummary(
                    actor_id=str(data["actor_id"]),
                    actor_name=str(data["actor_name"]),
                    event_count=int(data["event_count"] or 0),
                    critical_count=int(data["critical_count"] or 0),
                    last_seen=parse_datetime(str(data["last_seen"])),
                    kinds=kinds,
                )
            )
        return summaries

    def distinct_kinds(self) -> tuple[str, ...]:
        """Return every kind currently present in the store, alphabetically."""
        rows = self.fetch_all(f"SELECT DISTINCT kind FROM {self.table} ORDER BY kind ASC")
        return tuple(str(row["kind"]) for row in rows)

    def payload_fields(self, event_id: str) -> dict[str, Any]:
        """Return the decoded payload of one event.

        Args:
            event_id: The event identifier.

        Returns:
            The decoded payload mapping, or an empty object.
        """
        raw = self.fetch_value(
            f"SELECT payload_json FROM {self.table} WHERE id = ?",
            (event_id,),
            default="",
        )
        if not raw:
            return {}
        decoded: Any = json.loads(str(raw))
        return decoded if isinstance(decoded, dict) else {}


class TimelineStore:
    """Gateway exposing the timeline repositories to the service layer."""

    def __init__(self, database: Database | None = None) -> None:
        self.events = TimelineEventRepository(database or get_database())

    @property
    def database(self) -> Database:
        """Return the database shared by the repositories."""
        return self.events.database


def known_kinds(store: TimelineStore) -> tuple[TimelineKind, ...]:
    """Return the kinds present in the store as enum members.

    Args:
        store: The store to inspect.

    Returns:
        The distinct known kinds in stable order.
    """
    found: list[TimelineKind] = []
    for raw in store.events.distinct_kinds():
        try:
            kind = TimelineKind.parse(raw)
        except ValueError:
            continue
        if kind not in found:
            found.append(kind)
    return tuple(found)


def empty_payload() -> str:
    """Return the canonical JSON representation of an empty payload."""
    return encode_payload(None)
