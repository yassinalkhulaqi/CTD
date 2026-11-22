"""SQLite persistence for the event lifecycle.

The three stores in this module follow the repository pattern used everywhere
else in the dashboard: every statement is parameterised, timestamps are stored
as sortable ISO strings and tags as compact JSON.  All filtering happens in
SQL so large event catalogues do not have to be loaded into memory.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.features.ctf_events.models import (
    CtfEvent,
    EventFormat,
    EventRegistration,
    EventStatus,
    EventTask,
    RegistrationStatus,
)
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    dump_tags,
    format_datetime,
    parse_datetime,
    parse_tags,
    row_to_dict,
)

WINDOWS = frozenset({"all", "draft", "upcoming", "live", "archived"})
MAX_PAGE_SIZE = 500


def _as_datetime(value: str | None, default: datetime | None = None) -> datetime:
    """Read a stored timestamp, falling back to a supplied instant."""
    parsed = parse_datetime(value)
    if parsed is not None:
        return parsed
    return default if default is not None else utcnow()


class EventStore(BaseRepository):
    """CRUD and filtered listing for ``v3_events``."""

    table = "v3_events"

    @staticmethod
    def to_model(row: sqlite3.Row) -> CtfEvent:
        """Map a database row onto the domain model."""
        data = row_to_dict(row)
        return CtfEvent(
            id=str(data["id"]),
            name=str(data["name"]),
            slug=str(data["slug"]),
            description=str(data["description"]),
            format=EventFormat.parse(str(data["format"]), EventFormat.JEOPARDY),
            starts_at=_as_datetime(data.get("starts_at")),
            ends_at=_as_datetime(data.get("ends_at")),
            status=EventStatus.parse(str(data["status"]), EventStatus.DRAFT),
            max_team_size=max(1, int(data["max_team_size"])),
            registration_open=bool(data["registration_open"]),
            website_url=str(data.get("website_url") or ""),
            tags=parse_tags(data.get("tags")),
            created_at=_as_datetime(data.get("created_at")),
        )

    def _where(
        self,
        *,
        status: EventStatus | None,
        event_format: EventFormat | None,
        tag: str | None,
        search: str | None,
        registration_open: bool | None,
        window: str,
        now: datetime,
    ) -> tuple[str, list[Any]]:
        """Build the filter clause and its bound parameters."""
        clauses: list[str] = []
        params: list[Any] = []
        if window not in WINDOWS:
            window = "all"
        moment = format_datetime(now)

        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        if event_format is not None:
            clauses.append("format = ?")
            params.append(event_format.value)
        if tag:
            clauses.append("tags LIKE ?")
            params.append(f'%"{tag.strip().lower()}"%')
        if search:
            clauses.append("(name LIKE ? OR description LIKE ?)")
            term = f"%{search.strip()}%"
            params.extend((term, term))
        if registration_open is not None:
            clauses.append("registration_open = ?")
            params.append(1 if registration_open else 0)

        derived = "status NOT IN ('draft', 'archived')"
        if window == "draft":
            clauses.append("status = 'draft'")
        elif window == "upcoming":
            clauses.append(f"{derived} AND starts_at > ?")
            params.append(moment)
        elif window == "live":
            clauses.append(f"{derived} AND starts_at <= ? AND ends_at > ?")
            params.extend((moment, moment))
        elif window == "archived":
            clauses.append(f"(status = 'archived' OR ({derived} AND ends_at <= ?))")
            params.append(moment)

        clause = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        return clause, params

    def list_events(
        self,
        *,
        status: EventStatus | None = None,
        event_format: EventFormat | None = None,
        tag: str | None = None,
        search: str | None = None,
        registration_open: bool | None = None,
        window: str = "all",
        now: datetime | None = None,
        limit: int = 100,
    ) -> list[CtfEvent]:
        """Return events matching the supplied filters, soonest first."""
        clause, params = self._where(
            status=status,
            event_format=event_format,
            tag=tag,
            search=search,
            registration_open=registration_open,
            window=window,
            now=now if now is not None else utcnow(),
        )
        params.append(max(1, min(limit, MAX_PAGE_SIZE)))
        rows = self.fetch_all(
            f"SELECT * FROM v3_events{clause} ORDER BY starts_at ASC, name ASC LIMIT ?",
            params,
        )
        return [self.to_model(row) for row in rows]

    def count_events(
        self,
        *,
        status: EventStatus | None = None,
        event_format: EventFormat | None = None,
        tag: str | None = None,
        search: str | None = None,
        registration_open: bool | None = None,
        window: str = "all",
        now: datetime | None = None,
    ) -> int:
        """Return the number of events matching the supplied filters."""
        clause, params = self._where(
            status=status,
            event_format=event_format,
            tag=tag,
            search=search,
            registration_open=registration_open,
            window=window,
            now=now if now is not None else utcnow(),
        )
        value = self.fetch_value(f"SELECT COUNT(*) FROM v3_events{clause}", params, 0)
        return int(value or 0)

    def get(self, event_id: str) -> CtfEvent | None:
        """Return an event by identifier, when it exists."""
        row = self.fetch_one("SELECT * FROM v3_events WHERE id = ?", (event_id,))
        return self.to_model(row) if row is not None else None

    def get_by_slug(self, slug: str) -> CtfEvent | None:
        """Return an event by its URL slug, when it exists."""
        row = self.fetch_one("SELECT * FROM v3_events WHERE slug = ?", (slug,))
        return self.to_model(row) if row is not None else None

    def create(self, event: CtfEvent) -> CtfEvent:
        """Insert a new event and return the persisted record."""
        self.execute(
            """
            INSERT INTO v3_events
                (id, name, slug, description, format, starts_at, ends_at,
                 status, max_team_size, registration_open, website_url, tags,
                 created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.name,
                event.slug,
                event.description,
                event.format.value,
                format_datetime(event.starts_at),
                format_datetime(event.ends_at),
                event.status.value,
                event.max_team_size,
                int(event.registration_open),
                event.website_url,
                dump_tags(event.tags),
                format_datetime(event.created_at),
            ),
        )
        return event

    def update(self, event: CtfEvent) -> CtfEvent:
        """Overwrite the mutable columns of an event."""
        self.execute(
            """
            UPDATE v3_events
               SET name = ?, slug = ?, description = ?, format = ?,
                   starts_at = ?, ends_at = ?, status = ?, max_team_size = ?,
                   registration_open = ?, website_url = ?, tags = ?
             WHERE id = ?
            """,
            (
                event.name,
                event.slug,
                event.description,
                event.format.value,
                format_datetime(event.starts_at),
                format_datetime(event.ends_at),
                event.status.value,
                event.max_team_size,
                int(event.registration_open),
                event.website_url,
                dump_tags(event.tags),
                event.id,
            ),
        )
        return event

    def delete(self, event_id: str) -> bool:
        """Delete an event and return whether a row was removed."""
        return self.execute("DELETE FROM v3_events WHERE id = ?", (event_id,)) > 0

    def all_slugs(self) -> set[str]:
        """Return every slug currently in use."""
        rows = self.fetch_all("SELECT slug FROM v3_events")
        return {str(row["slug"]) for row in rows}


