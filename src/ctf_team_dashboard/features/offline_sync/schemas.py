"""Typed request and response schemas for the offline synchronisation API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ctf_team_dashboard.features.offline_sync.models import (
    ConflictStrategy,
    MutationOperation,
    MutationStatus,
    SyncOutcome,
)


class SyncApiModel(BaseModel):
    """Base model with permissive attribute population and stable aliases."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MutationCreate(SyncApiModel):
    """Body used to enqueue a local mutation."""

    client_id: str = Field(min_length=1, max_length=120)
    entity: str = Field(min_length=1, max_length=120)
    operation: MutationOperation
    payload: dict[str, Any] = Field(default_factory=dict)
    base_version: int = Field(default=0, ge=0)
    mutation_id: str | None = Field(default=None, max_length=120)


class MutationRead(SyncApiModel):
    """A queued mutation as returned by the API."""

    id: str
    client_id: str
    entity: str
    operation: MutationOperation
    payload: dict[str, Any]
    base_version: int
    created_at: datetime
    status: MutationStatus
    attempts: int
    last_error: str
    resolved_version: int | None = None
    entity_label: str
    is_pending: bool
    next_retry_delay: float


class SnapshotRead(SyncApiModel):
    """A completed synchronisation snapshot."""

    id: str
    client_id: str
    synced_at: datetime
    version: int
    mutation_count: int
    conflict_count: int
    note: str
    total_count: int
    success_rate: float


class QueueResponse(SyncApiModel):
    """The FIFO queue together with lightweight counters."""

    client_id: str | None = None
    items: list[MutationRead]
    total: int
    pending: int
    conflicts: int
    oldest_first: bool = True


class ProcessRequest(SyncApiModel):
    """Body controlling one processing batch."""

    client_id: str | None = None
    limit: int = Field(default=50, ge=1, le=500)
    current_versions: dict[str, int] = Field(default_factory=dict)


class MutationOutcomeRead(SyncApiModel):
    """Result of pushing one mutation during a batch."""

    mutation_id: str
    entity: str
    operation: MutationOperation
    result: SyncOutcome
    detail: str
    succeeded: bool
    needs_attention: bool


class ProcessResponse(SyncApiModel):
    """Summary returned by the batch endpoint."""

    outcomes: list[MutationOutcomeRead]
    processed: int
    applied: int
    conflicts: int
    skipped: int
    failed: int
    success_rate: float
    started_at: datetime
    finished_at: datetime
    snapshot: SnapshotRead | None = None


class FieldChangeRead(SyncApiModel):
    """One field level decision made during a merge."""

    field: str
    local_value: Any | None
    remote_value: Any | None
    chosen_value: Any | None
    contested: bool
    chose_local: bool
    summary: str


class ConflictResolveRequest(SyncApiModel):
    """Body selecting the strategy for a conflict resolution."""

    strategy: ConflictStrategy
    note: str = Field(default="", max_length=500)
    remote_payload: dict[str, Any] | None = None
    base_payload: dict[str, Any] | None = None


class ConflictResolutionRead(SyncApiModel):
    """A persisted conflict decision."""

    id: str
    mutation_id: str
    strategy: ConflictStrategy
    resolved_at: datetime
    local_version: int
    remote_version: int
    notes: str
    strategy_label: str
    version_gap: int
    was_merged: bool
    summary: str
    field_changes: list[FieldChangeRead]


class SyncStatusRead(SyncApiModel):
    """Health summary rendered by the sync status card."""

    pending: int
    synced: int
    conflict: int
    total: int
    attempts: int
    backlog: int
    completion_rate: float
    average_attempts: float
    health_label: str
    has_conflicts: bool
    oldest_pending: datetime | None
    newest_synced: datetime | None
    stale: bool
    resolution_count: int
    latest_snapshot: SnapshotRead | None = None


class ClearResponse(SyncApiModel):
    """Result of clearing synchronised queue entries."""

    client_id: str | None
    deleted: int
    remaining: int
