"""HTTP API for the CTF event lifecycle.

All routes are mounted under ``/api/events``.  Static paths such as
``/api/events/upcoming`` are registered before the ``{event_id}`` routes so a
literal word can never be mistaken for an identifier.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.features.ctf_events.models import EventFormat, EventStatus
from ctf_team_dashboard.features.ctf_events.schemas import (
    CancellationRead,
    CancelRequest,
    EventCreate,
    EventList,
    EventOverlapList,
    EventRead,
    EventStatsList,
    EventStatsRead,
    EventUpdate,
    MessageResponse,
    RegisterRequest,
    RegistrationList,
    RegistrationRead,
    TaskCreate,
    TaskRead,
    event_to_read,
    overlap_to_read,
    registration_to_read,
    stats_to_read,
    task_to_read,
)
from ctf_team_dashboard.features.ctf_events.service import EventFilters, EventService

router = APIRouter(prefix="/api/events", tags=["events"])


def get_event_service() -> EventService:
    """Build an event service bound to the current database."""
    return EventService()


ServiceDep = Annotated[EventService, Depends(get_event_service)]
StatusQuery = Annotated[EventStatus | None, Query(alias="status")]
FormatQuery = Annotated[EventFormat | None, Query(alias="format")]
WindowQuery = Annotated[str, Query(pattern=r"^(all|draft|upcoming|live|archived)$")]
PageLimitQuery = Annotated[int, Query(ge=1, le=500)]
ShortLimitQuery = Annotated[int, Query(ge=1, le=200)]


@router.get("", response_model=EventList)
def list_events(
    service: ServiceDep,
    status_filter: StatusQuery = None,
    format_filter: FormatQuery = None,
    tag: str | None = None,
    search: str | None = None,
    registration_open: bool | None = None,
    window: WindowQuery = "all",
    limit: PageLimitQuery = 100,
) -> EventList:
    """Return the event catalogue with optional filters."""
    events = service.list_events(
        EventFilters(
            status=status_filter,
            format=format_filter,
            tag=tag,
            search=search,
            registration_open=registration_open,
            window=window,
            limit=limit,
        )
    )
    now = utcnow()
    return EventList(
        events=[event_to_read(event, now=now) for event in events],
        total=len(events),
        window=window,
    )


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, service: ServiceDep) -> EventRead:
    """Create a new event."""
    event = service.create_event(
        payload.name,
        payload.starts_at,
        payload.ends_at,
        description=payload.description,
        event_format=payload.format,
        status=payload.status,
        max_team_size=payload.max_team_size,
        registration_open=payload.registration_open,
        website_url=payload.website_url,
        tags=payload.tags,
    )
    return event_to_read(event)


@router.get("/upcoming", response_model=EventList)
def upcoming_events(service: ServiceDep, limit: ShortLimitQuery = 20) -> EventList:
    """Return the next events whose windows have not opened yet."""
    events = service.upcoming_events(limit=limit)
    now = utcnow()
    return EventList(
        events=[event_to_read(event, now=now) for event in events],
        total=len(events),
        window="upcoming",
    )


@router.get("/live", response_model=EventList)
def live_events(service: ServiceDep, limit: ShortLimitQuery = 20) -> EventList:
    """Return the events currently in progress."""
    events = service.live_events(limit=limit)
    now = utcnow()
    return EventList(
        events=[event_to_read(event, now=now) for event in events],
        total=len(events),
        window="live",
    )


@router.get("/stats", response_model=EventStatsList)
def all_stats(service: ServiceDep) -> EventStatsList:
    """Return registration statistics for every event."""
    stats = [stats_to_read(service.stats(event.id)) for event in service.list_events()]
    return EventStatsList(events=stats)


@router.get("/overlaps", response_model=EventOverlapList)
def team_overlaps(service: ServiceDep, team_id: str) -> EventOverlapList:
    """Return live event clashes for a team."""
    overlaps = service.find_overlaps(team_id)
    return EventOverlapList(
        team_id=team_id,
        overlaps=[overlap_to_read(overlap) for overlap in overlaps],
    )


@router.get("/{event_id}", response_model=EventRead)
def get_event(event_id: str, service: ServiceDep) -> EventRead:
    """Return a single event."""
    return event_to_read(service.get_event(event_id))


@router.patch("/{event_id}", response_model=EventRead)
def update_event(event_id: str, payload: EventUpdate, service: ServiceDep) -> EventRead:
    """Apply a partial update to an event."""
    changed = service.update_event(
        event_id,
        name=payload.name,
        description=payload.description,
        event_format=payload.format,
        status=payload.status,
        max_team_size=payload.max_team_size,
        registration_open=payload.registration_open,
        website_url=payload.website_url,
        tags=payload.tags,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        slug=payload.slug,
    )
    return event_to_read(changed)


@router.delete("/{event_id}", response_model=MessageResponse)
def delete_event(event_id: str, service: ServiceDep) -> MessageResponse:
    """Delete an event and its related records."""
    service.delete_event(event_id)
    return MessageResponse(message="Event deleted", id=event_id)


@router.post(
    "/{event_id}/register",
    response_model=RegistrationRead,
    status_code=status.HTTP_201_CREATED,
)
def register(event_id: str, payload: RegisterRequest, service: ServiceDep) -> RegistrationRead:
    """Register a team, placing it on the waitlist when the event is full."""
    return registration_to_read(service.register(event_id, payload.team_id))


@router.post("/{event_id}/cancel", response_model=CancellationRead)
def cancel(event_id: str, payload: CancelRequest, service: ServiceDep) -> CancellationRead:
    """Cancel a registration and promote the first waiting team."""
    result = service.cancel(event_id, payload.team_id)
    return CancellationRead(
        event_id=event_id,
        team_id=result.registration.team_id,
        status=result.registration.status,
        promoted_team_id=result.promoted_team_id,
        promotion=(registration_to_read(result.promoted) if result.promoted is not None else None),
    )


@router.get("/{event_id}/registrations", response_model=RegistrationList)
def list_registrations(event_id: str, service: ServiceDep) -> RegistrationList:
    """Return the registration ledger of an event."""
    registrations = service.registrations(event_id)
    stats = service.stats(event_id)
    return RegistrationList(
        event_id=event_id,
        registrations=[registration_to_read(item) for item in registrations],
        confirmed=stats.confirmed,
        waitlisted=stats.waitlisted,
    )


@router.get("/{event_id}/stats", response_model=EventStatsRead)
def event_stats(event_id: str, service: ServiceDep) -> EventStatsRead:
    """Return registration figures for one event."""
    return stats_to_read(service.stats(event_id))


@router.get("/{event_id}/tasks", response_model=list[TaskRead])
def list_tasks(event_id: str, service: ServiceDep) -> list[TaskRead]:
    """Return the checklist of an event."""
    return [task_to_read(task) for task in service.tasks(event_id)]


@router.post("/{event_id}/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def add_task(event_id: str, payload: TaskCreate, service: ServiceDep) -> TaskRead:
    """Add an item to the event checklist."""
    task = service.add_task(event_id, payload.title, due_at=payload.due_at)
    return task_to_read(task)


@router.post("/{event_id}/tasks/{task_id}/toggle", response_model=TaskRead)
def toggle_task(event_id: str, task_id: str, service: ServiceDep) -> TaskRead:
    """Toggle the completion state of a checklist item."""
    return task_to_read(service.toggle_task(event_id, task_id))
