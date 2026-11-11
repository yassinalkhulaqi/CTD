"""Note repository."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from typing import Any

from ctf_team_dashboard.domain.models import Note, utcnow
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    format_datetime,
    parse_datetime,
    row_to_dict,
)


class NoteRepository(BaseRepository):
    """Persistence operations for :class:`Note` records."""

    table = "notes"

    @staticmethod
    def to_model(row: sqlite3.Row) -> Note:
        """Map a database row onto the domain model."""
        data = row_to_dict(row)
        created_at = parse_datetime(str(data["created_at"]))
        updated_at = parse_datetime(str(data["updated_at"]))
        return Note(
            id=str(data["id"]),
            challenge_id=str(data["challenge_id"]),
            member_id=str(data["member_id"]),
            body=str(data["body"]),
            created_at=created_at if created_at is not None else utcnow(),
            updated_at=updated_at if updated_at is not None else utcnow(),
        )

    def list_for_challenge(self, challenge_id: str) -> list[Note]:
        """Return every note attached to a challenge, oldest first."""
        rows = self.fetch_all(
            "SELECT * FROM notes WHERE challenge_id = ? ORDER BY created_at ASC",
            (challenge_id,),
        )
        return [self.to_model(row) for row in rows]

    def list_for_member(self, member_id: str) -> list[Note]:
        """Return every note written by a member."""
        rows = self.fetch_all(
            "SELECT * FROM notes WHERE member_id = ? ORDER BY created_at DESC",
            (member_id,),
        )
        return [self.to_model(row) for row in rows]

    def get(self, note_id: str) -> Note | None:
        """Return a note by identifier."""
        row = self.fetch_one("SELECT * FROM notes WHERE id = ?", (note_id,))
        return self.to_model(row) if row is not None else None

    def create(self, note: Note) -> Note:
        """Insert a note and return the persisted record."""
        self.execute(
            """
            INSERT INTO notes (id, challenge_id, member_id, body, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                note.id,
                note.challenge_id,
                note.member_id,
                note.body,
                format_datetime(note.created_at),
                format_datetime(note.updated_at),
            ),
        )
        return note

    def update(self, note: Note) -> Note:
        """Update a note in place and return the new state."""
        self.execute(
            "UPDATE notes SET body = ?, updated_at = ? WHERE id = ?",
            (note.body, format_datetime(note.updated_at), note.id),
        )
        return note

    def delete(self, note_id: str) -> bool:
        """Delete a note; returns ``True`` when a row was removed."""
        return self.execute("DELETE FROM notes WHERE id = ?", (note_id,)) > 0

    def count_matching(self, where: str = "", params: Sequence[Any] = ()) -> int:
        """Return the number of notes matching the optional filter."""
        clause = f" WHERE {where}" if where else ""
        value = self.fetch_value(f"SELECT COUNT(*) FROM notes{clause}", params, 0)
        return int(value or 0)
