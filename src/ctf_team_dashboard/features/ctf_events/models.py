"""Domain model of the CTF event lifecycle.

Events have two kinds of state.  ``draft`` and ``archived`` are explicit states
chosen by an organiser and stored verbatim.  ``upcoming`` and ``live`` are
*derived* from the competition window, so a scheduled event becomes live the
moment its start time passes without anybody having to run a cron job.  The
pure helpers in this module are the single source of truth for that derivation
and are shared by the store, the service and the API layer.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import datetime

from ctf_team_dashboard.domain.enums import StrEnum
from ctf_team_dashboard.domain.models import ensure_utc, utcnow

MAX_NAME_LENGTH = 120
MAX_DESCRIPTION_LENGTH = 4_000
MIN_NAME_LENGTH = 3
MIN_TEAM_SIZE = 1
MAX_TEAM_SIZE = 64
MAX_SLUG_LENGTH = 80
MAX_TAGS = 12


class EventFormat(StrEnum):
    """The scoring format used by an event."""

    JEOPARDY = "jeopardy"
    ATTACK_DEFENCE = "attack_defence"

    @property
    def label(self) -> str:
        """Return the human readable name of the format."""
        if self is EventFormat.JEOPARDY:
            return "Jeopardy"
        return "Attack / Defence"


class EventStatus(StrEnum):
    """Lifecycle state of an event.

    Only ``DRAFT`` and ``ARCHIVED`` may be persisted explicitly; ``UPCOMING``
    and ``LIVE`` are recomputed from the event window on every read.
    """

    DRAFT = "draft"
    UPCOMING = "upcoming"
    LIVE = "live"
    ARCHIVED = "archived"

    @property
    def is_explicit(self) -> bool:
        """Return whether an organiser may set this status directly."""
        return self in (EventStatus.DRAFT, EventStatus.ARCHIVED)

    @property
    def is_open(self) -> bool:
        """Return whether the event can accept registrations."""
        return self in (EventStatus.UPCOMING, EventStatus.LIVE)

    @property
    def tone(self) -> str:
        """Return the semantic colour token used by the interface."""
        return {
            EventStatus.DRAFT: "neutral",
            EventStatus.UPCOMING: "info",
            EventStatus.LIVE: "success",
            EventStatus.ARCHIVED: "warning",
        }[self]

    @property
    def label(self) -> str:
        """Return a capitalised display label."""
        return self.value.capitalize()


class RegistrationStatus(StrEnum):
    """State of a team's registration for an event."""

    CONFIRMED = "confirmed"
    WAITLISTED = "waitlisted"
    CANCELLED = "cancelled"

    @property
    def is_active(self) -> bool:
        """Return whether the registration still occupies a place."""
        return self in (RegistrationStatus.CONFIRMED, RegistrationStatus.WAITLISTED)

    @property
    def tone(self) -> str:
        """Return the semantic colour token used by the interface."""
        return {
            RegistrationStatus.CONFIRMED: "success",
            RegistrationStatus.WAITLISTED: "warning",
            RegistrationStatus.CANCELLED: "neutral",
        }[self]


def slugify(value: str, *, maximum: int = MAX_SLUG_LENGTH) -> str:
    """Convert a human name into a lowercase, hyphenated URL slug.

    Accented characters are transliterated to ASCII and every run of
    non-alphanumeric characters collapses to a single hyphen.  An empty result
    falls back to ``event`` so a slug is always usable in a route.

    Args:
        value: The raw name supplied by an organiser.
        maximum: Optional maximum length of the generated slug.

    Returns:
        The normalised slug.
    """
    transliterated = unicodedata.normalize("NFKD", value)
    ascii_text = transliterated.encode("ascii", "ignore").decode("ascii")
    collapsed = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    slug = collapsed[:maximum].rstrip("-")
    return slug or "event"


def normalise_tags(tags: Iterable[str], *, maximum: int = MAX_TAGS) -> tuple[str, ...]:
    """Trim, lower-case and de-duplicate a collection of tags."""
    cleaned: list[str] = []
    for tag in tags:
        value = tag.strip().lower()
        if value and value not in cleaned:
            cleaned.append(value)
        if len(cleaned) >= maximum:
            break
    return tuple(cleaned)


