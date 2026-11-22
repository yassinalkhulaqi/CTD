"""Typed request and response models for the event lifecycle API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ctf_team_dashboard.features.ctf_events.models import (
    MAX_DESCRIPTION_LENGTH,
    MAX_NAME_LENGTH,
    MAX_TAGS,
    MAX_TEAM_SIZE,
    MIN_NAME_LENGTH,
    MIN_TEAM_SIZE,
    CtfEvent,
    EventFormat,
    EventOverlap,
    EventRegistration,
    EventStats,
    EventStatus,
    EventTask,
    RegistrationStatus,
)


class EventApiModel(BaseModel):
    """Base model with attribute serialisation enabled."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EventRead(EventApiModel):
    """An event as returned by the API, including derived lifecycle data."""

    id: str
    name: str
    slug: str
    description: str
    format: EventFormat
    starts_at: datetime
    ends_at: datetime
    status: EventStatus
    stored_status: EventStatus
    max_team_size: int
    registration_open: bool
    website_url: str
    tags: list[str]
    created_at: datetime
    countdown_seconds: int
    countdown_label: str
    seconds_until_start: int
    seconds_remaining: int
    duration_seconds: int
    progress: float
    is_live: bool
    is_upcoming: bool
    is_archived: bool
    accepts_registrations: bool


class EventCreate(EventApiModel):
    """Payload used to create an event."""

    name: str = Field(min_length=MIN_NAME_LENGTH, max_length=MAX_NAME_LENGTH)
    starts_at: datetime
    ends_at: datetime
    description: str = Field(default="", max_length=MAX_DESCRIPTION_LENGTH)
    format: EventFormat = EventFormat.JEOPARDY
    status: EventStatus = EventStatus.UPCOMING
    max_team_size: int = Field(default=8, ge=MIN_TEAM_SIZE, le=MAX_TEAM_SIZE)
    registration_open: bool = True
    website_url: str = Field(default="", max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=MAX_TAGS)

    @field_validator("status")
    @classmethod
    def _reject_live(cls, value: EventStatus) -> EventStatus:
        """Ensure the live status cannot be set directly."""
        if value is EventStatus.LIVE:
            raise ValueError("The live status is derived from the event window")
        return value


class EventUpdate(EventApiModel):
    """Partial payload used to edit an event."""

    name: str | None = Field(default=None, min_length=MIN_NAME_LENGTH, max_length=MAX_NAME_LENGTH)
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    format: EventFormat | None = None
    status: EventStatus | None = None
    max_team_size: int | None = Field(default=None, ge=MIN_TEAM_SIZE, le=MAX_TEAM_SIZE)
    registration_open: bool | None = None
    website_url: str | None = Field(default=None, max_length=500)
    tags: list[str] | None = Field(default=None, max_length=MAX_TAGS)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    slug: str | None = Field(default=None, max_length=80)

    @field_validator("status")
    @classmethod
    def _reject_live(cls, value: EventStatus | None) -> EventStatus | None:
        """Ensure the live status cannot be set directly."""
        if value is EventStatus.LIVE:
            raise ValueError("The live status is derived from the event window")
        return value


class EventList(EventApiModel):
    """A filtered catalogue of events."""

    events: list[EventRead]
    total: int
    window: str


class RegistrationRead(EventApiModel):
    """A team's place in an event."""

    id: str
    event_id: str
    team_id: str
    status: RegistrationStatus
    registered_at: datetime
    is_confirmed: bool
    is_waitlisted: bool


class RegistrationList(EventApiModel):
    """The registration ledger of an event."""

    event_id: str
    registrations: list[RegistrationRead]
    confirmed: int
    waitlisted: int


class RegisterRequest(EventApiModel):
    """Payload used to register a team for an event."""

    team_id: str = Field(min_length=1, max_length=120)


class CancelRequest(EventApiModel):
    """Payload used to cancel a registration."""

    team_id: str = Field(min_length=1, max_length=120)


class CancellationRead(EventApiModel):
    """Outcome of a cancellation, including a possible waitlist promotion."""

    event_id: str
    team_id: str
    status: RegistrationStatus
    promoted_team_id: str | None = None
    promotion: RegistrationRead | None = None


