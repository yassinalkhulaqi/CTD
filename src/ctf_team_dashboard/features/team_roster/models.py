"""Domain model for the team roster feature.

The roster domain models members, invitations and challenge assignments. Every
entity is immutable: state transitions return a new record so that callers can
compare snapshots safely and business rules stay pure and testable.
"""

from __future__ import annotations

import re
import secrets
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ctf_team_dashboard.domain.enums import StrEnum
from ctf_team_dashboard.domain.models import ensure_utc, utcnow

DEFAULT_CAPACITY_HOURS = 8.0
DEFAULT_INVITE_TTL_DAYS = 7
MAX_CAPACITY_HOURS = 80.0
TOKEN_PREFIX = "inv_"

_HANDLE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{1,31}$")
_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
_TIMEZONE_PATTERN = re.compile(r"^(?:UTC|GMT|[A-Za-z_]+(?:/[A-Za-z_+\-]+){1,2})$")


class RosterPermission(StrEnum):
    """Capabilities that a roster role may grant to a member."""

    VIEW_ROSTER = "roster:view"
    VIEW_CONTACTS = "roster:contacts"
    WORK_CHALLENGES = "roster:work"
    ASSIGN_WORK = "roster:assign"
    INVITE_MEMBERS = "roster:invite"
    CHANGE_ROLES = "roster:roles"
    MANAGE_ROSTER = "roster:manage"


class RosterRole(StrEnum):
    """The four roles recognised by the roster.

    Ranking grows from observer to lead. A higher rank always inherits every
    capability of the lower ranks, which makes permission checks a simple
    comparison without a brittle chain of conditionals.
    """

    OBSERVER = "observer"
    ANALYST = "analyst"
    MEMBER = "member"
    LEAD = "lead"

    @property
    def rank(self) -> int:
        """Return the 0-based seniority of the role."""
        return list(RosterRole).index(self)

    @property
    def label(self) -> str:
        """Return the human readable role label."""
        return self.value.title()

    @property
    def tone(self) -> str:
        """Return the semantic colour tone used by the UI for this role."""
        return {
            RosterRole.OBSERVER: "neutral",
            RosterRole.ANALYST: "info",
            RosterRole.MEMBER: "accent",
            RosterRole.LEAD: "warning",
        }[self]

    @property
    def permissions(self) -> frozenset[RosterPermission]:
        """Return every capability granted by the role."""
        return ROLE_PERMISSIONS[self]

    def permits(self, permission: RosterPermission) -> bool:
        """Return whether the role grants ``permission``."""
        return permission in self.permissions

    def satisfies(self, required: RosterRole) -> bool:
        """Return whether this role is at least as senior as ``required``."""
        return self.rank >= required.rank


class Availability(StrEnum):
    """The work availability advertised by a roster member."""

    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"

    @property
    def label(self) -> str:
        """Return the human readable availability label."""
        return self.value.title()

    @property
    def tone(self) -> str:
        """Return the semantic colour tone for the availability indicator."""
        return {
            Availability.AVAILABLE: "success",
            Availability.BUSY: "warning",
            Availability.OFFLINE: "neutral",
        }[self]

    @property
    def accepts_work(self) -> bool:
        """Return whether new assignments may be offered to this member."""
        return self is Availability.AVAILABLE

    @property
    def rank(self) -> int:
        """Return a stable ordering used to sort availability groups."""
        return list(Availability).index(self)


