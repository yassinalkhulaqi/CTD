"""HTTP endpoints for the activity timeline feature."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from ctf_team_dashboard.features.activity_timeline.models import (
    DEFAULT_LIMIT,
    DEFAULT_MAX_AGE_DAYS,
    MAX_LIMIT,
    ActorSummary,
    EventCluster,
    Importance,
    PruneResult,
    TimelineBucket,
    TimelineEvent,
    TimelineFilter,
    TimelinePage,
    TimelineStats,
)
from ctf_team_dashboard.features.activity_timeline.schemas import (
    ActorRead,
    ClusterRead,
    DeleteResultRead,
    PruneResultRead,
    TimelineBucketRead,
    TimelineEventCreate,
    TimelineEventRead,
    TimelineKindsRead,
    TimelinePageRead,
    TimelineStatsRead,
)
from ctf_team_dashboard.features.activity_timeline.service import TimelineService

router = APIRouter(prefix="/api/timeline", tags=["timeline"])


def get_timeline_service() -> TimelineService:
    """Dependency returning a service bound to the shared database."""
    return TimelineService()


TimelineServiceDep = Annotated[TimelineService, Depends(get_timeline_service)]


def _event_to_read(event: TimelineEvent) -> TimelineEventRead:
    """Map a domain event onto its API representation."""
    kind = event.timeline_kind
    importance = event.importance_level
    return TimelineEventRead(
        id=event.id,
        team_id=event.team_id,
        kind=event.kind,
        actor_id=event.actor_id,
        actor_name=event.actor_name,
        summary=event.summary,
        payload_json=event.payload_json,
        importance=event.importance,
        occurred_at=event.occurred_at,
        kind_label=kind.label,
        kind_icon=kind.icon,
        kind_color=kind.color,
        importance_label=importance.label,
        importance_tone=importance.tone,
        importance_rank=event.importance_rank,
        actor_initials=event.actor_initials,
        date_key=event.date_key,
        hour_key=event.hour_key,
        hour_of_day=event.hour_of_day,
        relative_label=event.relative_label(),
    )


def _cluster_to_read(cluster: EventCluster) -> ClusterRead:
    """Map a display cluster onto its API representation."""
    return ClusterRead(
        id=cluster.id,
        event=_event_to_read(cluster.event),
        count=cluster.count,
        first_at=cluster.occurred_at,
        last_at=cluster.last_at or cluster.occurred_at,
        is_merged=cluster.is_merged,
        count_label=cluster.count_label,
        importance_rank=cluster.importance_rank,
    )


def _bucket_to_read(bucket: TimelineBucket) -> TimelineBucketRead:
    """Map a day/hour bucket and its children onto the API schema."""
    return TimelineBucketRead(
        key=bucket.key,
        label=bucket.label,
        level=str(bucket.level),
        events=[_cluster_to_read(cluster) for cluster in bucket.events],
        children=[_bucket_to_read(child) for child in bucket.children],
        count=bucket.count,
        item_count=bucket.item_count,
        critical_count=bucket.critical_count,
        peak_importance=str(bucket.peak_importance),
    )


def _page_to_read(page: TimelinePage) -> TimelinePageRead:
    """Map a paginated result onto its API representation."""
    return TimelinePageRead(
        events=[_event_to_read(event) for event in page.events],
        clusters=[_cluster_to_read(cluster) for cluster in page.clusters],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
        has_more=page.has_more,
        next_offset=page.next_offset,
        page_number=page.page_number,
    )


def _stats_to_read(stats: TimelineStats) -> TimelineStatsRead:
    """Map aggregated statistics onto their API representation."""
    return TimelineStatsRead(
        total=stats.total,
        by_kind=dict(stats.by_kind),
        by_hour=dict(stats.by_hour),
        by_importance=dict(stats.by_importance),
        unique_actors=stats.unique_actors,
        critical_count=stats.critical_count,
        first_seen=stats.first_seen,
        last_seen=stats.last_seen,
        generated_at=stats.generated_at,
        busiest_kind=stats.busiest_kind,
        busiest_hour=stats.busiest_hour,
        critical_ratio=stats.critical_ratio,
        average_per_hour=stats.average_per_hour,
        top_kinds=[[kind, count] for kind, count in stats.top_kinds()],
    )


def _actor_to_read(actor: ActorSummary) -> ActorRead:
    """Map an actor summary onto its API representation."""
    return ActorRead(
        actor_id=actor.actor_id,
        actor_name=actor.actor_name,
        event_count=actor.event_count,
        critical_count=actor.critical_count,
        last_seen=actor.last_seen,
        kinds=list(actor.kinds),
        label=actor.label,
        initials=actor.initials,
        first_kind=str(actor.first_kind),
    )


def _prune_to_read(result: PruneResult) -> PruneResultRead:
    """Map a prune result onto its API representation."""
    return PruneResultRead(
        cutoff=result.cutoff,
        deleted=result.deleted,
        max_age_days=result.max_age_days,
        retained=result.retained,
        description=result.description,
    )


@router.get("", response_model=TimelinePageRead)
def list_events(
    service: TimelineServiceDep,
    kinds: Annotated[list[str] | None, Query()] = None,
    actors: Annotated[list[str] | None, Query()] = None,
    importance: Annotated[list[Importance] | None, Query()] = None,
    team_id: str | None = None,
    from_at: Annotated[datetime | None, Query(alias="from")] = None,
    to_at: Annotated[datetime | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TimelinePageRead:
    """Return a filtered, deduplicated and paginated timeline page."""
    timeline_filter = TimelineFilter(
        kinds=tuple(kinds or ()),
        actors=tuple(actors or ()),
        importance=tuple(str(item) for item in importance or ()),
        team_id=team_id,
        from_at=from_at,
        to_at=to_at,
        limit=limit,
        offset=offset,
    )
    return _page_to_read(service.query(timeline_filter))


@router.post(
    "",
    response_model=TimelineEventRead,
    status_code=status.HTTP_201_CREATED,
)
def create_event(payload: TimelineEventCreate, service: TimelineServiceDep) -> TimelineEventRead:
    """Record a new activity event."""
    event = service.record_event(
        team_id=payload.team_id,
        kind=payload.kind,
        actor_id=payload.actor_id,
        actor_name=payload.actor_name,
        summary=payload.summary,
        payload=payload.payload,
        importance=payload.importance,
        occurred_at=payload.occurred_at,
    )
    return _event_to_read(event)


@router.get("/groups", response_model=list[TimelineBucketRead])
def get_groups(
    service: TimelineServiceDep,
    kinds: Annotated[list[str] | None, Query()] = None,
    actors: Annotated[list[str] | None, Query()] = None,
    team_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = MAX_LIMIT,
) -> list[TimelineBucketRead]:
    """Return timeline groups nested by day and hour."""
    timeline_filter = TimelineFilter(
        kinds=tuple(kinds or ()),
        actors=tuple(actors or ()),
        team_id=team_id,
        limit=limit,
    )
    return [_bucket_to_read(bucket) for bucket in service.groups(timeline_filter)]


@router.get("/stats", response_model=TimelineStatsRead)
def get_stats(
    service: TimelineServiceDep,
    team_id: str | None = None,
    kinds: Annotated[list[str] | None, Query()] = None,
    actors: Annotated[list[str] | None, Query()] = None,
    from_at: Annotated[datetime | None, Query(alias="from")] = None,
    to_at: Annotated[datetime | None, Query(alias="to")] = None,
) -> TimelineStatsRead:
    """Return aggregated counts by kind, importance and hour."""
    timeline_filter = TimelineFilter(
        kinds=tuple(kinds or ()),
        actors=tuple(actors or ()),
        team_id=team_id,
        from_at=from_at,
        to_at=to_at,
    )
    return _stats_to_read(service.stats(timeline_filter))


@router.get("/actors", response_model=list[ActorRead])
def get_actors(
    service: TimelineServiceDep,
    team_id: str | None = None,
) -> list[ActorRead]:
    """Return actors ordered by their recorded activity."""
    return [_actor_to_read(actor) for actor in service.list_actors(team_id)]


@router.get("/kinds", response_model=TimelineKindsRead)
def get_kinds(service: TimelineServiceDep) -> TimelineKindsRead:
    """Return the kinds currently present in the timeline store."""
    kinds = service.list_kinds()
    return TimelineKindsRead(kinds=list(kinds), count=len(kinds))


@router.post("/prune", response_model=PruneResultRead)
def prune_events(
    service: TimelineServiceDep,
    max_age_days: Annotated[int, Query(ge=1)] = DEFAULT_MAX_AGE_DAYS,
) -> PruneResultRead:
    """Delete events older than the requested age in days."""
    return _prune_to_read(service.prune(max_age_days))


@router.get("/{event_id}", response_model=TimelineEventRead)
def get_event(event_id: str, service: TimelineServiceDep) -> TimelineEventRead:
    """Return a single timeline event."""
    return _event_to_read(service.get_event(event_id))


@router.delete("/{event_id}", response_model=DeleteResultRead)
def delete_event(event_id: str, service: TimelineServiceDep) -> DeleteResultRead:
    """Delete a single timeline event."""
    service.delete_event(event_id)
    return DeleteResultRead(id=event_id, deleted=True)
