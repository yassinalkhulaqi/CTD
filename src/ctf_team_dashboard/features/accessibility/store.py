"""SQLite persistence for the accessibility toolkit."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.features.accessibility.models import (
    A11yIssue,
    FocusOrderEntry,
    KeyboardShortcut,
    Severity,
    canonical_shortcut,
)
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    format_datetime,
    parse_datetime,
)


def _text(row: dict[str, Any], key: str) -> str:
    """Return a string column from a mapped database row."""
    return str(row[key])


class IssueRepository(BaseRepository):
    """Persistence operations for :class:`A11yIssue` records."""

    table = "v3_a11y_issues"

    @staticmethod
    def to_model(row: sqlite3.Row) -> A11yIssue:
        """Map a database row onto an accessibility issue."""
        data = dict(row)
        detected = parse_datetime(_text(data, "detected_at"))
        return A11yIssue(
            id=_text(data, "id"),
            path=_text(data, "path"),
            rule_id=_text(data, "rule_id"),
            severity=Severity.parse(_text(data, "severity"), Severity.INFO),
            description=_text(data, "description"),
            suggestion=_text(data, "suggestion"),
            detected_at=detected if detected is not None else utcnow(),
            resolved_at=parse_datetime(data["resolved_at"]),
        )

    def list_all(
        self,
        *,
        path: str | None = None,
        severity: Severity | None = None,
        resolved: bool | None = None,
        limit: int = 500,
    ) -> list[A11yIssue]:
        """Return issues filtered by route, severity and resolution state."""
        clauses: list[str] = []
        params: list[Any] = []
        if path is not None:
            clauses.append("path = ?")
            params.append(path)
        if severity is not None:
            clauses.append("severity = ?")
            params.append(severity.value)
        if resolved is True:
            clauses.append("resolved_at IS NOT NULL")
        elif resolved is False:
            clauses.append("resolved_at IS NULL")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.fetch_all(
            f"""
            SELECT * FROM {self.table}{where}
            ORDER BY
                CASE severity WHEN 'critical' THEN 3 WHEN 'warning' THEN 2 ELSE 1 END DESC,
                detected_at DESC
            LIMIT ?
            """,
            [*params, limit],
        )
        return [self.to_model(row) for row in rows]

    def get(self, issue_id: str) -> A11yIssue | None:
        """Return one issue by identifier, when present."""
        row = self.fetch_one(f"SELECT * FROM {self.table} WHERE id = ?", (issue_id,))
        return self.to_model(row) if row is not None else None

    def create(self, issue: A11yIssue) -> A11yIssue:
        """Insert an issue and return the persisted record."""
        self.execute(
            f"""
            INSERT INTO {self.table}
                (id, path, rule_id, severity, description, suggestion, detected_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                issue.id,
                issue.path,
                issue.rule_id,
                issue.severity.value,
                issue.description,
                issue.suggestion,
                format_datetime(issue.detected_at),
                format_datetime(issue.resolved_at),
            ),
        )
        return issue

    def set_resolved(self, issue_id: str, when: datetime | None) -> bool:
        """Store the resolution timestamp of an open issue."""
        resolved_at = format_datetime(when)
        return (
            self.execute(
                f"""
                UPDATE {self.table}
                   SET resolved_at = ?
                 WHERE id = ? AND resolved_at IS NULL
                """,
                (resolved_at, issue_id),
            )
            > 0
        )

    def count_by_severity(self) -> dict[str, int]:
        """Return the number of issues at each severity level."""
        counts = {severity.value: 0 for severity in Severity}
        rows = self.fetch_all(
            f"SELECT severity, COUNT(*) AS total FROM {self.table} GROUP BY severity"
        )
        for row in rows:
            counts[_text(dict(row), "severity")] = int(row["total"])
        return counts

    def count_open_by_severity(self) -> dict[str, int]:
        """Return the number of unresolved issues at each severity level."""
        counts = {severity.value: 0 for severity in Severity}
        rows = self.fetch_all(
            f"""
            SELECT severity, COUNT(*) AS total
              FROM {self.table}
             WHERE resolved_at IS NULL
             GROUP BY severity
            """
        )
        for row in rows:
            counts[_text(dict(row), "severity")] = int(row["total"])
        return counts

    def count_by_state(self) -> tuple[int, int, int]:
        """Return total, open and resolved issue counts."""
        row = self.fetch_one(
            f"""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN resolved_at IS NULL THEN 1 ELSE 0 END) AS open,
                   SUM(CASE WHEN resolved_at IS NOT NULL THEN 1 ELSE 0 END) AS done
              FROM {self.table}
            """
        )
        if row is None:
            return 0, 0, 0
        return int(row["total"] or 0), int(row["open"] or 0), int(row["done"] or 0)

    def paths(self) -> list[str]:
        """Return the distinct routes with recorded issues."""
        rows = self.fetch_all(f"SELECT DISTINCT path FROM {self.table} ORDER BY path")
        return [_text(dict(row), "path") for row in rows]

    def delete(self, issue_id: str) -> bool:
        """Delete an issue and report whether a row was removed."""
        return self.execute(f"DELETE FROM {self.table} WHERE id = ?", (issue_id,)) > 0


