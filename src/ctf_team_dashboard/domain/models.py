"""Immutable domain entities for the CTF Team Dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ctf_team_dashboard.domain.enums import (
    ChallengeCategory,
    ChallengeStatus,
    Difficulty,
    EventKind,
    MemberRole,
    Presence,
)


def utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    """Normalise a datetime to timezone-aware UTC.

    Naive datetimes are assumed to already be expressed in UTC, which keeps
    ingestion of legacy rows safe while guaranteeing that every timestamp
    leaving the domain layer carries an explicit offset.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class Team:
    """A CTF team tracked by the dashboard."""

    id: str
    name: str
    slug: str
    color: str = "#6366f1"
    description: str = ""
    created_at: datetime = field(default_factory=utcnow)

    @property
    def initials(self) -> str:
        """Return up to two uppercase initials derived from the team name."""
        parts = [part for part in self.name.split() if part]
        if not parts:
            return "??"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[1][0]).upper()


@dataclass(frozen=True, slots=True)
class Member:
    """A team member tracked by the dashboard."""

    id: str
    team_id: str
    handle: str
    display_name: str
    role: MemberRole = MemberRole.ANALYST
    presence: Presence = Presence.OFFLINE
    joined_at: datetime = field(default_factory=utcnow)

    @property
    def is_online(self) -> bool:
        """Return whether the member is currently connected."""
        return self.presence is Presence.ONLINE

    @property
    def label(self) -> str:
        """Return the preferred human readable name for the member."""
        return self.display_name or self.handle


@dataclass(frozen=True, slots=True)
class Challenge:
    """A single CTF challenge."""

    id: str
    team_id: str
    title: str
    category: ChallengeCategory
    difficulty: Difficulty
    points: int = 100
    description: str = ""
    status: ChallengeStatus = ChallengeStatus.PENDING
    tags: tuple[str, ...] = ()
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    created_at: datetime = field(default_factory=utcnow)

    @property
    def is_solved(self) -> bool:
        """Return whether the challenge has been solved."""
        return self.status is ChallengeStatus.SOLVED

    @property
    def is_open(self) -> bool:
        """Return whether the challenge is currently playable."""
        return self.status in (ChallengeStatus.PENDING, ChallengeStatus.ACTIVE)

    def seconds_remaining(self, now: datetime | None = None) -> float:
        """Return seconds left before the challenge window closes."""
        if self.ends_at is None:
            return 0.0
        current = ensure_utc(now if now is not None else utcnow())
        return max(0.0, (ensure_utc(self.ends_at) - current).total_seconds())

    def seconds_until_start(self, now: datetime | None = None) -> float:
        """Return seconds remaining until the challenge window opens."""
        if self.starts_at is None:
            return 0.0
        current = ensure_utc(now if now is not None else utcnow())
        return max(0.0, (ensure_utc(self.starts_at) - current).total_seconds())

    @property
    def difficulty_points(self) -> int:
        """Return the base point value implied by the difficulty tier."""
        return int(self.points * self.difficulty.weight)


@dataclass(frozen=True, slots=True)
class Solve:
    """A flag solve attributed to a member for a challenge."""

    id: str
    challenge_id: str
    member_id: str
    flag: str = ""
    points_awarded: int = 0
    solved_at: datetime = field(default_factory=utcnow)

    @property
    def is_scored(self) -> bool:
        """Return whether the solve contributed points to the team."""
        return self.points_awarded > 0


@dataclass(frozen=True, slots=True)
class Note:
    """A note attached to a challenge by a team member."""

    id: str
    challenge_id: str
    member_id: str
    body: str
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    @property
    def preview(self) -> str:
        """Return the first 140 characters of the note."""
        collapsed = " ".join(self.body.split())
        if len(collapsed) <= 140:
            return collapsed
        return f"{collapsed[:139]}…"


