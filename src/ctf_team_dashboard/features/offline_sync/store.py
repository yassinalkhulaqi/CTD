"""SQLite persistence for the offline queue, snapshots and conflict ledger."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from typing import Any

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.features.offline_sync.models import (
    ConflictResolution,
    ConflictStrategy,
    MutationOperation,
    MutationStatus,
    PendingMutation,
    SyncSnapshot,
)
from ctf_team_dashboard.repositories.base import BaseRepository, format_datetime, parse_datetime


def _operation(raw: str) -> MutationOperation:
    """Decode a stored operation, falling back to ``update`` for legacy rows."""
    try:
        return MutationOperation(raw)
    except ValueError:
        return MutationOperation.UPDATE


def _status(raw: str) -> MutationStatus:
    """Decode a stored status, falling back to ``pending`` for legacy rows."""
    try:
        return MutationStatus(raw)
    except ValueError:
        return MutationStatus.PENDING


def _strategy(raw: str) -> ConflictStrategy:
    """Decode a stored strategy, falling back to ``merge`` for legacy rows."""
    try:
        return ConflictStrategy(raw)
    except ValueError:
        return ConflictStrategy.MERGE


def _timestamp(raw: str) -> Any:
    """Decode a stored ISO timestamp with a safe fallback."""
    return parse_datetime(raw) or utcnow()


def _row_to_mutation(row: sqlite3.Row) -> PendingMutation:
    """Map a pending-mutation row onto its domain entity."""
    resolved = row["resolved_version"]
    return PendingMutation(
        id=str(row["id"]),
        client_id=str(row["client_id"]),
        entity=str(row["entity"]),
        operation=_operation(str(row["operation"])),
        payload_json=str(row["payload_json"]),
        base_version=int(row["base_version"]),
        created_at=_timestamp(str(row["created_at"])),
        status=_status(str(row["status"])),
        attempts=int(row["attempts"]),
        last_error=str(row["last_error"]),
        resolved_version=int(resolved) if resolved is not None else None,
    )


def _row_to_snapshot(row: sqlite3.Row) -> SyncSnapshot:
    """Map a snapshot row onto its domain entity."""
    return SyncSnapshot(
        id=str(row["id"]),
        client_id=str(row["client_id"]),
        synced_at=_timestamp(str(row["synced_at"])),
        version=int(row["version"]),
        mutation_count=int(row["mutation_count"]),
        conflict_count=int(row["conflict_count"]),
        note=str(row["note"]),
    )


def _row_to_resolution(row: sqlite3.Row) -> ConflictResolution:
    """Map a conflict resolution row onto its domain entity."""
    return ConflictResolution(
        id=str(row["id"]),
        mutation_id=str(row["mutation_id"]),
        strategy=_strategy(str(row["strategy"])),
        resolved_at=_timestamp(str(row["resolved_at"])),
        local_version=int(row["local_version"]),
        remote_version=int(row["remote_version"]),
        field_changes_json=str(row["field_changes_json"]),
        notes=str(row["notes"]),
    )


class MutationRepository(BaseRepository):
    """Repository over the FIFO mutation queue table."""

    table = "v3_pending_mutations"

    def add(self, mutation: PendingMutation) -> int:
        """Insert a mutation and return the affected row count."""
        return self.execute(
            """
            INSERT INTO v3_pending_mutations (
                id, client_id, entity, operation, payload_json, base_version,
                created_at, status, attempts, last_error, resolved_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mutation.id,
                mutation.client_id,
                mutation.entity,
                mutation.operation.value,
                mutation.payload_json,
                mutation.base_version,
                format_datetime(mutation.created_at),
                mutation.status.value,
                mutation.attempts,
                mutation.last_error,
                mutation.resolved_version,
            ),
        )

    def get(self, mutation_id: str) -> PendingMutation | None:
        """Return a mutation by identifier, or ``None`` when absent."""
        row = self.fetch_one(
            f"SELECT * FROM {self.table} WHERE id = ?",
            (mutation_id,),
        )
        return _row_to_mutation(row) if row is not None else None

    def list_all(
        self,
        *,
        client_id: str | None = None,
        status: MutationStatus | None = None,
        entity: str | None = None,
        limit: int | None = None,
    ) -> list[PendingMutation]:
        """Return mutations matching the filters in FIFO order."""
        clauses: list[str] = []
        params: list[Any] = []
        if client_id:
            clauses.append("client_id = ?")
            params.append(client_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        if entity:
            clauses.append("entity = ?")
            params.append(entity)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        suffix = " ORDER BY created_at ASC, id ASC"
        if limit is not None:
            suffix += " LIMIT ?"
            params.append(limit)
        rows = self.fetch_all(f"SELECT * FROM {self.table}{where}{suffix}", params)
        return [_row_to_mutation(row) for row in rows]

    def list_pending(
        self, *, client_id: str | None = None, limit: int | None = None
    ) -> list[PendingMutation]:
        """Return only mutations waiting to be pushed, oldest first."""
        return self.list_all(
            client_id=client_id,
            status=MutationStatus.PENDING,
            limit=limit,
        )

    def list_conflicts(self, *, client_id: str | None = None) -> list[PendingMutation]:
        """Return mutations paused by a version conflict."""
        return self.list_all(client_id=client_id, status=MutationStatus.CONFLICT)

    def save(self, mutation: PendingMutation) -> int:
        """Persist the mutable fields of a mutation."""
        return self.execute(
            """
            UPDATE v3_pending_mutations
               SET payload_json = ?, base_version = ?, status = ?, attempts = ?,
                   last_error = ?, resolved_version = ?
             WHERE id = ?
            """,
            (
                mutation.payload_json,
                mutation.base_version,
                mutation.status.value,
                mutation.attempts,
                mutation.last_error,
                mutation.resolved_version,
                mutation.id,
            ),
        )

    def delete(self, mutation_id: str) -> int:
        """Remove one mutation from the queue."""
        return self.execute(f"DELETE FROM {self.table} WHERE id = ?", (mutation_id,))

    def delete_synced(self, *, client_id: str | None = None) -> int:
        """Remove every synchronised mutation and return the removed count."""
        if client_id:
            return self.execute(
                f"DELETE FROM {self.table} WHERE status = ? AND client_id = ?",
                (MutationStatus.SYNCED.value, client_id),
            )
        return self.execute(
            f"DELETE FROM {self.table} WHERE status = ?",
            (MutationStatus.SYNCED.value,),
        )

    def delete_many(self, mutation_ids: Sequence[str]) -> int:
        """Remove a batch of mutations identified by their identifiers."""
        if not mutation_ids:
            return 0
        placeholders = ", ".join("?" for _ in mutation_ids)
        return self.execute(
            f"DELETE FROM {self.table} WHERE id IN ({placeholders})",
            tuple(mutation_ids),
        )

    def count_by_status(self, *, client_id: str | None = None) -> dict[str, int]:
        """Return a mapping of status value to the number of queued rows."""
        where = " WHERE client_id = ?" if client_id else ""
        params: Sequence[Any] = (client_id,) if client_id else ()
        rows = self.fetch_all(
            f"SELECT status, COUNT(*) AS total FROM {self.table}{where} GROUP BY status",
            params,
        )
        return {str(row["status"]): int(row["total"]) for row in rows}

    def total_attempts(self, *, client_id: str | None = None) -> int:
        """Return the sum of push attempts across the queue."""
        where = " WHERE client_id = ?" if client_id else ""
        params: Sequence[Any] = (client_id,) if client_id else ()
        value = self.fetch_value(
            f"SELECT COALESCE(SUM(attempts), 0) FROM {self.table}{where}",
            params,
            0,
        )
        return int(value or 0)

    def oldest_pending_at(self, *, client_id: str | None = None) -> Any:
        """Return the creation time of the oldest pending mutation."""
        clauses = ["status = ?"]
        params: list[Any] = [MutationStatus.PENDING.value]
        if client_id:
            clauses.append("client_id = ?")
            params.append(client_id)
        raw = self.fetch_value(
            f"SELECT MIN(created_at) FROM {self.table} WHERE {' AND '.join(clauses)}",
            params,
        )
        return parse_datetime(str(raw)) if raw else None

    def newest_synced_at(self, *, client_id: str | None = None) -> Any:
        """Return the creation time of the most recently synchronised mutation."""
        clauses = ["status = ?"]
        params: list[Any] = [MutationStatus.SYNCED.value]
        if client_id:
            clauses.append("client_id = ?")
            params.append(client_id)
        raw = self.fetch_value(
            f"SELECT MAX(created_at) FROM {self.table} WHERE {' AND '.join(clauses)}",
            params,
        )
        return parse_datetime(str(raw)) if raw else None


class SnapshotRepository(BaseRepository):
    """Repository over immutable synchronisation snapshots."""

    table = "v3_sync_snapshots"

    def add(self, snapshot: SyncSnapshot) -> int:
        """Insert a snapshot record."""
        return self.execute(
            """
            INSERT INTO v3_sync_snapshots (
                id, client_id, synced_at, version, mutation_count, conflict_count, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.id,
                snapshot.client_id,
                format_datetime(snapshot.synced_at),
                snapshot.version,
                snapshot.mutation_count,
                snapshot.conflict_count,
                snapshot.note,
            ),
        )

    def latest(self, *, client_id: str | None = None) -> SyncSnapshot | None:
        """Return the newest snapshot, optionally scoped to one client."""
        if client_id:
            row = self.fetch_one(
                f"SELECT * FROM {self.table} WHERE client_id = ? "
                "ORDER BY synced_at DESC, id DESC LIMIT 1",
                (client_id,),
            )
        else:
            row = self.fetch_one(
                f"SELECT * FROM {self.table} ORDER BY synced_at DESC, id DESC LIMIT 1"
            )
        return _row_to_snapshot(row) if row is not None else None

    def list_all(self, *, client_id: str | None = None, limit: int = 20) -> list[SyncSnapshot]:
        """Return the most recent snapshots, newest first."""
        if client_id:
            rows = self.fetch_all(
                f"SELECT * FROM {self.table} WHERE client_id = ? "
                "ORDER BY synced_at DESC, id DESC LIMIT ?",
                (client_id, limit),
            )
        else:
            rows = self.fetch_all(
                f"SELECT * FROM {self.table} ORDER BY synced_at DESC, id DESC LIMIT ?",
                (limit,),
            )
        return [_row_to_snapshot(row) for row in rows]

    def highest_version(self, *, client_id: str | None = None) -> int:
        """Return the greatest version recorded by any snapshot."""
        if client_id:
            value = self.fetch_value(
                f"SELECT MAX(version) FROM {self.table} WHERE client_id = ?",
                (client_id,),
                0,
            )
        else:
            value = self.fetch_value(f"SELECT MAX(version) FROM {self.table}", (), 0)
        return int(value or 0)


class ConflictRepository(BaseRepository):
    """Repository over conflict resolutions produced by the user."""

    table = "v3_conflict_resolutions"

    def add(self, resolution: ConflictResolution) -> int:
        """Insert a conflict resolution record."""
        return self.execute(
            """
            INSERT INTO v3_conflict_resolutions (
                id, mutation_id, strategy, resolved_at, local_version,
                remote_version, field_changes_json, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolution.id,
                resolution.mutation_id,
                resolution.strategy.value,
                format_datetime(resolution.resolved_at),
                resolution.local_version,
                resolution.remote_version,
                resolution.field_changes_json,
                resolution.notes,
            ),
        )

    def get(self, resolution_id: str) -> ConflictResolution | None:
        """Return a resolution by its own identifier."""
        row = self.fetch_one(f"SELECT * FROM {self.table} WHERE id = ?", (resolution_id,))
        return _row_to_resolution(row) if row is not None else None

    def for_mutation(self, mutation_id: str) -> ConflictResolution | None:
        """Return the resolution recorded for a mutation, when one exists."""
        row = self.fetch_one(
            f"SELECT * FROM {self.table} WHERE mutation_id = ? ORDER BY resolved_at DESC LIMIT 1",
            (mutation_id,),
        )
        return _row_to_resolution(row) if row is not None else None

    def list_all(
        self, *, client_id: str | None = None, limit: int = 50
    ) -> list[ConflictResolution]:
        """Return resolutions, newest first, optionally scoped by client."""
        if client_id:
            rows = self.fetch_all(
                f"SELECT r.* FROM {self.table} AS r "
                "JOIN v3_pending_mutations AS m ON m.id = r.mutation_id "
                "WHERE m.client_id = ? ORDER BY r.resolved_at DESC LIMIT ?",
                (client_id, limit),
            )
        else:
            rows = self.fetch_all(
                f"SELECT * FROM {self.table} ORDER BY resolved_at DESC LIMIT ?",
                (limit,),
            )
        return [_row_to_resolution(row) for row in rows]

    def delete_for_mutation(self, mutation_id: str) -> int:
        """Remove every resolution attached to a mutation."""
        return self.execute(
            f"DELETE FROM {self.table} WHERE mutation_id = ?",
            (mutation_id,),
        )

    def count_resolutions(self, *, client_id: str | None = None) -> int:
        """Return the number of recorded resolutions."""
        if client_id:
            value = self.fetch_value(
                f"SELECT COUNT(*) FROM {self.table} AS r "
                "JOIN v3_pending_mutations AS m ON m.id = r.mutation_id "
                "WHERE m.client_id = ?",
                (client_id,),
                0,
            )
        else:
            value = self.fetch_value(f"SELECT COUNT(*) FROM {self.table}", (), 0)
        return int(value or 0)


class SyncStore:
    """Aggregate exposing the three repositories used by the sync service."""

    def __init__(self) -> None:
        self.mutations = MutationRepository()
        self.snapshots = SnapshotRepository()
        self.conflicts = ConflictRepository()