class ShortcutRepository(BaseRepository):
    """Persistence operations for :class:`KeyboardShortcut` records."""

    table = "v3_shortcuts"

    @staticmethod
    def to_model(row: sqlite3.Row) -> KeyboardShortcut:
        """Map a database row onto a keyboard shortcut."""
        data = dict(row)
        return KeyboardShortcut(
            id=_text(data, "id"),
            keys=_text(data, "keys"),
            action=_text(data, "action"),
            scope=_text(data, "scope"),
        )

    def list_all(self, *, scope: str | None = None) -> list[KeyboardShortcut]:
        """Return shortcuts, optionally filtered to a scope and globals."""
        if scope is None:
            rows = self.fetch_all(
                f"SELECT * FROM {self.table} ORDER BY scope ASC, keys ASC, id ASC"
            )
        else:
            rows = self.fetch_all(
                f"""
                SELECT * FROM {self.table}
                 WHERE scope = ? OR scope IN ('global', '*', 'all')
                 ORDER BY scope ASC, keys ASC, id ASC
                """,
                (scope,),
            )
        return [self.to_model(row) for row in rows]

    def get(self, shortcut_id: str) -> KeyboardShortcut | None:
        """Return one shortcut by identifier, when present."""
        row = self.fetch_one(f"SELECT * FROM {self.table} WHERE id = ?", (shortcut_id,))
        return self.to_model(row) if row is not None else None

    def create(self, shortcut: KeyboardShortcut) -> KeyboardShortcut:
        """Insert a shortcut and return the persisted record."""
        self.execute(
            f"""
            INSERT INTO {self.table} (id, keys, action, scope)
            VALUES (?, ?, ?, ?)
            """,
            (
                shortcut.id,
                shortcut.canonical_keys,
                shortcut.action,
                shortcut.scope,
            ),
        )
        return KeyboardShortcut(
            id=shortcut.id,
            keys=shortcut.canonical_keys,
            action=shortcut.action,
            scope=shortcut.scope,
        )

    def find_matching(self, keys: str, *, scope: str | None = None) -> list[KeyboardShortcut]:
        """Return shortcuts bound to an equivalent key sequence."""
        canonical = canonical_shortcut(keys)
        candidates = [self.to_model(row) for row in self.fetch_all(f"SELECT * FROM {self.table}")]
        return [
            shortcut
            for shortcut in candidates
            if shortcut.canonical_keys == canonical
            and (scope is None or shortcut.applies_to(scope))
        ]

    def scopes(self) -> tuple[str, ...]:
        """Return the distinct registered scopes in stable order."""
        rows = self.fetch_all(f"SELECT DISTINCT scope FROM {self.table} ORDER BY scope")
        return tuple(_text(dict(row), "scope") for row in rows)

    def delete(self, shortcut_id: str) -> bool:
        """Delete a shortcut and report whether a row was removed."""
        return self.execute(f"DELETE FROM {self.table} WHERE id = ?", (shortcut_id,)) > 0


class FocusOrderRepository(BaseRepository):
    """Persistence operations for :class:`FocusOrderEntry` records."""

    table = "v3_focus_orders"

    @staticmethod
    def to_model(row: sqlite3.Row) -> FocusOrderEntry:
        """Map a database row onto a focus order entry."""
        data = dict(row)
        return FocusOrderEntry(
            id=_text(data, "id"),
            label=_text(data, "label"),
            order=int(data["sort_order"]),
        )

    def list_all(self) -> list[FocusOrderEntry]:
        """Return every focus stop in tab order."""
        rows = self.fetch_all(f"SELECT * FROM {self.table} ORDER BY sort_order ASC, id ASC")
        return [self.to_model(row) for row in rows]

    def get(self, entry_id: str) -> FocusOrderEntry | None:
        """Return one focus stop by identifier, when present."""
        row = self.fetch_one(f"SELECT * FROM {self.table} WHERE id = ?", (entry_id,))
        return self.to_model(row) if row is not None else None

    def create(self, entry: FocusOrderEntry) -> FocusOrderEntry:
        """Insert a focus stop and return the persisted record."""
        self.execute(
            f"""
            INSERT INTO {self.table} (id, label, sort_order)
            VALUES (?, ?, ?)
            """,
            (entry.id, entry.label, entry.order),
        )
        return entry

    def replace_all(self, entries: Sequence[FocusOrderEntry]) -> list[FocusOrderEntry]:
        """Replace the whole focus order with a validated sequence."""
        rows = [(entry.id, entry.label, entry.order) for entry in entries]
        with self.database.transaction() as connection:
            connection.execute(f"DELETE FROM {self.table}")
            connection.executemany(
                f"INSERT INTO {self.table} (id, label, sort_order) VALUES (?, ?, ?)",
                rows,
            )
        return list(entries)

    def delete(self, entry_id: str) -> bool:
        """Delete a focus stop and report whether a row was removed."""
        return self.execute(f"DELETE FROM {self.table} WHERE id = ?", (entry_id,)) > 0