def derive_event_status(
    stored: EventStatus,
    starts_at: datetime,
    ends_at: datetime,
    now: datetime | None = None,
) -> EventStatus:
    """Resolve the effective status of an event at a point in time.

    Draft and archived events keep their stored status.  Every other event is
    upcoming before its window, live inside its window and archived once the
    window has closed.

    Args:
        stored: The status recorded on the event row.
        starts_at: The start of the competition window.
        ends_at: The end of the competition window.
        now: Optional instant used for the calculation; defaults to UTC now.

    Returns:
        The effective status.
    """
    if stored in (EventStatus.DRAFT, EventStatus.ARCHIVED):
        return stored
    moment = ensure_utc(now if now is not None else utcnow())
    start = ensure_utc(starts_at)
    end = ensure_utc(ends_at)
    if moment < start:
        return EventStatus.UPCOMING
    if moment < end:
        return EventStatus.LIVE
    return EventStatus.ARCHIVED


def intervals_overlap(
    first_start: datetime,
    first_end: datetime,
    second_start: datetime,
    second_end: datetime,
) -> bool:
    """Return whether two half-open time intervals intersect.

    Touching endpoints do not count as an overlap: an event that finishes at
    12:00 and one that starts at 12:00 can share a team safely.
    """
    return ensure_utc(first_start) < ensure_utc(second_end) and ensure_utc(
        second_start
    ) < ensure_utc(first_end)


def overlap_seconds(
    first_start: datetime,
    first_end: datetime,
    second_start: datetime,
    second_end: datetime,
) -> float:
    """Return the number of overlapping seconds between two intervals."""
    if not intervals_overlap(first_start, first_end, second_start, second_end):
        return 0.0
    start = max(ensure_utc(first_start), ensure_utc(second_start))
    end = min(ensure_utc(first_end), ensure_utc(second_end))
    return max(0.0, (end - start).total_seconds())


def format_countdown(seconds: int) -> str:
    """Render a countdown as a compact, human readable string.

    Days are shown when the remaining time exceeds a day, otherwise hours and
    minutes are used.  Negative values are clamped to zero.

    Args:
        seconds: Number of seconds remaining.

    Returns:
        A string such as ``02d 04h``, ``05h 32m`` or ``12m 09s``.
    """
    total = max(0, int(seconds))
    days, remainder = divmod(total, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes, secs = divmod(remainder, 60)
    if days:
        return f"{days:02d}d {hours:02d}h"
    if hours:
        return f"{hours:02d}h {minutes:02d}m"
    return f"{minutes:02d}m {secs:02d}s"


@dataclass(frozen=True, slots=True)
class CtfEvent:
    """A CTF competition that a team can register for."""

    id: str
    name: str
    slug: str
    description: str
    format: EventFormat
    starts_at: datetime
    ends_at: datetime
    status: EventStatus = EventStatus.DRAFT
    max_team_size: int = 8
    registration_open: bool = True
    website_url: str = ""
    tags: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=utcnow)

    def status_at(self, now: datetime | None = None) -> EventStatus:
        """Return the effective status at ``now``."""
        return derive_event_status(self.status, self.starts_at, self.ends_at, now)

    @property
    def derived_status(self) -> EventStatus:
        """Return the effective status at the current instant."""
        return self.status_at()

    @property
    def is_live(self) -> bool:
        """Return whether the event is currently running."""
        return self.derived_status is EventStatus.LIVE

    @property
    def is_upcoming(self) -> bool:
        """Return whether the event has not started yet."""
        return self.derived_status is EventStatus.UPCOMING

    @property
    def is_archived(self) -> bool:
        """Return whether the event window has closed or was archived."""
        return self.derived_status is EventStatus.ARCHIVED

    @property
    def duration_seconds(self) -> int:
        """Return the length of the competition window in seconds."""
        return max(
            0,
            int((ensure_utc(self.ends_at) - ensure_utc(self.starts_at)).total_seconds()),
        )

    def seconds_until_start(self, now: datetime | None = None) -> int:
        """Return the number of seconds before the window opens."""
        moment = ensure_utc(now if now is not None else utcnow())
        return max(0, int((ensure_utc(self.starts_at) - moment).total_seconds()))

    def seconds_remaining(self, now: datetime | None = None) -> int:
        """Return the number of seconds before the window closes."""
        moment = ensure_utc(now if now is not None else utcnow())
        return max(0, int((ensure_utc(self.ends_at) - moment).total_seconds()))

    def countdown_seconds(self, now: datetime | None = None) -> int:
        """Return the seconds relevant to the current lifecycle phase.

        Upcoming events count down to their start, live events to their end,
        and draft or archived events report zero.
        """
        status = self.status_at(now)
        if status is EventStatus.UPCOMING:
            return self.seconds_until_start(now)
        if status is EventStatus.LIVE:
            return self.seconds_remaining(now)
        return 0

    def countdown_label(self, now: datetime | None = None) -> str:
        """Return the formatted countdown for the current lifecycle phase."""
        return format_countdown(self.countdown_seconds(now))

    def progress(self, now: datetime | None = None) -> float:
        """Return the fraction of the competition window already elapsed."""
        total = self.duration_seconds
        if total <= 0:
            return 0.0
        elapsed = total - self.seconds_remaining(now)
        return min(1.0, max(0.0, elapsed / total))

    def accepts_registrations(self, now: datetime | None = None) -> bool:
        """Return whether the event is open for registrations at ``now``."""
        return self.registration_open and self.status_at(now).is_open

    def overlaps_with(self, other: CtfEvent) -> bool:
        """Return whether two live events share any competition time."""
        return intervals_overlap(self.starts_at, self.ends_at, other.starts_at, other.ends_at)

    def with_status(self, status: EventStatus) -> CtfEvent:
        """Return a copy of the event with a different stored status."""
        return replace(self, status=status)

    def with_slug(self, slug: str) -> CtfEvent:
        """Return a copy of the event with a different slug."""
        return replace(self, slug=slug)


