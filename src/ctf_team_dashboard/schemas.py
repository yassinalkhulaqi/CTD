"""Pydantic request/response schemas for the public API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ctf_team_dashboard.domain.enums import (
    ChallengeCategory,
    ChallengeStatus,
    Difficulty,
    MemberRole,
    Presence,
)


class ApiModel(BaseModel):
    """Base model with the shared serialisation configuration."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ErrorDetail(ApiModel):
    """Error payload embedded in every failure response."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(ApiModel):
    """Envelope used for all non-2xx responses."""

    error: ErrorDetail


# ----------------------------------------------------------------------
# Teams
# ----------------------------------------------------------------------
class TeamRead(ApiModel):
    """A team as returned by the API."""

    id: str
    name: str
    slug: str
    color: str
    description: str
    created_at: datetime
    initials: str


class TeamCreate(ApiModel):
    """Payload used to create a team."""

    name: str = Field(min_length=1, max_length=64)
    slug: str | None = Field(default=None, max_length=64)
    color: str = Field(default="#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")
    description: str = Field(default="", max_length=280)


class TeamUpdate(ApiModel):
    """Payload used to update a team."""

    name: str | None = Field(default=None, min_length=1, max_length=64)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    description: str | None = Field(default=None, max_length=280)


class TeamScoreRead(ApiModel):
    """A single scoreboard row."""

    team_id: str
    team_name: str
    solves: int
    points: int
    challenges: int
    members: int
    completion_rate: float


# ----------------------------------------------------------------------
# Members
# ----------------------------------------------------------------------
class MemberRead(ApiModel):
    """A team member as returned by the API."""

    id: str
    team_id: str
    handle: str
    display_name: str
    role: MemberRole
    presence: Presence
    joined_at: datetime
    is_online: bool


class MemberCreate(ApiModel):
    """Payload used to create a member."""

    team_id: str
    handle: str = Field(min_length=2, max_length=32)
    display_name: str = Field(default="", max_length=64)
    role: MemberRole = MemberRole.ANALYST


class MemberUpdate(ApiModel):
    """Payload used to update a member."""

    handle: str | None = Field(default=None, min_length=2, max_length=32)
    display_name: str | None = Field(default=None, max_length=64)
    role: MemberRole | None = None


class PresenceUpdate(ApiModel):
    """Payload used to change the presence of a member."""

    presence: Presence


class MemberContributionRead(ApiModel):
    """Contribution statistics for one member."""

    member_id: str
    handle: str
    display_name: str
    team_id: str
    solves: int
    points: int
    average_points: float
    first_solve_at: datetime | None = None
    last_solve_at: datetime | None = None


# ----------------------------------------------------------------------
# Challenges
# ----------------------------------------------------------------------
class ChallengeRead(ApiModel):
    """A challenge as returned by the API."""

    id: str
    team_id: str
    title: str
    category: ChallengeCategory
    difficulty: Difficulty
    points: int
    description: str
    status: ChallengeStatus
    tags: list[str]
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    created_at: datetime
    seconds_remaining: float


class ChallengeCreate(ApiModel):
    """Payload used to create a challenge."""

    team_id: str
    title: str = Field(min_length=1, max_length=120)
    category: ChallengeCategory
    difficulty: Difficulty
    points: int = Field(default=100, ge=0, le=10_000)
    description: str = Field(default="", max_length=2_000)
    status: ChallengeStatus = ChallengeStatus.PENDING
    tags: list[str] = Field(default_factory=list, max_length=12)
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @field_validator("tags")
    @classmethod
    def _normalise_tags(cls, value: list[str]) -> list[str]:
        """Lower-case and de-duplicate the tag list."""
        seen: list[str] = []
        for tag in value:
            cleaned = tag.strip().lower()
            if cleaned and cleaned not in seen:
                seen.append(cleaned)
        return seen


class ChallengeUpdate(ApiModel):
    """Payload used to update a challenge."""

    title: str | None = Field(default=None, min_length=1, max_length=120)
    category: ChallengeCategory | None = None
    difficulty: Difficulty | None = None
    points: int | None = Field(default=None, ge=0, le=10_000)
    description: str | None = Field(default=None, max_length=2_000)
    status: ChallengeStatus | None = None
    tags: list[str] | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class ChallengeStatusUpdate(ApiModel):
    """Payload used to move a challenge between lifecycle states."""

    status: ChallengeStatus


# ----------------------------------------------------------------------
# Solves
# ----------------------------------------------------------------------
class SolveRead(ApiModel):
    """A flag solve as returned by the API."""

    id: str
    challenge_id: str
    member_id: str
    flag: str
    points_awarded: int
    solved_at: datetime


class SolveCreate(ApiModel):
    """Payload used to record a solve."""

    challenge_id: str
    member_id: str
    flag: str = Field(default="", max_length=256)
    points_awarded: int | None = Field(default=None, ge=0, le=10_000)


# ----------------------------------------------------------------------
# Statistics
# ----------------------------------------------------------------------
class OverviewStats(ApiModel):
    """Headline counters rendered on the dashboard."""

    teams: int
    members: int
    challenges: int
    solves: int
    solved_challenges: int
    completion_rate: float
    total_points: int
    active_members: int


class CategoryStats(ApiModel):
    """Solve statistics for one challenge category."""

    category: ChallengeCategory
    label: str
    accent: str
    challenges: int
    solves: int
    solve_rate: float
    unsolved: int


class ActivityEventRead(ApiModel):
    """A realtime activity record."""

    id: int
    team_id: str | None = None
    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime


class DashboardSnapshot(ApiModel):
    """The aggregated payload powering the overview dashboard."""

    overview: OverviewStats
    scoreboard: list[TeamScoreRead]
    categories: list[CategoryStats]
    contributions: list[MemberContributionRead]
    recent_events: list[ActivityEventRead]
    competition_seconds_remaining: float
    generated_at: datetime
