"""Mapping helpers from domain entities to typed API representations."""

from __future__ import annotations

from ctf_team_dashboard.features.offline_sync.models import (
    ConflictResolution,
    FieldChange,
    MutationOutcome,
    PendingMutation,
    SyncSnapshot,
    SyncStats,
    display_value,
)
from ctf_team_dashboard.features.offline_sync.schemas import (
    ConflictResolutionRead,
    FieldChangeRead,
    MutationOutcomeRead,
    MutationRead,
    SnapshotRead,
    SyncStatusRead,
)


def mutation_to_read(mutation: PendingMutation) -> MutationRead:
    """Render a pending mutation as an API model."""
    return MutationRead(
        id=mutation.id,
        client_id=mutation.client_id,
        entity=mutation.entity,
        operation=mutation.operation,
        payload=mutation.payload,
        base_version=mutation.base_version,
        created_at=mutation.created_at,
        status=mutation.status,
        attempts=mutation.attempts,
        last_error=mutation.last_error,
        resolved_version=mutation.resolved_version,
        entity_label=mutation.entity_label,
        is_pending=mutation.is_pending,
        next_retry_delay=mutation.next_retry_delay,
    )


def snapshot_to_read(snapshot: SyncSnapshot | None) -> SnapshotRead | None:
    """Render a snapshot as an API model, preserving ``None``."""
    if snapshot is None:
        return None
    return SnapshotRead(
        id=snapshot.id,
        client_id=snapshot.client_id,
        synced_at=snapshot.synced_at,
        version=snapshot.version,
        mutation_count=snapshot.mutation_count,
        conflict_count=snapshot.conflict_count,
        note=snapshot.note,
        total_count=snapshot.total_count,
        success_rate=snapshot.success_rate,
    )


def outcome_to_read(outcome: MutationOutcome) -> MutationOutcomeRead:
    """Render one batch outcome as an API model."""
    return MutationOutcomeRead(
        mutation_id=outcome.mutation_id,
        entity=outcome.entity,
        operation=outcome.operation,
        result=outcome.result,
        detail=outcome.detail,
        succeeded=outcome.succeeded,
        needs_attention=outcome.needs_attention,
    )


def field_change_to_read(change: FieldChange) -> FieldChangeRead:
    """Render a field decision as an API model."""
    return FieldChangeRead(
        field=change.field,
        local_value=display_value(change.local_value),
        remote_value=display_value(change.remote_value),
        chosen_value=display_value(change.chosen_value),
        contested=change.contested,
        chose_local=change.chose_local,
        summary=change.summary,
    )


def resolution_to_read(resolution: ConflictResolution) -> ConflictResolutionRead:
    """Render a conflict resolution, including its field decisions."""
    return ConflictResolutionRead(
        id=resolution.id,
        mutation_id=resolution.mutation_id,
        strategy=resolution.strategy,
        resolved_at=resolution.resolved_at,
        local_version=resolution.local_version,
        remote_version=resolution.remote_version,
        notes=resolution.notes,
        strategy_label=resolution.strategy_label,
        version_gap=resolution.version_gap,
        was_merged=resolution.was_merged,
        summary=resolution.summary,
        field_changes=[field_change_to_read(change) for change in resolution.changes],
    )


def status_to_read(
    stats: SyncStats,
    snapshot: SyncSnapshot | None,
    *,
    stale: bool,
    resolution_count: int,
) -> SyncStatusRead:
    """Combine queue statistics and snapshot freshness into a status model."""
    return SyncStatusRead(
        pending=stats.pending,
        synced=stats.synced,
        conflict=stats.conflict,
        total=stats.total,
        attempts=stats.attempts,
        backlog=stats.backlog,
        completion_rate=stats.completion_rate,
        average_attempts=stats.average_attempts,
        health_label=stats.health_label,
        has_conflicts=stats.has_conflicts,
        oldest_pending=stats.oldest_pending,
        newest_synced=stats.newest_synced,
        stale=stale,
        resolution_count=resolution_count,
        latest_snapshot=snapshot_to_read(snapshot),
    )