@dataclass(frozen=True, slots=True)
class ActivityEvent:
    """An append-only realtime activity record."""

    id: int
    team_id: str | None
    kind: EventKind
    payload: dict[str, Any]
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class User:
    """A dashboard account able to authenticate against the API."""

    id: str
    username: str
    email: str
    password_hash: str
    role: MemberRole = MemberRole.VIEWER
    team_id: str | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=utcnow)
    last_login_at: datetime | None = None

    @property
    def is_admin(self) -> bool:
        """Return whether the user holds administrative clearance."""
        return self.role.satisfies(MemberRole.ADMIN)

    @property
    def can_write(self) -> bool:
        """Return whether the user may record solves."""
        return self.role.satisfies(MemberRole.ANALYST)


@dataclass(frozen=True, slots=True)
class ApiKey:
    """A long lived credential used for machine to machine access."""

    id: str
    user_id: str
    name: str
    prefix: str
    secret_hash: str
    scopes: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=utcnow)
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None

    @property
    def is_revoked(self) -> bool:
        """Return whether the key has been revoked."""
        return self.revoked_at is not None

    @property
    def masked(self) -> str:
        """Return the display form of the key."""
        return f"ctfd_{self.prefix}_{'*' * 8}"

    def allows(self, permission: str) -> bool:
        """Return whether the key scope covers the requested permission."""
        return not self.scopes or permission in self.scopes


@dataclass(frozen=True, slots=True)
class TeamScore:
    """Aggregated scoreboard row for a single team."""

    team_id: str
    team_name: str
    solves: int = 0
    points: int = 0
    challenges: int = 0
    members: int = 0

    @property
    def completion_rate(self) -> float:
        """Return the fraction of the team's challenges that were solved."""
        if self.challenges <= 0:
            return 0.0
        return self.solves / self.challenges


@dataclass(frozen=True, slots=True)
class CategoryBreakdown:
    """Solve statistics for one challenge category."""

    category: ChallengeCategory
    challenges: int = 0
    solves: int = 0

    @property
    def solve_rate(self) -> float:
        """Return the ratio of solved challenges within the category."""
        if self.challenges <= 0:
            return 0.0
        return self.solves / self.challenges

    @property
    def unsolved(self) -> int:
        """Return the number of outstanding challenges in the category."""
        return max(0, self.challenges - self.solves)


@dataclass(frozen=True, slots=True)
class MemberContribution:
    """Contribution statistics for one member."""

    member_id: str
    handle: str
    display_name: str
    team_id: str
    solves: int = 0
    points: int = 0
    first_solve_at: datetime | None = None
    last_solve_at: datetime | None = None

    @property
    def average_points(self) -> float:
        """Return the mean points contributed per solve."""
        if self.solves <= 0:
            return 0.0
        return self.points / self.solves


@dataclass(frozen=True, slots=True)
class CompetitionWindow:
    """The overall competition timing envelope."""

    starts_at: datetime | None = None
    ends_at: datetime | None = None

    def seconds_remaining(self, now: datetime | None = None) -> float:
        """Return seconds left until the competition ends."""
        if self.ends_at is None:
            return 0.0
        current = ensure_utc(now if now is not None else utcnow())
        return max(0.0, (ensure_utc(self.ends_at) - current).total_seconds())

    def seconds_elapsed(self, now: datetime | None = None) -> float:
        """Return seconds elapsed since the competition started."""
        if self.starts_at is None:
            return 0.0
        current = ensure_utc(now if now is not None else utcnow())
        return max(0.0, (current - ensure_utc(self.starts_at)).total_seconds())

    def total_seconds(self) -> float:
        """Return the total length of the competition window."""
        if self.starts_at is None or self.ends_at is None:
            return 0.0
        return max(0.0, (ensure_utc(self.ends_at) - ensure_utc(self.starts_at)).total_seconds())

    def progress(self, now: datetime | None = None) -> float:
        """Return the fraction of the competition window that has elapsed."""
        total = self.total_seconds()
        if total <= 0:
            return 0.0
        return min(1.0, self.seconds_elapsed(now) / total)
