"""Persistence for the unified search index and command registry."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from typing import Any

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.features.search_commands.models import (
    Command,
    SearchDocument,
    SearchKind,
)
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    dump_tags,
    format_datetime,
    parse_datetime,
    parse_tags,
    row_to_dict,
)

DOCUMENT_COLUMNS = ("id", "kind", "title", "body", "tags", "path", "updated_at")
COMMAND_COLUMNS = ("id", "name", "description", "command_group", "shortcut", "keywords")


class SearchStore(BaseRepository):
    """Read and write access to the search-owned SQLite tables."""

    table = "v3_search_documents"

    @staticmethod
    def document_from_row(row: sqlite3.Row) -> SearchDocument:
        """Map a document row onto the domain model."""
        data = row_to_dict(row)
        updated = parse_datetime(str(data["updated_at"]))
        return SearchDocument(
            id=str(data["id"]),
            kind=SearchKind.parse(str(data["kind"])),
            title=str(data["title"]),
            body=str(data["body"]),
            tags=parse_tags(data["tags"]),
            path=str(data["path"]),
            updated_at=updated if updated is not None else utcnow(),
        )

    @staticmethod
    def command_from_row(row: sqlite3.Row) -> Command:
        """Map a command row onto the domain model."""
        data = row_to_dict(row)
        return Command(
            id=str(data["id"]),
            name=str(data["name"]),
            description=str(data["description"]),
            group=str(data["command_group"]),
            shortcut=str(data["shortcut"]),
            keywords=parse_tags(data["keywords"]),
        )

    @staticmethod
    def _document_values(document: SearchDocument) -> tuple[Any, ...]:
        """Return the column values of a document for an upsert statement."""
        return (
            document.id,
            document.kind.value,
            document.title,
            document.body,
            dump_tags(document.tags),
            document.path,
            format_datetime(document.updated_at),
        )

    def upsert_document(self, document: SearchDocument) -> SearchDocument:
        """Insert or replace one document and return the stored value."""
        values = self._document_values(document)
        self.execute(
            """
            INSERT INTO v3_search_documents
                (id, kind, title, body, tags, path, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                kind = excluded.kind,
                title = excluded.title,
                body = excluded.body,
                tags = excluded.tags,
                path = excluded.path,
                updated_at = excluded.updated_at
            """,
            values,
        )
        return document

    def bulk_index(self, documents: Sequence[SearchDocument]) -> int:
        """Upsert a batch of documents and return the number of rows written."""
        if not documents:
            return 0
        self.execute_many(
            """
            INSERT INTO v3_search_documents
                (id, kind, title, body, tags, path, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                kind = excluded.kind,
                title = excluded.title,
                body = excluded.body,
                tags = excluded.tags,
                path = excluded.path,
                updated_at = excluded.updated_at
            """,
            [self._document_values(document) for document in documents],
        )
        return len(documents)

    def get_document(self, document_id: str) -> SearchDocument | None:
        """Return a document by its identifier, when present."""
        row = self.fetch_one("SELECT * FROM v3_search_documents WHERE id = ?", (document_id,))
        return self.document_from_row(row) if row is not None else None

    def scan_documents(
        self,
        *,
        kinds: Sequence[SearchKind] = (),
        tags: Sequence[str] = (),
    ) -> list[SearchDocument]:
        """Scan the index with optional kind and tag filters."""
        clauses: list[str] = []
        params: list[Any] = []
        if kinds:
            placeholders = ", ".join("?" for _ in kinds)
            clauses.append(f"kind IN ({placeholders})")
            params.extend(kind.value for kind in kinds)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.fetch_all(f"SELECT * FROM v3_search_documents{where} ORDER BY id ASC", params)
        documents = [self.document_from_row(row) for row in rows]
        if tags:
            folded = {tag.casefold() for tag in tags}
            documents = [
                document
                for document in documents
                if folded.issubset({tag.casefold() for tag in document.tags})
            ]
        return documents

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and report whether a row was removed."""
        return self.execute("DELETE FROM v3_search_documents WHERE id = ?", (document_id,)) > 0

    def document_count(self) -> int:
        """Return the number of indexed documents."""
        return self.count()

    def documents_by_kind(self) -> dict[str, int]:
        """Return a count of documents grouped by kind."""
        rows = self.fetch_all(
            "SELECT kind, COUNT(*) AS total FROM v3_search_documents GROUP BY kind"
        )
        return {str(row["kind"]): int(row["total"]) for row in rows}

    def all_tags(self) -> list[str]:
        """Return every tag stored in the index, including duplicates."""
        rows = self.fetch_all("SELECT tags FROM v3_search_documents")
        tags: list[str] = []
        for row in rows:
            tags.extend(parse_tags(row["tags"]))
        return tags

    def average_body_length(self) -> float:
        """Return the mean body length across indexed documents."""
        value = self.fetch_value("SELECT AVG(LENGTH(body)) FROM v3_search_documents", (), 0.0)
        return round(float(value or 0.0), 2)

    def upsert_command(self, command: Command) -> Command:
        """Insert or replace one command and return the stored value."""
        self.execute(
            """
            INSERT INTO v3_commands
                (id, name, description, command_group, shortcut, keywords)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                description = excluded.description,
                command_group = excluded.command_group,
                shortcut = excluded.shortcut,
                keywords = excluded.keywords
            """,
            (
                command.id,
                command.name,
                command.description,
                command.group,
                command.shortcut,
                dump_tags(command.keywords),
            ),
        )
        return command

    def get_command(self, command_id: str) -> Command | None:
        """Return a command by identifier, when present."""
        row = self.fetch_one("SELECT * FROM v3_commands WHERE id = ?", (command_id,))
        return self.command_from_row(row) if row is not None else None

    def list_commands(self, *, group: str | None = None) -> list[Command]:
        """Return commands ordered by group and name."""
        if group is None:
            rows = self.fetch_all("SELECT * FROM v3_commands ORDER BY command_group ASC, name ASC")
        else:
            rows = self.fetch_all(
                """
                SELECT * FROM v3_commands
                 WHERE command_group = ?
                 ORDER BY command_group ASC, name ASC
                """,
                (group,),
            )
        return [self.command_from_row(row) for row in rows]

    def command_groups(self) -> list[str]:
        """Return the distinct command groups in display order."""
        rows = self.fetch_all(
            "SELECT DISTINCT command_group FROM v3_commands ORDER BY command_group ASC"
        )
        return [str(row["command_group"]) for row in rows]

    def delete_command(self, command_id: str) -> bool:
        """Delete a command and report whether a row was removed."""
        return self.execute("DELETE FROM v3_commands WHERE id = ?", (command_id,)) > 0

    def command_count(self) -> int:
        """Return the number of registered commands."""
        value: int | None = self.fetch_value("SELECT COUNT(*) FROM v3_commands", (), 0)
        return int(value or 0)

    def clear_documents(self) -> int:
        """Remove every document and return the number of deleted rows."""
        return self.execute("DELETE FROM v3_search_documents")
