"""HTTP endpoints for the offline mutation queue and synchronisation flow."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from ctf_team_dashboard.features.offline_sync.models import MutationStatus
from ctf_team_dashboard.features.offline_sync.schemas import (
    ClearResponse,
    ConflictResolutionRead,
    ConflictResolveRequest,
    MutationCreate,
    MutationRead,
    ProcessRequest,
    ProcessResponse,
    QueueResponse,
    SyncStatusRead,
)
from ctf_team_dashboard.features.offline_sync.service import OfflineSyncService
from ctf_team_dashboard.features.offline_sync.views import (
    mutation_to_read,
    outcome_to_read,
    resolution_to_read,
    snapshot_to_read,
    status_to_read,
)

router = APIRouter(prefix="/api/sync", tags=["sync"])


def get_sync_service() -> OfflineSyncService:
    """Dependency returning a service bound to the shared database."""
    return OfflineSyncService()


SyncServiceDep = Annotated[OfflineSyncService, Depends(get_sync_service)]
ClientIdQuery = Annotated[str | None, Query(max_length=120)]
StatusQuery = Annotated[MutationStatus | None, Query(alias="status")]
EntityQuery = Annotated[str | None, Query(max_length=120)]
LimitQuery = Annotated[int | None, Query(ge=1, le=500)]


@router.post(
    "/mutations",
    response_model=MutationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Enqueue an offline mutation",
)
def enqueue_mutation(payload: MutationCreate, service: SyncServiceDep) -> MutationRead:
    """Append a locally captured mutation to the FIFO queue."""
    mutation = service.enqueue(
        client_id=payload.client_id,
        entity=payload.entity,
        operation=payload.operation,
        payload=payload.payload,
        base_version=payload.base_version,
        mutation_id=payload.mutation_id,
    )
    return mutation_to_read(mutation)


@router.get("/queue", response_model=QueueResponse, summary="Inspect the mutation queue")
def list_queue(
    service: SyncServiceDep,
    client_id: ClientIdQuery = None,
    status_filter: StatusQuery = None,
    entity: EntityQuery = None,
    limit: LimitQuery = None,
) -> QueueResponse:
    """Return queued mutations in FIFO order with queue counters."""
    mutations = service.list_queue(
        client_id=client_id,
        status=status_filter,
        entity=entity,
        limit=limit,
    )
    stats = service.stats(client_id=client_id)
    return QueueResponse(
        client_id=client_id,
        items=[mutation_to_read(mutation) for mutation in mutations],
        total=len(mutations),
        pending=stats.pending,
        conflicts=stats.conflict,
    )


@router.post("/process", response_model=ProcessResponse, summary="Process a sync batch")
def process_batch(payload: ProcessRequest, service: SyncServiceDep) -> ProcessResponse:
    """Push the next batch of pending mutations against current versions."""
    result = service.process_batch(
        client_id=payload.client_id,
        limit=payload.limit,
        current_versions=payload.current_versions,
    )
    return ProcessResponse(
        outcomes=[outcome_to_read(outcome) for outcome in result.outcomes],
        processed=result.processed,
        applied=result.applied,
        conflicts=result.conflicts,
        skipped=result.skipped,
        failed=result.failed,
        success_rate=result.success_rate,
        started_at=result.started_at,
        finished_at=result.finished_at,
        snapshot=snapshot_to_read(result.snapshot),
    )


@router.post(
    "/conflicts/{mutation_id}/resolve",
    response_model=ConflictResolutionRead,
    summary="Resolve a version conflict",
)
def resolve_conflict(
    mutation_id: str,
    payload: ConflictResolveRequest,
    service: SyncServiceDep,
) -> ConflictResolutionRead:
    """Record a conflict decision and mark the mutation synchronised.

    The path identifier is the identifier of the conflicting mutation, which
    is what the queue inspector exposes to the resolution dialog.
    """
    resolution = service.resolve_conflict(
        mutation_id,
        payload.strategy,
        note=payload.note,
        remote_payload=payload.remote_payload,
        base_payload=payload.base_payload,
    )
    return resolution_to_read(resolution)


@router.get("/status", response_model=SyncStatusRead, summary="Read sync health")
def get_status(
    service: SyncServiceDep,
    client_id: ClientIdQuery = None,
) -> SyncStatusRead:
    """Return queue counters, snapshot freshness and conflict totals."""
    snapshot = service.latest_snapshot(client_id=client_id)
    return status_to_read(
        service.stats(client_id=client_id),
        snapshot,
        stale=service.is_snapshot_stale(client_id=client_id),
        resolution_count=service.resolution_count(client_id=client_id),
    )


@router.delete("/queue", response_model=ClearResponse, summary="Clear synchronised entries")
def clear_queue(
    service: SyncServiceDep,
    client_id: ClientIdQuery = None,
) -> ClearResponse:
    """Delete synchronised mutations while leaving pending work intact."""
    deleted = service.clear_synced(client_id=client_id)
    remaining = service.stats(client_id=client_id).total
    return ClearResponse(client_id=client_id, deleted=deleted, remaining=remaining)