class RegistrationStore(BaseRepository):
    """CRUD, queries and waitlist operations for event registrations."""

    table = "v3_event_registrations"

    @staticmethod
    def to_model(row: sqlite3.Row) -> EventRegistration:
        """Map a database row onto the domain model."""
        data = row_to_dict(row)
        return EventRegistration(
            id=str(data["id"]),
            event_id=str(data["event_id"]),
            team_id=str(data["team_id"]),
            status=RegistrationStatus.parse(str(data["status"]), RegistrationStatus.CONFIRMED),
            registered_at=_as_datetime(data.get("registered_at")),
        )

    def list_for_event(
        self,
        event_id: str,
        *,
        statuses: Sequence[RegistrationStatus] | None = None,
    ) -> list[EventRegistration]:
        """Return the registrations of an event in sign-up order."""
        clauses = ["event_id = ?"]
        params: list[Any] = [event_id]
        if statuses:
            clauses.append(f"status IN ({', '.join('?' for _ in statuses)})")
            params.extend(status.value for status in statuses)
        where = " AND ".join(clauses)
        rows = self.fetch_all(
            f"SELECT * FROM v3_event_registrations WHERE {where} "
            "ORDER BY registered_at ASC, id ASC",
            params,
        )
        return [self.to_model(row) for row in rows]

    def list_for_team(
        self,
        team_id: str,
        *,
        statuses: Sequence[RegistrationStatus] | None = None,
    ) -> list[EventRegistration]:
        """Return every registration belonging to a team."""
        clauses = ["team_id = ?"]
        params: list[Any] = [team_id]
        if statuses:
            clauses.append(f"status IN ({', '.join('?' for _ in statuses)})")
            params.extend(status.value for status in statuses)
        where = " AND ".join(clauses)
        rows = self.fetch_all(
            f"SELECT * FROM v3_event_registrations WHERE {where} "
            "ORDER BY registered_at ASC, id ASC",
            params,
        )
        return [self.to_model(row) for row in rows]

    def get(self, registration_id: str) -> EventRegistration | None:
        """Return a registration by identifier."""
        row = self.fetch_one(
            "SELECT * FROM v3_event_registrations WHERE id = ?", (registration_id,)
        )
        return self.to_model(row) if row is not None else None

    def get_for_event_team(self, event_id: str, team_id: str) -> EventRegistration | None:
        """Return an active registration of a team for an event."""
        row = self.fetch_one(
            "SELECT * FROM v3_event_registrations "
            "WHERE event_id = ? AND team_id = ? AND status IN ('confirmed', 'waitlisted') "
            "ORDER BY registered_at DESC LIMIT 1",
            (event_id, team_id),
        )
        return self.to_model(row) if row is not None else None

    def create(self, registration: EventRegistration) -> EventRegistration:
        """Insert a registration."""
        self.execute(
            """
            INSERT INTO v3_event_registrations (id, event_id, team_id, status, registered_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                registration.id,
                registration.event_id,
                registration.team_id,
                registration.status.value,
                format_datetime(registration.registered_at),
            ),
        )
        return registration

    def reserve_slot(
        self,
        *,
        event_id: str,
        team_id: str,
        capacity: int,
        registration_id: str,
        registered_at: datetime,
    ) -> EventRegistration:
        """Atomically count confirmed slots and insert a new registration.

        The count and the insert share one write transaction, so two teams
        registering at the same instant can never both take the final slot.
        """
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM v3_event_registrations "
                "WHERE event_id = ? AND status = 'confirmed'",
                (event_id,),
            ).fetchone()
            confirmed = int(row["total"]) if row is not None else 0
            status = (
                RegistrationStatus.CONFIRMED
                if confirmed < capacity
                else RegistrationStatus.WAITLISTED
            )
            connection.execute(
                """
                INSERT INTO v3_event_registrations
                    (id, event_id, team_id, status, registered_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    registration_id,
                    event_id,
                    team_id,
                    status.value,
                    format_datetime(registered_at),
                ),
            )
        return EventRegistration(
            id=registration_id,
            event_id=event_id,
            team_id=team_id,
            status=status,
            registered_at=registered_at,
        )

    def update(self, registration: EventRegistration) -> EventRegistration:
        """Persist a changed registration status."""
        self.execute(
            "UPDATE v3_event_registrations SET status = ? WHERE id = ?",
            (registration.status.value, registration.id),
        )
        return registration

    def count_status(self, event_id: str, status: RegistrationStatus) -> int:
        """Count registrations of an event in a given state."""
        value = self.fetch_value(
            "SELECT COUNT(*) FROM v3_event_registrations WHERE event_id = ? AND status = ?",
            (event_id, status.value),
            0,
        )
        return int(value or 0)

    def next_waitlisted(self, event_id: str) -> EventRegistration | None:
        """Return the longest-waiting confirmed candidate for promotion."""
        row = self.fetch_one(
            "SELECT * FROM v3_event_registrations "
            "WHERE event_id = ? AND status = 'waitlisted' "
            "ORDER BY registered_at ASC, id ASC LIMIT 1",
            (event_id,),
        )
        return self.to_model(row) if row is not None else None

    def promote_next(self, event_id: str) -> EventRegistration | None:
        """Atomically promote the oldest waitlisted team to confirmed."""
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM v3_event_registrations "
                "WHERE event_id = ? AND status = 'waitlisted' "
                "ORDER BY registered_at ASC, id ASC LIMIT 1",
                (event_id,),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "UPDATE v3_event_registrations "
                "SET status = 'confirmed', promoted_at = ? WHERE id = ?",
                (format_datetime(utcnow()), row["id"]),
            )
            return self.to_model(row).with_status(RegistrationStatus.CONFIRMED)

    def count_promotions(self, event_id: str) -> int:
        """Count teams that were promoted from the waitlist."""
        value = self.fetch_value(
            "SELECT COUNT(*) FROM v3_event_registrations "
            "WHERE event_id = ? AND promoted_at IS NOT NULL",
            (event_id,),
            0,
        )
        return int(value or 0)

    def delete_for_event(self, event_id: str) -> int:
        """Remove every registration of an event."""
        return self.execute("DELETE FROM v3_event_registrations WHERE event_id = ?", (event_id,))

    def delete(self, registration_id: str) -> bool:
        """Delete one registration."""
        return (
            self.execute("DELETE FROM v3_event_registrations WHERE id = ?", (registration_id,)) > 0
        )


