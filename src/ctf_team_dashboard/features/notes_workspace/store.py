"""SQLite persistence for the notes workspace feature.

Every query is parameterised, tags are stored as compact JSON and timestamps
are persisted as aware ISO-8601 strings so the shared repository primitives can
be reused without modification.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from ctf_team_dashboard.db.engine import Database, get_database
from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.features.notes_workspace.models import (
    NoteEntry,
    NoteFormat,
    NoteRevision,
    NoteTemplate,
    TemplateCategory,
)
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    dump_tags,
    format_datetime,
    parse_datetime,
    parse_tags,
    row_to_dict,
)

_NOTES_COLUMNS = (
    "id, challenge_id, member_id, title, body, format, tags, "
    "pinned, version, created_at, updated_at"
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


def _tag_like(tag: str) -> str:
    """Build a LIKE pattern that matches one exact JSON encoded tag.

    Args:
        tag: The normalised tag.

    Returns:
        A pattern suitable for a parameterised ``LIKE`` predicate.
    """
    return f"%{dump_tags([tag])[1:-1]}%"


class NoteEntryRepository(BaseRepository):
    """CRUD and search operations for workspace notes."""

    table = "v3_notes"

    @staticmethod
    def to_model(row: sqlite3.Row) -> NoteEntry:
        """Map a database row onto a :class:`NoteEntry`."""
        data = row_to_dict(row)
        return NoteEntry(
            id=str(data["id"]),
            challenge_id=str(data["challenge_id"]),
            member_id=str(data["member_id"]),
            title=str(data["title"]),
            body=str(data["body"]),
            format=NoteFormat.parse(str(data["format"]), NoteFormat.MARKDOWN),
            tags=parse_tags(str(data["tags"])),
            pinned=bool(data["pinned"]),
            version=int(data["version"]),
            created_at=_datetime(data, "created_at"),
            updated_at=_datetime(data, "updated_at"),
        )

    def get(self, note_id: str) -> NoteEntry | None:
        """Return a note by identifier, or ``None`` when it is missing."""
        row = self.fetch_one(
            f"SELECT {_NOTES_COLUMNS} FROM {self.table} WHERE id = ?",
            (note_id,),
        )
        return self.to_model(row) if row is not None else None

    def list_all(self) -> list[NoteEntry]:
        """Return every note, pinned first and most recently updated first."""
        rows = self.fetch_all(
            f"SELECT {_NOTES_COLUMNS} FROM {self.table} "
            "ORDER BY pinned DESC, updated_at DESC, id ASC"
        )
        return [self.to_model(row) for row in rows]

    def list_for_challenge(self, challenge_id: str) -> list[NoteEntry]:
        """Return the notes belonging to one challenge."""
        rows = self.fetch_all(
            f"SELECT {_NOTES_COLUMNS} FROM {self.table} "
            "WHERE challenge_id = ? ORDER BY pinned DESC, updated_at DESC",
            (challenge_id,),
        )
        return [self.to_model(row) for row in rows]

    def list_for_member(self, member_id: str) -> list[NoteEntry]:
        """Return the notes authored by one member."""
        rows = self.fetch_all(
            f"SELECT {_NOTES_COLUMNS} FROM {self.table} "
            "WHERE member_id = ? ORDER BY updated_at DESC",
            (member_id,),
        )
        return [self.to_model(row) for row in rows]

    def search(
        self,
        *,
        query: str | None = None,
        tags: Sequence[str] = (),
        challenge_id: str | None = None,
        member_id: str | None = None,
        pinned_only: bool = False,
    ) -> list[NoteEntry]:
        """Search notes by free text, tags and ownership.

        Args:
            query: Case-insensitive substring matched against title, body and tags.
            tags: Every tag that must be present on a matching note.
            challenge_id: Optional challenge restriction.
            member_id: Optional author restriction.
            pinned_only: Restrict results to pinned notes.

        Returns:
            The matching notes in display order.
        """
        clauses: list[str] = []
        params: list[Any] = []
        if query and query.strip():
            needle = f"%{query.strip().lower()}%"
            clauses.append("(LOWER(title) LIKE ? OR LOWER(body) LIKE ? OR LOWER(tags) LIKE ?)")
            params.extend((needle, needle, needle))
        for tag in tags:
            clauses.append("tags LIKE ?")
            params.append(_tag_like(tag))
        if challenge_id:
            clauses.append("challenge_id = ?")
            params.append(challenge_id)
        if member_id:
            clauses.append("member_id = ?")
            params.append(member_id)
        if pinned_only:
            clauses.append("pinned = 1")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.fetch_all(
            f"SELECT {_NOTES_COLUMNS} FROM {self.table}{where} "
            "ORDER BY pinned DESC, updated_at DESC, id ASC",
            params,
        )
        return [self.to_model(row) for row in rows]

    def create(self, note: NoteEntry) -> NoteEntry:
        """Insert a note and return the persisted entity."""
        self.execute(
            f"""
            INSERT INTO {self.table}
                (id, challenge_id, member_id, title, body, format, tags,
                 pinned, version, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                note.id,
                note.challenge_id,
                note.member_id,
                note.title,
                note.body,
                str(note.format),
                dump_tags(note.tags),
                int(note.pinned),
                note.version,
                format_datetime(note.created_at),
                format_datetime(note.updated_at),
            ),
        )
        return note

    def update(self, note: NoteEntry) -> NoteEntry:
        """Replace the mutable fields of an existing note."""
        self.execute(
            f"""
            UPDATE {self.table}
            SET title = ?, body = ?, format = ?, tags = ?, version = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                note.title,
                note.body,
                str(note.format),
                dump_tags(note.tags),
                note.version,
                format_datetime(note.updated_at),
                note.id,
            ),
        )
        return note

    def set_pinned(self, note_id: str, pinned: bool) -> NoteEntry | None:
        """Update the pinned flag and return the new note state."""
        cursor_changed = self.execute(
            f"UPDATE {self.table} SET pinned = ?, updated_at = ? WHERE id = ?",
            (int(pinned), format_datetime(utcnow()), note_id),
        )
        if cursor_changed == 0:
            return None
        return self.get(note_id)

    def delete(self, note_id: str) -> bool:
        """Delete a note and report whether a row was removed."""
        return self.execute(f"DELETE FROM {self.table} WHERE id = ?", (note_id,)) > 0

    def distinct_tags(self) -> tuple[str, ...]:
        """Return every tag used in the workspace, ordered alphabetically."""
        rows = self.fetch_all(f"SELECT DISTINCT tags FROM {self.table}")
        found: set[str] = set()
        for row in rows:
            found.update(parse_tags(str(row["tags"])))
        return tuple(sorted(found))


class NoteTemplateRepository(BaseRepository):
    """CRUD operations for reusable note templates."""

    table = "v3_note_templates"

    @staticmethod
    def to_model(row: sqlite3.Row) -> NoteTemplate:
        """Map a database row onto a :class:`NoteTemplate`."""
        data = row_to_dict(row)
        return NoteTemplate(
            id=str(data["id"]),
            name=str(data["name"]),
            category=TemplateCategory.parse(str(data["category"]), TemplateCategory.GENERAL),
            body=str(data["body"]),
        )

    def get(self, template_id: str) -> NoteTemplate | None:
        """Return a template by identifier."""
        row = self.fetch_one(
            f"SELECT id, name, category, body FROM {self.table} WHERE id = ?",
            (template_id,),
        )
        return self.to_model(row) if row is not None else None

    def find_by_name(self, name: str) -> NoteTemplate | None:
        """Return a template whose name matches, ignoring case."""
        row = self.fetch_one(
            f"SELECT id, name, category, body FROM {self.table} "
            "WHERE LOWER(name) = LOWER(?) LIMIT 1",
            (name,),
        )
        return self.to_model(row) if row is not None else None

    def list_all(self, category: TemplateCategory | None = None) -> list[NoteTemplate]:
        """Return templates ordered by category and name."""
        if category is None:
            rows = self.fetch_all(
                f"SELECT id, name, category, body FROM {self.table} ORDER BY category ASC, name ASC"
            )
        else:
            rows = self.fetch_all(
                f"SELECT id, name, category, body FROM {self.table} "
                "WHERE category = ? ORDER BY name ASC",
                (str(category),),
            )
        return [self.to_model(row) for row in rows]

    def create(self, template: NoteTemplate) -> NoteTemplate:
        """Insert a template and return it."""
        self.execute(
            f"INSERT INTO {self.table} (id, name, category, body) VALUES (?, ?, ?, ?)",
            (template.id, template.name, str(template.category), template.body),
        )
        return template

    def delete(self, template_id: str) -> bool:
        """Delete a template and report whether a row was removed."""
        return self.execute(f"DELETE FROM {self.table} WHERE id = ?", (template_id,)) > 0


class NoteRevisionRepository(BaseRepository):
    """Append-only storage for note body snapshots."""

    table = "v3_note_revisions"

    @staticmethod
    def to_model(row: sqlite3.Row) -> NoteRevision:
        """Map a database row onto a :class:`NoteRevision`."""
        data = row_to_dict(row)
        return NoteRevision(
            id=str(data["id"]),
            note_id=str(data["note_id"]),
            version=int(data["version"]),
            body=str(data["body"]),
            author_id=str(data["author_id"]),
            created_at=_datetime(data, "created_at"),
        )

    def list_for_note(self, note_id: str) -> list[NoteRevision]:
        """Return every revision of a note, oldest version first."""
        rows = self.fetch_all(
            f"SELECT id, note_id, version, body, author_id, created_at "
            f"FROM {self.table} WHERE note_id = ? ORDER BY version ASC",
            (note_id,),
        )
        return [self.to_model(row) for row in rows]

    def latest_for_note(self, note_id: str) -> NoteRevision | None:
        """Return the most recent revision of a note."""
        row = self.fetch_one(
            f"SELECT id, note_id, version, body, author_id, created_at "
            f"FROM {self.table} WHERE note_id = ? ORDER BY version DESC LIMIT 1",
            (note_id,),
        )
        return self.to_model(row) if row is not None else None

    def count_for_note(self, note_id: str) -> int:
        """Return the number of stored revisions for a note."""
        value = self.fetch_value(
            f"SELECT COUNT(*) FROM {self.table} WHERE note_id = ?", (note_id,), 0
        )
        return int(value or 0)

    def create(self, revision: NoteRevision) -> NoteRevision:
        """Append a revision snapshot."""
        self.execute(
            f"""
            INSERT INTO {self.table} (id, note_id, version, body, author_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                revision.id,
                revision.note_id,
                revision.version,
                revision.body,
                revision.author_id,
                format_datetime(revision.created_at),
            ),
        )
        return revision

    def delete_for_note(self, note_id: str) -> int:
        """Remove every revision belonging to a note."""
        return self.execute(f"DELETE FROM {self.table} WHERE note_id = ?", (note_id,))


class NotesStore:
    """Aggregate gateway exposing all three notes workspace repositories."""

    def __init__(self, database: Database | None = None) -> None:
        resolved = database or get_database()
        self.notes = NoteEntryRepository(resolved)
        self.templates = NoteTemplateRepository(resolved)
        self.revisions = NoteRevisionRepository(resolved)

    @property
    def database(self) -> Database:
        """Return the database shared by the repositories."""
        return self.notes.database
