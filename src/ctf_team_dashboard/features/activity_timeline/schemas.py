"""Typed Pydantic schemas for the activity timeline HTTP API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ctf_team_dashboard.features.activity_timeline.models import (
    MAX_ACTOR_NAME_LENGTH,
    MAX_IDENTIFIER_LENGTH,
    MAX_LIMIT,
    MAX_SUMMARY_LENGTH,
)


class TimelineApiModel(BaseModel):
    """Shared configuration for every timeline schema."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TimelineEventRead(TimelineApiModel):
    """The API representation of one timeline event."""

    id: str
    team_id: str
    kind: str
    actor_id: str
    actor_name: str
    summary: str
    payload_json: str
    importance: str
    occurred_at: datetime
    kind_label: str
    kind_icon: str
    kind_color: str
    importance_label: str
    importance_tone: str
    importance_rank: int
    actor_initials: str
    date_key: str
    hour_key: str
    hour_of_day: int
    relative_label: str


class ClusterRead(TimelineApiModel):
    """A display item produced by consecutive-event deduplication."""

    id: str
    event: TimelineEventRead
    count: int = Field(ge=1)
    first_at: datetime
    last_at: datetime
    is_merged: bool
    count_label: str
    importance_rank: int


class TimelineBucketRead(TimelineApiModel):
    """A day or hour group of clustered events."""

    key: str
    label: str
    level: str
    events: list[ClusterRead] = Field(default_factory=list)
    children: list[TimelineBucketRead] = Field(default_factory=list)
    count: int = 0
    item_count: int = 0
    critical_count: int = 0
    peak_importance: str


TimelineBucketRead.model_rebuild()


class TimelinePageRead(TimelineApiModel):
    """A page of deduplicated events with pagination metadata."""

    events: list[TimelineEventRead]
    clusters: list[ClusterRead]
    total: int
    limit: int
    offset: int
    has_more: bool
    next_offset: int | None
    page_number: int


class TimelineStatsRead(TimelineApiModel):
    """Aggregated timeline counters."""

    total: int
    by_kind: dict[str, int]
    by_hour: dict[str, int]
    by_importance: dict[str, int]
    unique_actors: int
    critical_count: int
    first_seen: datetime | None
    last_seen: datetime | None
    generated_at: datetime
    busiest_kind: str | None
    busiest_hour: str | None
    critical_ratio: float
    average_per_hour: float
    top_kinds: list[list[str | int]]


class ActorRead(TimelineApiModel):
    """Aggregated activity for a single actor."""

    actor_id: str
    actor_name: str
    event_count: int
    critical_count: int
    last_seen: datetime | None
    kinds: list[str]
    label: str
    initials: str
    first_kind: str


class TimelineEventCreate(TimelineApiModel):
    """Payload accepted by ``POST /api/timeline``."""

    team_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    kind: str = Field(min_length=1, max_length=60)
    actor_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    actor_name: str = Field(min_length=1, max_length=MAX_ACTOR_NAME_LENGTH)
    summary: str = Field(min_length=1, max_length=MAX_SUMMARY_LENGTH)
    payload: dict[str, object] = Field(default_factory=dict)
    importance: str = "normal"
    occurred_at: datetime | None = None


class PruneResultRead(TimelineApiModel):
    """The outcome of an age based prune."""

    cutoff: datetime
    deleted: int
    max_age_days: int
    retained: int
    description: str


class DeleteResultRead(TimelineApiModel):
    """Confirmation payload returned after a successful delete."""

    id: str
    deleted: bool = True


class TimelineKindsRead(TimelineApiModel):
    """The kinds currently present in the store."""

    kinds: list[str]
    count: int


class TimelineQueryRead(TimelineApiModel):
    """Echo of the filters used for a timeline query."""

    kinds: list[str]
    actors: list[str]
    importance: list[str]
    team_id: str | None
    from_at: datetime | None
    to_at: datetime | None
    limit: int = Field(default=50, ge=1, le=MAX_LIMIT)
    offset: int = Field(default=0, ge=0)
