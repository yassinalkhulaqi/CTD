"""Business rules for event authoring, registration and scheduling.

The service layer owns every invariant of the feature: names must be usable,
windows must end after they start, only open events accept teams, a full event
moves new teams to a waitlist, and a cancelled confirmed slot is immediately
offered to the longest-waiting team.  Stores remain deliberately dumb so these
rules can be unit tested without an HTTP server.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
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
    normalise_tags,
    slugify,
)
from ctf_team_dashboard.features.ctf_events.store import (
    EventStore,
    RegistrationStore,
    TaskStore,
)
from ctf_team_dashboard.repositories.teams import TeamRepository

MAX_SLUG_SUFFIX = 500
MAX_TASK_TITLE_LENGTH = 160


@dataclass(frozen=True, slots=True)
class EventFilters:
    """Optional filters accepted by the event catalogue."""

    status: EventStatus | None = None
    format: EventFormat | None = None
    tag: str | None = None
    search: str | None = None
    registration_open: bool | None = None
    window: str = "all"
    limit: int = 100


@dataclass(frozen=True, slots=True)
class CancellationResult:
    """Outcome of cancelling a registration, including any promotion."""

    registration: EventRegistration
    promoted: EventRegistration | None = None

    @property
    def promoted_team_id(self) -> str | None:
        """Return the team that was promoted, when one was."""
        return self.promoted.team_id if self.promoted is not None else None


class EventService:
    """Coordinate events, registrations and checklists with domain rules."""

    def __init__(
        self,
        events: EventStore | None = None,
        registrations: RegistrationStore | None = None,
        tasks: TaskStore | None = None,
        teams: TeamRepository | None = None,
    ) -> None:
        self._events = events or EventStore()
        self._registrations = registrations or RegistrationStore()
        self._tasks = tasks or TaskStore()
        self._teams = teams or TeamRepository()

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    @staticmethod
    def validate_name(name: str) -> str:
        """Trim and validate an event name."""
        cleaned = " ".join(name.split())
        if len(cleaned) < MIN_NAME_LENGTH:
            raise ValidationError(
                f"An event name must contain at least {MIN_NAME_LENGTH} characters"
            )
        if len(cleaned) > MAX_NAME_LENGTH:
            raise ValidationError(f"An event name must not exceed {MAX_NAME_LENGTH} characters")
        return cleaned

    @staticmethod
    def validate_window(starts_at: datetime, ends_at: datetime) -> None:
        """Ensure the event window has a positive duration."""
        if ends_at <= starts_at:
            raise ValidationError("An event must end after it starts")

    @staticmethod
    def validate_status(status: EventStatus) -> EventStatus:
        """Reject statuses that must be derived from timestamps."""
        if status is EventStatus.LIVE:
            raise ValidationError(
                "The live status is derived from the event window and cannot be set"
            )
        return status

    @staticmethod
    def validate_capacity(capacity: int) -> int:
        """Validate the maximum number of confirmed teams."""
        if capacity < MIN_TEAM_SIZE or capacity > MAX_TEAM_SIZE:
            raise ValidationError(
                f"Team capacity must be between {MIN_TEAM_SIZE} and {MAX_TEAM_SIZE}"
            )
        return capacity

    @staticmethod
    def validate_website(url: str) -> str:
        """Validate the optional event website."""
        cleaned = url.strip()
        if cleaned and not cleaned.startswith(("https://", "http://")):
            raise ValidationError("The event website must start with http:// or https://")
        return cleaned

    @staticmethod
    def validate_description(description: str) -> str:
        """Validate the length of the event description."""
        cleaned = description.strip()
        if len(cleaned) > MAX_DESCRIPTION_LENGTH:
            raise ValidationError(
                f"The description must not exceed {MAX_DESCRIPTION_LENGTH} characters"
            )
        return cleaned

    @staticmethod
    def validate_task_title(title: str) -> str:
        """Validate the title of a checklist item."""
        cleaned = " ".join(title.split())
        if not cleaned:
            raise ValidationError("A task title must not be empty")
        if len(cleaned) > MAX_TASK_TITLE_LENGTH:
            raise ValidationError(
                f"A task title must not exceed {MAX_TASK_TITLE_LENGTH} characters"
            )
        return cleaned

    def unique_slug(self, name: str, *, exclude_id: str | None = None) -> str:
        """Generate a slug that does not collide with an existing event."""
        base = slugify(name)
        taken = self._events.all_slugs()
        if exclude_id is not None:
            current = self._events.get(exclude_id)
            if current is not None:
                taken.discard(current.slug)
        if base not in taken:
            return base
        for index in range(2, MAX_SLUG_SUFFIX + 1):
            candidate = f"{base[: MAX_SLUG_SUFFIX // 2]}-{index}"
            if candidate not in taken:
                return candidate
        raise ConflictError("Unable to allocate a unique event slug")

    # ------------------------------------------------------------------
    # Event lifecycle
    # ------------------------------------------------------------------
    def get_event(self, event_id: str) -> CtfEvent:
        """Return an event or raise :class:`NotFoundError`."""
        event = self._events.get(event_id)
        if event is None:
            raise NotFoundError(f"Event {event_id!r} does not exist")
        return event

    def get_event_by_slug(self, slug: str) -> CtfEvent:
        """Return an event by slug or raise :class:`NotFoundError`."""
        event = self._events.get_by_slug(slug)
        if event is None:
            raise NotFoundError(f"Event with slug {slug!r} does not exist")
        return event

    def list_events(self, filters: EventFilters | None = None) -> list[CtfEvent]:
        """Return events matching the provided filters."""
        options = filters or EventFilters()
        return self._events.list_events(
            status=options.status,
            event_format=options.format,
            tag=options.tag,
            search=options.search,
            registration_open=options.registration_open,
            window=options.window,
            now=utcnow(),
            limit=options.limit,
        )

    def upcoming_events(self, *, limit: int = 20) -> list[CtfEvent]:
        """Return upcoming events ordered by their start time."""
        return self._events.list_events(window="upcoming", limit=limit)

    def live_events(self, *, limit: int = 20) -> list[CtfEvent]:
        """Return the events currently in progress."""
        return self._events.list_events(window="live", limit=limit)

    def create_event(
        self,
        name: str,
        starts_at: datetime,
        ends_at: datetime,
        *,
        description: str = "",
        event_format: EventFormat = EventFormat.JEOPARDY,
        status: EventStatus = EventStatus.UPCOMING,
        max_team_size: int = 8,
        registration_open: bool = True,
        website_url: str = "",
        tags: tuple[str, ...] | list[str] = (),
        slug: str | None = None,
    ) -> CtfEvent:
        """Validate and persist a new event."""
        cleaned_name = self.validate_name(name)
        self.validate_window(starts_at, ends_at)
        tags_tuple = normalise_tags(tags)
        if len(tags_tuple) > MAX_TAGS:
            raise ValidationError(f"An event may have at most {MAX_TAGS} tags")
        event = CtfEvent(
            id=f"event-{uuid.uuid4().hex[:12]}",
            name=cleaned_name,
            slug=self.unique_slug(slug) if slug else self.unique_slug(cleaned_name),
            description=self.validate_description(description),
            format=event_format,
            starts_at=starts_at,
            ends_at=ends_at,
            status=self.validate_status(status),
            max_team_size=self.validate_capacity(max_team_size),
            registration_open=registration_open,
            website_url=self.validate_website(website_url),
            tags=tags_tuple,
            created_at=utcnow(),
        )
        return self._events.create(event)

    def update_event(
        self,
        event_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        event_format: EventFormat | None = None,
        status: EventStatus | None = None,
        max_team_size: int | None = None,
        registration_open: bool | None = None,
        website_url: str | None = None,
        tags: tuple[str, ...] | list[str] | None = None,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
        slug: str | None = None,
    ) -> CtfEvent:
        """Validate and apply a partial update to an event.

        Changing the name regenerates the slug unless an explicit slug is
        supplied.  Moving an event to ``archived`` is allowed; moving it to
        ``live`` is not, because that state belongs to the clock.
        """
        event = self.get_event(event_id)
        new_name = self.validate_name(name) if name is not None else event.name
        new_starts = starts_at if starts_at is not None else event.starts_at
        new_ends = ends_at if ends_at is not None else event.ends_at
        self.validate_window(new_starts, new_ends)

        new_slug = event.slug
        if slug is not None:
            candidate = slugify(slug)
            if candidate != event.slug:
                new_slug = self.unique_slug(candidate, exclude_id=event_id)
        elif new_name != event.name:
            new_slug = self.unique_slug(new_name, exclude_id=event_id)

        updated = CtfEvent(
            id=event.id,
            name=new_name,
            slug=new_slug,
            description=(
                self.validate_description(description)
                if description is not None
                else event.description
            ),
            format=event_format if event_format is not None else event.format,
            starts_at=new_starts,
            ends_at=new_ends,
            status=(self.validate_status(status) if status is not None else event.status),
            max_team_size=(
                self.validate_capacity(max_team_size)
                if max_team_size is not None
                else event.max_team_size
            ),
            registration_open=(
                registration_open if registration_open is not None else event.registration_open
            ),
            website_url=(
                self.validate_website(website_url) if website_url is not None else event.website_url
            ),
            tags=normalise_tags(tags) if tags is not None else event.tags,
            created_at=event.created_at,
        )
        return self._events.update(updated)

    def archive_event(self, event_id: str) -> CtfEvent:
        """Explicitly archive an event regardless of its window."""
        return self.update_event(event_id, status=EventStatus.ARCHIVED)

    def delete_event(self, event_id: str) -> None:
        """Delete an event together with its registrations and checklist."""
        self.get_event(event_id)
        self._registrations.delete_for_event(event_id)
        self._tasks.delete_for_event(event_id)
        self._events.delete(event_id)

    # ------------------------------------------------------------------
    # Registration and scheduling
    # ------------------------------------------------------------------
    def _overlapping_live_event(
        self, event: CtfEvent, team_id: str, now: datetime
    ) -> CtfEvent | None:
        """Return a confirmed, overlapping live event for a team."""
        confirmed = self._registrations.list_for_team(
            team_id, statuses=(RegistrationStatus.CONFIRMED,)
        )
        for registration in confirmed:
            if registration.event_id == event.id:
                continue
            other = self._events.get(registration.event_id)
            if other is None or not other.overlaps_with(event):
                continue
            if EventStatus.LIVE in (other.status_at(now), event.status_at(now)):
                return other
        return None

    def register(self, event_id: str, team_id: str) -> EventRegistration:
        """Register a team, assigning a waitlist place when the event is full.

        Args:
            event_id: The event to join.
            team_id: The team joining the event.

        Returns:
            The newly created registration.

        Raises:
            NotFoundError: When the event or team does not exist.
            ConflictError: When registration is closed, duplicated or clashes
                with another live event the team is playing.
        """
        event = self.get_event(event_id)
        now = utcnow()
        if self._teams.get(team_id) is None:
            raise NotFoundError(f"Team {team_id!r} does not exist")
        if not event.accepts_registrations(now):
            raise ConflictError(f"Registration for event {event_id!r} is closed")
        if self._registrations.get_for_event_team(event_id, team_id) is not None:
            raise ConflictError("This team is already registered for the event")
        overlapping = self._overlapping_live_event(event, team_id, now)
        if overlapping is not None:
            raise ConflictError(
                f"Team {team_id!r} is already playing the overlapping live event "
                f"{overlapping.name!r}"
            )
        return self._registrations.reserve_slot(
            event_id=event_id,
            team_id=team_id,
            capacity=event.max_team_size,
            registration_id=f"reg-{uuid.uuid4().hex[:12]}",
            registered_at=now,
        )

    def cancel(self, event_id: str, team_id: str) -> CancellationResult:
        """Cancel a registration and promote the first waiting team.

        Promotion only happens when the cancelled registration held a confirmed
        slot; cancelling a waitlist place leaves the confirmed ledger intact.
        """
        self.get_event(event_id)
        registration = self._registrations.get_for_event_team(event_id, team_id)
        if registration is None:
            raise NotFoundError(
                f"Team {team_id!r} has no active registration for event {event_id!r}"
            )
        if registration.is_cancelled:
            raise ConflictError("The registration is already cancelled")

        cancelled = self._registrations.update(
            registration.with_status(RegistrationStatus.CANCELLED)
        )
        promoted: EventRegistration | None = None
        if registration.is_confirmed:
            promoted = self._registrations.promote_next(event_id)
        return CancellationResult(registration=cancelled, promoted=promoted)

    def registrations(self, event_id: str) -> list[EventRegistration]:
        """Return the registration ledger of an event."""
        self.get_event(event_id)
        return self._registrations.list_for_event(event_id)

    def stats(self, event_id: str) -> EventStats:
        """Aggregate registration figures for an event."""
        event = self.get_event(event_id)
        store = self._registrations
        return EventStats(
            event_id=event.id,
            capacity=event.max_team_size,
            confirmed=store.count_status(event.id, RegistrationStatus.CONFIRMED),
            waitlisted=store.count_status(event.id, RegistrationStatus.WAITLISTED),
            cancelled=store.count_status(event.id, RegistrationStatus.CANCELLED),
            promotions=store.count_promotions(event.id),
        )

    def find_overlaps(self, team_id: str) -> list[EventOverlap]:
        """Return all pairs of live events that clash for a team."""
        now = utcnow()
        live_events: list[CtfEvent] = []
        for registration in self._registrations.list_for_team(
            team_id, statuses=(RegistrationStatus.CONFIRMED,)
        ):
            event = self._events.get(registration.event_id)
            if event is not None and event.status_at(now) is EventStatus.LIVE:
                live_events.append(event)
        live_events.sort(key=lambda item: (item.starts_at, item.id))
        overlaps: list[EventOverlap] = []
        for index, first in enumerate(live_events):
            for second in live_events[index + 1 :]:
                if first.overlaps_with(second):
                    overlaps.append(EventOverlap(team_id, first, second))
        return overlaps

    # ------------------------------------------------------------------
    # Checklist
    # ------------------------------------------------------------------
    def tasks(self, event_id: str) -> list[EventTask]:
        """Return the checklist of an event."""
        self.get_event(event_id)
        return self._tasks.list_for_event(event_id)

    def add_task(self, event_id: str, title: str, *, due_at: datetime | None = None) -> EventTask:
        """Add a checklist item to an event."""
        self.get_event(event_id)
        task = EventTask(
            id=f"task-{uuid.uuid4().hex[:12]}",
            event_id=event_id,
            title=self.validate_task_title(title),
            done=False,
            due_at=due_at,
        )
        return self._tasks.create(task)

    def toggle_task(self, event_id: str, task_id: str) -> EventTask:
        """Toggle a checklist item, checking that it belongs to the event."""
        self.get_event(event_id)
        task = self._tasks.get(task_id)
        if task is None or task.event_id != event_id:
            raise NotFoundError(f"Task {task_id!r} does not belong to event {event_id!r}")
        updated = self._tasks.toggle(task_id)
        if updated is None:
            raise NotFoundError(f"Task {task_id!r} does not exist")
        return updated

    def task_progress(self, event_id: str) -> tuple[int, int]:
        """Return the number of completed and total checklist items."""
        self.get_event(event_id)
        all_tasks = self._tasks.list_for_event(event_id)
        return (sum(1 for task in all_tasks if task.done), len(all_tasks))

    def delete_task(self, event_id: str, task_id: str) -> None:
        """Remove a checklist item from an event."""
        task = self._tasks.get(task_id)
        if task is None or task.event_id != event_id:
            raise NotFoundError(f"Task {task_id!r} does not belong to event {event_id!r}")
        self._tasks.delete(task_id)