class InvitationStatus(StrEnum):
    """Lifecycle states of a team invitation."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"

    @property
    def is_open(self) -> bool:
        """Return whether the invitation can still be acted upon."""
        return self is InvitationStatus.PENDING

    @property
    def is_terminal(self) -> bool:
        """Return whether the invitation can no longer change state."""
        return self is not InvitationStatus.PENDING

    @property
    def label(self) -> str:
        """Return the human readable status label."""
        return self.value.title()

    @property
    def tone(self) -> str:
        """Return the semantic colour tone for the status."""
        return {
            InvitationStatus.PENDING: "warning",
            InvitationStatus.ACCEPTED: "success",
            InvitationStatus.EXPIRED: "neutral",
            InvitationStatus.REVOKED: "danger",
        }[self]


_VIEW_PERMISSIONS = frozenset({RosterPermission.VIEW_ROSTER, RosterPermission.WORK_CHALLENGES})
_ANALYST_PERMISSIONS = _VIEW_PERMISSIONS | frozenset({RosterPermission.VIEW_CONTACTS})
_MEMBER_PERMISSIONS = _ANALYST_PERMISSIONS | frozenset(
    {RosterPermission.ASSIGN_WORK, RosterPermission.INVITE_MEMBERS}
)
_LEAD_PERMISSIONS = _MEMBER_PERMISSIONS | frozenset(
    {RosterPermission.CHANGE_ROLES, RosterPermission.MANAGE_ROSTER}
)

ROLE_PERMISSIONS: dict[RosterRole, frozenset[RosterPermission]] = {
    RosterRole.OBSERVER: _VIEW_PERMISSIONS,
    RosterRole.ANALYST: _ANALYST_PERMISSIONS,
    RosterRole.MEMBER: _MEMBER_PERMISSIONS,
    RosterRole.LEAD: _LEAD_PERMISSIONS,
}


def initials_of(name: str) -> str:
    """Derive up to two uppercase initials from a name or handle."""
    parts = [part for part in name.strip().split() if part]
    if not parts:
        return "??"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def role_rank(role: RosterRole) -> int:
    """Return the seniority rank of a role."""
    return role.rank


def normalise_handle(handle: str) -> str:
    """Normalise a handle to its canonical lowercase representation."""
    return handle.strip().lower()


def normalise_email(email: str) -> str:
    """Normalise an email address for duplicate detection."""
    return email.strip().lower()


def is_valid_handle(handle: str) -> bool:
    """Return whether a handle conforms to the roster naming rules."""
    return _HANDLE_PATTERN.fullmatch(handle) is not None


def is_valid_email(email: str) -> bool:
    """Return whether an email address has a plausible shape."""
    return _EMAIL_PATTERN.fullmatch(email) is not None


def is_valid_timezone(timezone: str) -> bool:
    """Return whether a timezone name resolves to a real IANA zone."""
    if _TIMEZONE_PATTERN.fullmatch(timezone) is None:
        return False
    try:
        ZoneInfo(timezone)
    except (KeyError, ValueError, OSError):
        return False
    return True


def default_expiry(now: datetime | None = None) -> datetime:
    """Return the default expiration moment for a new invitation."""
    current = ensure_utc(now if now is not None else utcnow())
    return current + timedelta(days=DEFAULT_INVITE_TTL_DAYS)


def generate_invite_token() -> str:
    """Return a cryptographically strong, human distinguishable invite token."""
    return f"{TOKEN_PREFIX}{secrets.token_urlsafe(24)}"


def is_expired(expires_at: datetime, now: datetime | None = None) -> bool:
    """Return whether an expiration timestamp has been reached."""
    current = ensure_utc(now if now is not None else utcnow())
    return ensure_utc(expires_at) <= current


def capacity_utilisation(assigned_hours: float, capacity_hours: float) -> float:
    """Return the assigned hours divided by capacity, ignoring negative input."""
    if capacity_hours <= 0:
        return 0.0
    return max(0.0, assigned_hours) / capacity_hours


def bounded_utilisation(assigned_hours: float, capacity_hours: float) -> float:
    """Return a utilisation ratio clamped into the inclusive 0..1 range."""
    return min(1.0, capacity_utilisation(assigned_hours, capacity_hours))


def total_assigned_hours(assignments: Iterable[RosterAssignment]) -> float:
    """Return the sum of positive hours across a set of assignments."""
    return round(
        sum(assignment.hours for assignment in assignments if assignment.is_positive),
        2,
    )


def remaining_capacity(capacity_hours: float, assignments: Iterable[RosterAssignment]) -> float:
    """Return the unreserved capacity left after accounting for assignments."""
    return round(max(0.0, capacity_hours - total_assigned_hours(assignments)), 2)


def hours_label(hours: float) -> str:
    """Format an hour count for display without trailing zeroes."""
    value = round(hours, 1)
    return f"{value:g}h"


@dataclass(frozen=True, slots=True)
class RosterMember:
    """A person who belongs to a team roster."""

    id: str
    team_id: str
    handle: str
    display_name: str
    role: RosterRole = RosterRole.MEMBER
    specialty: str = ""
    timezone: str = "UTC"
    availability: Availability = Availability.OFFLINE
    capacity_hours: float = DEFAULT_CAPACITY_HOURS
    joined_at: datetime = field(default_factory=utcnow)

    @property
    def initials(self) -> str:
        """Return up to two uppercase initials for the avatar."""
        return initials_of(self.label)

    @property
    def label(self) -> str:
        """Return the preferred display name with the handle as fallback."""
        return self.display_name.strip() or self.handle

    @property
    def rank(self) -> int:
        """Return the seniority rank implied by the role."""
        return self.role.rank

    @property
    def accepts_work(self) -> bool:
        """Return whether the member is available and has reserve capacity."""
        return self.availability.accepts_work and self.capacity_hours > 0

    def permits(self, permission: RosterPermission) -> bool:
        """Return whether the member's role grants ``permission``."""
        return self.role.permits(permission)

    def satisfies(self, required: RosterRole) -> bool:
        """Return whether the member is at least as senior as ``required``."""
        return self.role.satisfies(required)

    def assigned_hours(self, assignments: Iterable[RosterAssignment]) -> float:
        """Return hours assigned to this member across the supplied records."""
        return total_assigned_hours(
            assignment for assignment in assignments if assignment.member_id == self.id
        )

    def remaining_hours(self, assignments: Iterable[RosterAssignment]) -> float:
        """Return the capacity left after the supplied assignments."""
        return round(max(0.0, self.capacity_hours - self.assigned_hours(assignments)), 2)

    def utilisation(self, assignments: Iterable[RosterAssignment]) -> float:
        """Return the capacity utilisation ratio for this member."""
        return capacity_utilisation(self.assigned_hours(assignments), self.capacity_hours)

    def with_role(self, role: RosterRole) -> RosterMember:
        """Return a copy of the member holding a different role."""
        return replace(self, role=role)

    def with_availability(self, availability: Availability) -> RosterMember:
        """Return a copy of the member with a different availability."""
        return replace(self, availability=availability)

    def with_details(
        self,
        *,
        handle: str | None = None,
        display_name: str | None = None,
        specialty: str | None = None,
        timezone: str | None = None,
        capacity_hours: float | None = None,
    ) -> RosterMember:
        """Return a copy with selected descriptive fields replaced."""
        updated = self
        if handle is not None:
            updated = replace(updated, handle=handle)
        if display_name is not None:
            updated = replace(updated, display_name=display_name)
        if specialty is not None:
            updated = replace(updated, specialty=specialty)
        if timezone is not None:
            updated = replace(updated, timezone=timezone)
        if capacity_hours is not None:
            updated = replace(updated, capacity_hours=capacity_hours)
        return updated


