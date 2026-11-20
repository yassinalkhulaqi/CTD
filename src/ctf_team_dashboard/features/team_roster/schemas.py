"""Pydantic schemas for the team roster HTTP API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ctf_team_dashboard.features.team_roster.models import (
    Availability,
    InvitationStatus,
    RosterRole,
)

_HANDLE_PATTERN = r"^[a-zA-Z0-9][a-zA-Z0-9._-]{1,31}$"
_TIMEZONE_PATTERN = r"^(?:UTC|GMT|[A-Za-z_]+(?:/[A-Za-z_+\-]+){1,2})$"


class RosterApiModel(BaseModel):
    """Base model configured for domain objects and by-name population."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RosterMemberRead(RosterApiModel):
    """A roster member as exposed by the API."""

    id: str
    team_id: str
    handle: str
    display_name: str
    role: RosterRole
    specialty: str
    timezone: str
    availability: Availability
    capacity_hours: float
    joined_at: datetime
    initials: str
    rank: int
    availability_label: str
    accepts_work: bool


class RosterMemberCreate(RosterApiModel):
    """Payload used to add a member to a roster."""

    team_id: str = Field(min_length=1, max_length=64)
    handle: str = Field(min_length=2, max_length=32, pattern=_HANDLE_PATTERN)
    display_name: str = Field(default="", max_length=64)
    role: RosterRole = RosterRole.MEMBER
    specialty: str = Field(default="", max_length=80)
    timezone: str = Field(default="UTC", max_length=64, pattern=_TIMEZONE_PATTERN)
    availability: Availability = Availability.OFFLINE
    capacity_hours: float = Field(default=8.0, ge=0, le=80)


class RosterMemberUpdate(RosterApiModel):
    """Partial update payload for a roster member."""

    handle: str | None = Field(default=None, min_length=2, max_length=32, pattern=_HANDLE_PATTERN)
    display_name: str | None = Field(default=None, max_length=64)
    specialty: str | None = Field(default=None, max_length=80)
    timezone: str | None = Field(default=None, max_length=64, pattern=_TIMEZONE_PATTERN)
    availability: Availability | None = None
    capacity_hours: float | None = Field(default=None, ge=0, le=80)


class RoleChange(RosterApiModel):
    """Payload for the explicit role-change endpoint."""

    role: RosterRole
    actor_id: str | None = None


class AvailabilityUpdate(RosterApiModel):
    """Payload for the availability endpoint."""

    availability: Availability


class InvitationRead(RosterApiModel):
    """An invitation as exposed by the API."""

    id: str
    team_id: str
    email: str
    role: RosterRole
    token: str
    status: InvitationStatus
    created_at: datetime
    expires_at: datetime
    masked_token: str
    effective_status: InvitationStatus


class InvitationCreate(RosterApiModel):
    """Payload used to invite a new team member."""

    team_id: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
    role: RosterRole = RosterRole.MEMBER
    expires_at: datetime | None = None


class InvitationAccept(RosterApiModel):
    """Payload used when accepting an invitation."""

    handle: str = Field(min_length=2, max_length=32, pattern=_HANDLE_PATTERN)
    display_name: str = Field(default="", max_length=64)


class AcceptanceResult(RosterApiModel):
    """The member and invitation produced by accepting an invitation."""

    member: RosterMemberRead
    invitation: InvitationRead


class RosterAssignmentRead(RosterApiModel):
    """A work assignment as exposed by the API."""

    id: str
    member_id: str
    challenge_id: str
    hours: float
    assigned_at: datetime


class RosterAssignmentCreate(RosterApiModel):
    """Payload used to reserve work for a member."""

    member_id: str = Field(min_length=1, max_length=64)
    challenge_id: str = Field(min_length=1, max_length=64)
    hours: float = Field(default=1.0, gt=0, le=24)


class RosterAssignmentUpdate(RosterApiModel):
    """Payload used to change a reservation's size."""

    hours: float = Field(gt=0, le=24)


class RosterStatsRead(RosterApiModel):
    """Aggregated roster metrics grouped by role and availability."""

    team_id: str | None = None
    total_members: int
    total_capacity_hours: float
    assigned_hours: float
    assignment_count: int
    pending_invitations: int
    by_role: dict[str, int]
    by_availability: dict[str, int]
    utilisation: float
    utilisation_percent: float
    remaining_hours: float
    available_count: int
    lead_count: int