class TaskRead(EventApiModel):
    """A checklist item of an event."""

    id: str
    event_id: str
    title: str
    done: bool
    due_at: datetime | None
    is_overdue: bool


class TaskCreate(EventApiModel):
    """Payload used to add a checklist item."""

    title: str = Field(min_length=1, max_length=160)
    due_at: datetime | None = None


class EventStatsRead(EventApiModel):
    """Registration figures for an event."""

    event_id: str
    capacity: int
    confirmed: int
    waitlisted: int
    cancelled: int
    promotions: int
    total: int
    available_slots: int
    is_full: bool
    capacity_ratio: float
    fill_percentage: int
    waitlist_pressure: float


class EventStatsList(EventApiModel):
    """Statistics of several events."""

    events: list[EventStatsRead]


class EventOverlapRead(EventApiModel):
    """A scheduling conflict between two live events."""

    team_id: str
    first_event_id: str
    first_event_name: str
    second_event_id: str
    second_event_name: str
    overlap_seconds: float


class EventOverlapList(EventApiModel):
    """All scheduling conflicts of a team."""

    team_id: str
    overlaps: list[EventOverlapRead]


class MessageResponse(EventApiModel):
    """Generic acknowledgement payload."""

    message: str
    id: str | None = None


def event_to_read(event: CtfEvent, *, now: datetime | None = None) -> EventRead:
    """Convert a domain event into its API representation."""
    derived = event.status_at(now)
    return EventRead(
        id=event.id,
        name=event.name,
        slug=event.slug,
        description=event.description,
        format=event.format,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        status=derived,
        stored_status=event.status,
        max_team_size=event.max_team_size,
        registration_open=event.registration_open,
        website_url=event.website_url,
        tags=list(event.tags),
        created_at=event.created_at,
        countdown_seconds=event.countdown_seconds(now),
        countdown_label=event.countdown_label(now),
        seconds_until_start=event.seconds_until_start(now),
        seconds_remaining=event.seconds_remaining(now),
        duration_seconds=event.duration_seconds,
        progress=round(event.progress(now), 4),
        is_live=derived is EventStatus.LIVE,
        is_upcoming=derived is EventStatus.UPCOMING,
        is_archived=derived is EventStatus.ARCHIVED,
        accepts_registrations=event.accepts_registrations(now),
    )


def registration_to_read(registration: EventRegistration) -> RegistrationRead:
    """Convert a registration into its API representation."""
    return RegistrationRead(
        id=registration.id,
        event_id=registration.event_id,
        team_id=registration.team_id,
        status=registration.status,
        registered_at=registration.registered_at,
        is_confirmed=registration.is_confirmed,
        is_waitlisted=registration.is_waitlisted,
    )


def task_to_read(task: EventTask, *, now: datetime | None = None) -> TaskRead:
    """Convert a checklist item into its API representation."""
    return TaskRead(
        id=task.id,
        event_id=task.event_id,
        title=task.title,
        done=task.done,
        due_at=task.due_at,
        is_overdue=task.is_overdue(now),
    )


def stats_to_read(stats: EventStats) -> EventStatsRead:
    """Convert registration statistics into their API representation."""
    return EventStatsRead(
        event_id=stats.event_id,
        capacity=stats.capacity,
        confirmed=stats.confirmed,
        waitlisted=stats.waitlisted,
        cancelled=stats.cancelled,
        promotions=stats.promotions,
        total=stats.total,
        available_slots=stats.available_slots,
        is_full=stats.is_full,
        capacity_ratio=round(stats.capacity_ratio, 4),
        fill_percentage=stats.fill_percentage,
        waitlist_pressure=round(stats.waitlist_pressure, 4),
    )


def overlap_to_read(overlap: EventOverlap) -> EventOverlapRead:
    """Convert a scheduling conflict into its API representation."""
    return EventOverlapRead(
        team_id=overlap.team_id,
        first_event_id=overlap.first.id,
        first_event_name=overlap.first.name,
        second_event_id=overlap.second.id,
        second_event_name=overlap.second.name,
        overlap_seconds=round(overlap.seconds, 3),
    )