@dataclass(frozen=True, slots=True)
class Invitation:
    """An invitation offering a role to an email address."""

    id: str
    team_id: str
    email: str
    role: RosterRole
    token: str
    status: InvitationStatus = InvitationStatus.PENDING
    created_at: datetime = field(default_factory=utcnow)
    expires_at: datetime = field(default_factory=default_expiry)

    @property
    def email_local(self) -> str:
        """Return the part of the address before the ``@`` sign."""
        return self.email.split("@", 1)[0]

    @property
    def email_domain(self) -> str:
        """Return the domain part of the address."""
        parts = self.email.split("@", 1)
        return parts[1] if len(parts) == 2 else ""

    @property
    def is_open(self) -> bool:
        """Return whether the invitation is still pending."""
        return self.status.is_open

    @property
    def masked_token(self) -> str:
        """Return a shortened token suitable for display in a list."""
        return f"{self.token[:12]}…"

    def is_expired(self, now: datetime | None = None) -> bool:
        """Return whether the invitation's deadline has passed."""
        return is_expired(self.expires_at, now)

    def effective_status(self, now: datetime | None = None) -> InvitationStatus:
        """Return the status after applying deadline expiry to pending invites."""
        if self.status is InvitationStatus.PENDING and self.is_expired(now):
            return InvitationStatus.EXPIRED
        return self.status

    def can_be_accepted(self, now: datetime | None = None) -> bool:
        """Return whether the invitation may be accepted right now."""
        return self.effective_status(now) is InvitationStatus.PENDING

    def accepted(self, now: datetime | None = None) -> Invitation:
        """Return an accepted copy, validating the current status first."""
        if not self.can_be_accepted(now):
            raise ValueError("Only an unexpired pending invitation can be accepted")
        return replace(self, status=InvitationStatus.ACCEPTED)

    def revoked(self, now: datetime | None = None) -> Invitation:
        """Return a revoked copy, validating the current status first."""
        if self.effective_status(now) is InvitationStatus.EXPIRED:
            raise ValueError("An expired invitation cannot be revoked")
        if self.status.is_terminal:
            raise ValueError("Only a pending invitation can be revoked")
        return replace(self, status=InvitationStatus.REVOKED)

    def expired(self) -> Invitation:
        """Return an expired copy of the invitation."""
        return replace(self, status=InvitationStatus.EXPIRED)


