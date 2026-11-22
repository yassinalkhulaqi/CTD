"""Business rules for queuing, reconciling and clearing offline mutations."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.offline_sync.models import (
    BatchResult,
    ConflictResolution,
    ConflictStrategy,
    MergeResult,
    MutationOperation,
    MutationOutcome,
    MutationStatus,
    PendingMutation,
    SyncOutcome,
    SyncSnapshot,
    SyncStats,
    detect_version_conflict,
    merge_payloads,
    summarise_mutations,
)
from ctf_team_dashboard.features.offline_sync.store import SyncStore

DEFAULT_BATCH_LIMIT = 50
MAX_BATCH_LIMIT = 500
MAX_ATTEMPTS = 5
STALE_SNAPSHOT_SECONDS = 300.0


def generate_id(prefix: str) -> str:
    """Return a short unique identifier with a stable prefix."""
    return f"{prefix}-{uuid4().hex[:12]}"


def encode_payload(payload: dict[str, Any]) -> str:
    """Serialise a payload deterministically for storage."""
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


class OfflineSyncService:
    """Coordinate queue writes, batch processing and conflict resolution."""

    def __init__(
        self,
        store: SyncStore | None = None,
        *,
        clock: Callable[[], datetime] = utcnow,
        id_factory: Callable[[str], str] = generate_id,
    ) -> None:
        self._store = store or SyncStore()
        self._clock = clock
        self._id_factory = id_factory

    # ------------------------------------------------------------------
    # Queue writes
    # ------------------------------------------------------------------
    def enqueue(
        self,
        *,
        client_id: str,
        entity: str,
        operation: MutationOperation,
        payload: dict[str, Any],
        base_version: int = 0,
        mutation_id: str | None = None,
    ) -> PendingMutation:
        """Record a mutation produced while the client was offline.

        Args:
            client_id: Identifier of the device that produced the mutation.
            entity: Logical entity name used for version lookups.
            operation: Create, update or delete.
            payload: JSON serialisable object describing the change.
            base_version: Server version the client based the change on.
            mutation_id: Optional caller supplied identifier for idempotency.

        Returns:
            The newly queued mutation.

        Raises:
            ValidationError: When any input fails validation.
            ConflictError: When the supplied identifier is already queued.
        """
        clean_client = client_id.strip()
        clean_entity = entity.strip()
        if not clean_client:
            raise ValidationError("client_id must not be empty")
        if not clean_entity:
            raise ValidationError("entity must not be empty")
        if not isinstance(operation, MutationOperation):
            raise ValidationError("operation must be create, update or delete")
        if not isinstance(payload, dict):
            raise ValidationError("payload must be a JSON object")
        if base_version < 0:
            raise ValidationError("base_version must not be negative")

        identifier = mutation_id.strip() if mutation_id else self._id_factory("mut")
        if not identifier:
            raise ValidationError("mutation_id must not be empty")
        if self._store.mutations.get(identifier) is not None:
            raise ConflictError(
                f"A mutation with id {identifier!r} already exists",
                details={"mutation_id": identifier},
            )

        mutation = PendingMutation(
            id=identifier,
            client_id=clean_client,
            entity=clean_entity,
            operation=operation,
            payload_json=encode_payload(payload),
            base_version=base_version,
            created_at=self._clock(),
        )
        self._store.mutations.add(mutation)
        return mutation

    def get_mutation(self, mutation_id: str) -> PendingMutation:
        """Return a mutation or raise a typed not-found error."""
        mutation = self._store.mutations.get(mutation_id)
        if mutation is None:
            raise NotFoundError(
                f"Mutation {mutation_id!r} does not exist",
                details={"mutation_id": mutation_id},
            )
        return mutation

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    def list_queue(
        self,
        *,
        client_id: str | None = None,
        status: MutationStatus | None = None,
        entity: str | None = None,
        limit: int | None = None,
    ) -> list[PendingMutation]:
        """Return queued mutations in FIFO order after validating the limit."""
        if limit is not None and limit < 1:
            raise ValidationError("limit must be at least 1")
        return self._store.mutations.list_all(
            client_id=client_id,
            status=status,
            entity=entity,
            limit=limit,
        )

    def stats(self, *, client_id: str | None = None) -> SyncStats:
        """Build a queue summary, including attempt and staleness counters."""
        mutations = self._store.mutations.list_all(client_id=client_id)
        summary = summarise_mutations(mutations)
        stored_attempts = self._store.mutations.total_attempts(client_id=client_id)
        return SyncStats(
            pending=summary.pending,
            synced=summary.synced,
            conflict=summary.conflict,
            total=summary.total,
            attempts=stored_attempts or summary.attempts,
            oldest_pending=self._store.mutations.oldest_pending_at(client_id=client_id),
            newest_synced=self._store.mutations.newest_synced_at(client_id=client_id),
        )

    def latest_snapshot(self, *, client_id: str | None = None) -> SyncSnapshot | None:
        """Return the most recent snapshot for a client or globally."""
        return self._store.snapshots.latest(client_id=client_id)

    def list_resolutions(
        self, *, client_id: str | None = None, limit: int = 50
    ) -> list[ConflictResolution]:
        """Return previously recorded conflict decisions, newest first."""
        if limit < 1:
            raise ValidationError("limit must be at least 1")
        return self._store.conflicts.list_all(client_id=client_id, limit=limit)

    def resolution_count(self, *, client_id: str | None = None) -> int:
        """Return the number of recorded conflict decisions."""
        return self._store.conflicts.count_resolutions(client_id=client_id)

    # ------------------------------------------------------------------
    # Batch processing
    # ------------------------------------------------------------------
    def process_batch(
        self,
        *,
        client_id: str | None = None,
        limit: int = DEFAULT_BATCH_LIMIT,
        current_versions: dict[str, int] | None = None,
    ) -> BatchResult:
        """Push pending mutations in FIFO order against supplied versions.

        A mutation conflicts when the server version for its entity differs
        from the version it was based on.  Conflicted mutations are paused for
        the user to resolve; successful ones are marked synchronised and a new
        snapshot records the resulting version.

        Args:
            client_id: Optional device filter, otherwise all clients are processed.
            limit: Maximum number of pending mutations to examine.
            current_versions: Mapping of entity name to current server version.

        Returns:
            A batch report containing one outcome per examined mutation.
        """
        if limit < 1:
            raise ValidationError("limit must be at least 1")
        if limit > MAX_BATCH_LIMIT:
            raise ValidationError(f"limit must not exceed {MAX_BATCH_LIMIT}")

        versions = current_versions or {}
        started_at = self._clock()
        queued = self._store.mutations.list_pending(client_id=client_id, limit=limit)
        highest_version = self._store.snapshots.highest_version(client_id=client_id)

        outcomes: list[MutationOutcome] = []
        applied = 0
        conflicts = 0
        skipped = 0
        failed = 0

        for mutation in queued:
            if not mutation.is_retryable:
                updated = mutation.mark_conflict(
                    mutation.base_version,
                    "Retry limit reached; manual intervention required",
                )
                failed += 1
                outcomes.append(
                    MutationOutcome(
                        mutation_id=mutation.id,
                        entity=mutation.entity,
                        operation=mutation.operation,
                        result=SyncOutcome.FAILED,
                        detail=updated.last_error,
                    )
                )
                self._store.mutations.save(updated)
                continue

            attempted = mutation.mark_attempt()
            current = versions.get(mutation.entity, mutation.base_version)
            if current < 0:
                raise ValidationError(
                    f"current version for {mutation.entity!r} must not be negative"
                )

            if detect_version_conflict(mutation.base_version, current):
                detail = f"Version conflict: local base v{mutation.base_version}, remote v{current}"
                updated = attempted.mark_conflict(current, detail)
                conflicts += 1
                result = SyncOutcome.CONFLICT
            else:
                next_version = current + 1
                updated = attempted.mark_synced(next_version)
                highest_version = max(highest_version, next_version)
                applied += 1
                result = SyncOutcome.APPLIED

            outcomes.append(
                MutationOutcome(
                    mutation_id=mutation.id,
                    entity=mutation.entity,
                    operation=mutation.operation,
                    result=result,
                    detail=updated.last_error,
                )
            )
            self._store.mutations.save(updated)

        snapshot = SyncSnapshot(
            id=self._id_factory("snap"),
            client_id=client_id or "all",
            synced_at=self._clock(),
            version=highest_version,
            mutation_count=applied,
            conflict_count=conflicts,
            note=f"batch of {len(queued)}, failed {failed}, skipped {skipped}",
        )
        self._store.snapshots.add(snapshot)

        return BatchResult(
            outcomes=tuple(outcomes),
            applied=applied,
            conflicts=conflicts,
            skipped=skipped,
            failed=failed,
            snapshot=snapshot,
            started_at=started_at,
            finished_at=self._clock(),
        )

    # ------------------------------------------------------------------
    # Conflict handling
    # ------------------------------------------------------------------
    def resolve_conflict(
        self,
        mutation_id: str,
        strategy: ConflictStrategy,
        *,
        note: str = "",
        remote_payload: dict[str, Any] | None = None,
        base_payload: dict[str, Any] | None = None,
    ) -> ConflictResolution:
        """Settle a conflicted mutation and mark it synchronised.

        Args:
            mutation_id: Identifier of the paused mutation.
            strategy: Local wins, remote wins or a three-way field merge.
            note: Optional explanation recorded on the resolution.
            remote_payload: Current server payload used for comparison.
            base_payload: Payload the client originally edited.

        Returns:
            The persisted resolution record.

        Raises:
            NotFoundError: When the mutation does not exist.
            ConflictError: When the mutation has no outstanding conflict.
        """
        mutation = self.get_mutation(mutation_id)
        if not mutation.is_conflicted:
            raise ConflictError(
                f"Mutation {mutation_id!r} is not awaiting resolution",
                details={"status": mutation.status.value},
            )
        if not isinstance(strategy, ConflictStrategy):
            raise ValidationError("strategy must be local_wins, remote_wins or merge")

        remote = remote_payload or {}
        base = base_payload or {}
        merged: MergeResult = merge_payloads(base, mutation.payload, remote, strategy)
        remote_version = mutation.resolved_version or mutation.base_version + 1

        resolution = ConflictResolution(
            id=self._id_factory("res"),
            mutation_id=mutation.id,
            strategy=strategy,
            resolved_at=self._clock(),
            local_version=mutation.base_version,
            remote_version=remote_version,
            field_changes_json=merged.to_json(),
            notes=note.strip(),
        )
        self._store.conflicts.add(resolution)

        reconciled = mutation.with_payload(merged.payload).mark_synced(remote_version)
        self._store.mutations.save(reconciled)
        return resolution

    def retry_conflict(self, mutation_id: str) -> PendingMutation:
        """Return a conflicted mutation to the pending queue for another try."""
        mutation = self.get_mutation(mutation_id)
        if not mutation.is_conflicted:
            raise ConflictError(
                f"Mutation {mutation_id!r} is not awaiting resolution",
                details={"status": mutation.status.value},
            )
        requeued = mutation.requeue()
        self._store.mutations.save(requeued)
        return requeued

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def clear_synced(self, *, client_id: str | None = None) -> int:
        """Delete synchronised mutations and their resolution records."""
        synced = self._store.mutations.list_all(client_id=client_id, status=MutationStatus.SYNCED)
        for mutation in synced:
            self._store.conflicts.delete_for_mutation(mutation.id)
        return self._store.mutations.delete_synced(client_id=client_id)

    def is_snapshot_stale(
        self,
        *,
        client_id: str | None = None,
        threshold: float = STALE_SNAPSHOT_SECONDS,
    ) -> bool:
        """Return whether the latest snapshot is missing or too old."""
        snapshot = self.latest_snapshot(client_id=client_id)
        if snapshot is None:
            return True
        return snapshot.age_seconds() > timedelta(seconds=threshold).total_seconds()
