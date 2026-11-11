"""Shared repository helpers: row mapping and query primitives."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any, TypeVar

from ctf_team_dashboard.db.engine import Database, get_database
from ctf_team_dashboard.domain.models import ensure_utc

_ScalarT = TypeVar("_ScalarT")


def parse_datetime(raw: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp into an aware datetime."""
    if raw is None or raw == "":
        return None
    return ensure_utc(datetime.fromisoformat(raw))


def format_datetime(value: datetime | None) -> str | None:
    """Serialise a datetime into a sortable ISO-8601 string."""
    if value is None:
        return None
    return ensure_utc(value).isoformat()


def parse_tags(raw: str | None) -> tuple[str, ...]:
    """Parse the JSON encoded tag list stored on a challenge row."""
    if not raw:
        return ()
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return ()
    if not isinstance(decoded, list):
        return ()
    return tuple(str(item) for item in decoded)


def dump_tags(tags: Iterable[str]) -> str:
    """Serialise a tag list into its JSON representation."""
    return json.dumps(list(tags), separators=(",", ":"))


def parse_payload(raw: str | None) -> dict[str, Any]:
    """Parse the JSON payload stored on an activity event row."""
    if not raw:
        return {}
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(decoded, dict):
        return {}
    return decoded


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a result row into a plain dictionary."""
    return dict(row)


class BaseRepository:
    """Common behaviour shared by every repository."""

    table: str = ""

    def __init__(self, database: Database | None = None) -> None:
        self._database = database or get_database()

    @property
    def database(self) -> Database:
        """Return the database gateway backing the repository."""
        return self._database

    def fetch_all(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        """Execute ``sql`` and return every row."""
        with self.database.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            return cursor.fetchall()

    def fetch_one(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
        """Execute ``sql`` and return the first row, if any."""
        with self.database.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            row: sqlite3.Row | None = cursor.fetchone()
            return row

    def fetch_value(
        self,
        sql: str,
        params: Sequence[Any] = (),
        default: _ScalarT | None = None,
    ) -> _ScalarT | None:
        """Execute ``sql`` and return the first column of the first row.

        Args:
            sql: The SQL statement to execute.
            params: Positional parameters bound to the statement.
            default: Value returned when the query produced no rows.

        Returns:
            The scalar value or ``default``.
        """
        row = self.fetch_one(sql, params)
        if row is None:
            return default
        value: _ScalarT = row[0]
        return value

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        """Execute a mutating statement and return the affected row count."""
        with self.database.transaction() as connection:
            cursor = connection.execute(sql, tuple(params))
            return cursor.rowcount

    def execute_many(self, sql: str, rows: Sequence[Sequence[Any]]) -> int:
        """Execute a mutating statement for every row of ``rows``."""
        if not rows:
            return 0
        with self.database.transaction() as connection:
            cursor = connection.executemany(sql, [tuple(row) for row in rows])
            return cursor.rowcount

    def count(self, where: str = "", params: Sequence[Any] = ()) -> int:
        """Return the number of rows matching the optional ``where`` clause."""
        clause = f" WHERE {where}" if where else ""
        value = self.fetch_value(f"SELECT COUNT(*) FROM {self.table}{clause}", params, 0)
        return int(value or 0)

    def exists(self, where: str, params: Sequence[Any] = ()) -> bool:
        """Return whether at least one row matches ``where``."""
        clause = f" WHERE {where}"
        value = self.fetch_value(f"SELECT 1 FROM {self.table}{clause} LIMIT 1", params)
        return value is not None