@dataclass(frozen=True, slots=True)
class RosterAssignment:
    """A block of work reserved on a challenge for one member."""

    id: str
    member_id: str
    challenge_id: str
    hours: float = 1.0
    assigned_at: datetime = field(default_factory=utcnow)

    @property
    def is_positive(self) -> bool:
        """Return whether the assignment reserves a positive amount of time."""
        return self.hours > 0

    @property
    def rounded_hours(self) -> float:
        """Return the hour count rounded to two decimals."""
        return round(self.hours, 2)

    def with_hours(self, hours: float) -> RosterAssignment:
        """Return a copy with a different hour reservation."""
        return replace(self, hours=hours)


@dataclass(frozen=True, slots=True)
class RosterStats:
    """Aggregated roster metrics grouped by role and availability."""

    team_id: str | None = None
    total_members: int = 0
    total_capacity_hours: float = 0.0
    assigned_hours: float = 0.0
    assignment_count: int = 0
    pending_invitations: int = 0
    by_role: dict[RosterRole, int] = field(default_factory=dict)
    by_availability: dict[Availability, int] = field(default_factory=dict)

    @property
    def available_count(self) -> int:
        """Return the number of members advertising availability."""
        return self.by_availability.get(Availability.AVAILABLE, 0)

    @property
    def lead_count(self) -> int:
        """Return the number of team leads."""
        return self.by_role.get(RosterRole.LEAD, 0)

    @property
    def remaining_hours(self) -> float:
        """Return the reserved capacity still available to the team."""
        return round(max(0.0, self.total_capacity_hours - self.assigned_hours), 2)

    @property
    def utilisation(self) -> float:
        """Return the ratio of assigned hours to total capacity."""
        return capacity_utilisation(self.assigned_hours, self.total_capacity_hours)

    @property
    def utilisation_percent(self) -> float:
        """Return the utilisation ratio expressed as a percentage."""
        return round(bounded_utilisation(self.assigned_hours, self.total_capacity_hours) * 100, 1)

    def count_for(self, role: RosterRole) -> int:
        """Return the number of members holding a role."""
        return self.by_role.get(role, 0)

    def availability_count(self, availability: Availability) -> int:
        """Return the number of members with an availability state."""
        return self.by_availability.get(availability, 0)

    def role_share(self, role: RosterRole) -> float:
        """Return the fraction of members holding a role."""
        if self.total_members <= 0:
            return 0.0
        return self.count_for(role) / self.total_members


def build_roster_stats(
    members: Iterable[RosterMember],
    invitations: Iterable[Invitation],
    assignments: Iterable[RosterAssignment],
    *,
    team_id: str | None = None,
    now: datetime | None = None,
) -> RosterStats:
    """Aggregate roster records into the statistics used by the API and UI."""
    member_list = list(members)
    assignment_list = list(assignments)
    assigned = total_assigned_hours(assignment_list)
    capacity = round(sum(member.capacity_hours for member in member_list), 2)
    by_role: dict[RosterRole, int] = dict.fromkeys(RosterRole, 0)
    by_availability: dict[Availability, int] = dict.fromkeys(Availability, 0)
    for member in member_list:
        by_role[member.role] += 1
        by_availability[member.availability] += 1
    pending = sum(
        1 for invite in invitations if invite.effective_status(now) is InvitationStatus.PENDING
    )
    return RosterStats(
        team_id=team_id,
        total_members=len(member_list),
        total_capacity_hours=capacity,
        assigned_hours=assigned,
        assignment_count=len(assignment_list),
        pending_invitations=pending,
        by_role=by_role,
        by_availability=by_availability,
    )