class TaskStore(BaseRepository):
    """CRUD and queries for the event checklist."""

    table = "v3_event_tasks"

    @staticmethod
    def to_model(row: sqlite3.Row) -> EventTask:
        """Map a database row onto the domain model."""
        data = row_to_dict(row)
        return EventTask(
            id=str(data["id"]),
            event_id=str(data["event_id"]),
            title=str(data["title"]),
            done=bool(data["done"]),
            due_at=parse_datetime(data.get("due_at")),
        )

    def list_for_event(self, event_id: str) -> list[EventTask]:
        """Return the checklist of an event, incomplete items first."""
        rows = self.fetch_all(
            "SELECT * FROM v3_event_tasks WHERE event_id = ? ORDER BY done ASC, due_at ASC, id ASC",
            (event_id,),
        )
        return [self.to_model(row) for row in rows]

    def get(self, task_id: str) -> EventTask | None:
        """Return a task by identifier."""
        row = self.fetch_one("SELECT * FROM v3_event_tasks WHERE id = ?", (task_id,))
        return self.to_model(row) if row is not None else None

    def create(self, task: EventTask) -> EventTask:
        """Insert a checklist item."""
        self.execute(
            """
            INSERT INTO v3_event_tasks (id, event_id, title, done, due_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                task.id,
                task.event_id,
                task.title,
                int(task.done),
                format_datetime(task.due_at),
            ),
        )
        return task

    def update(self, task: EventTask) -> EventTask:
        """Persist the mutable columns of a task."""
        self.execute(
            "UPDATE v3_event_tasks SET title = ?, done = ?, due_at = ? WHERE id = ?",
            (task.title, int(task.done), format_datetime(task.due_at), task.id),
        )
        return task

    def toggle(self, task_id: str) -> EventTask | None:
        """Flip the done flag atomically and return the new state."""
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM v3_event_tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if row is None:
                return None
            done = 0 if bool(row["done"]) else 1
            connection.execute("UPDATE v3_event_tasks SET done = ? WHERE id = ?", (done, task_id))
            return self.to_model(row).toggle()

    def count_done(self, event_id: str) -> int:
        """Return the number of completed checklist items."""
        value = self.fetch_value(
            "SELECT COUNT(*) FROM v3_event_tasks WHERE event_id = ? AND done = 1",
            (event_id,),
            0,
        )
        return int(value or 0)

    def delete(self, task_id: str) -> bool:
        """Delete one checklist item."""
        return self.execute("DELETE FROM v3_event_tasks WHERE id = ?", (task_id,)) > 0

    def delete_for_event(self, event_id: str) -> int:
        """Remove every checklist item of an event."""
        return self.execute("DELETE FROM v3_event_tasks WHERE event_id = ?", (event_id,))