@dataclass(frozen=True, slots=True)
class EventRegistration:
    """A team's entry in an event's registration ledger."""

    id: str
    event_id: str
    team_id: str
    status: RegistrationStatus = RegistrationStatus.CONFIRMED
    registered_at: datetime = field(default_factory=utcnow)

    @property
    def is_confirmed(self) -> bool:
        """Return whether the team holds a confirmed slot."""
        return self.status is RegistrationStatus.CONFIRMED

    @property
    def is_waitlisted(self) -> bool:
        """Return whether the team waits for a slot to open."""
        return self.status is RegistrationStatus.WAITLISTED

    @property
    def is_cancelled(self) -> bool:
        """Return whether the registration was cancelled."""
        return self.status is RegistrationStatus.CANCELLED

    def with_status(self, status: RegistrationStatus) -> EventRegistration:
        """Return a copy with a different registration status."""
        return replace(self, status=status)


@dataclass(frozen=True, slots=True)
class EventTask:
    """A checklist item attached to an event."""

    id: str
    event_id: str
    title: str
    done: bool = False
    due_at: datetime | None = None

    def is_overdue(self, now: datetime | None = None) -> bool:
        """Return whether an incomplete task is past its due date."""
        if self.done or self.due_at is None:
            return False
        moment = ensure_utc(now if now is not None else utcnow())
        return moment >= ensure_utc(self.due_at)

    def toggle(self) -> EventTask:
        """Return a copy with the completion flag inverted."""
        return replace(self, done=not self.done)

    def with_title(self, title: str) -> EventTask:
        """Return a copy with a different title."""
        return replace(self, title=title)


@dataclass(frozen=True, slots=True)
class EventStats:
    """Aggregated registration figures for a single event."""

    event_id: str
    capacity: int
    confirmed: int
    waitlisted: int
    cancelled: int
    promotions: int = 0

    @property
    def total(self) -> int:
        """Return the total number of registrations ever recorded."""
        return self.confirmed + self.waitlisted + self.cancelled

    @property
    def available_slots(self) -> int:
        """Return the number of free confirmed slots."""
        return max(0, self.capacity - self.confirmed)

    @property
    def is_full(self) -> bool:
        """Return whether every confirmed slot is occupied."""
        return self.available_slots == 0

    @property
    def capacity_ratio(self) -> float:
        """Return confirmed registrations divided by capacity.

        Events created without a finite capacity report zero so that callers
        never have to special-case division by zero.
        """
        if self.capacity <= 0:
            return 0.0
        return self.confirmed / self.capacity

    @property
    def fill_percentage(self) -> int:
        """Return the capacity ratio as a percentage clamped to 100."""
        return min(100, round(self.capacity_ratio * 100))

    @property
    def waitlist_pressure(self) -> float:
        """Return waitlisted teams relative to the confirmed capacity."""
        if self.capacity <= 0:
            return 0.0
        return self.waitlisted / self.capacity


@dataclass(frozen=True, slots=True)
class EventOverlap:
    """A scheduling conflict between two live events sharing a team."""

    team_id: str
    first: CtfEvent
    second: CtfEvent

    @property
    def seconds(self) -> float:
        """Return the length of the conflicting window."""
        return overlap_seconds(
            self.first.starts_at,
            self.first.ends_at,
            self.second.starts_at,
            self.second.ends_at,
        )
