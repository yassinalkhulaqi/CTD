"""Domain records for the CTF Team Dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Team:
    """A CTF team tracked by the dashboard."""

    id: str
    name: str


@dataclass(frozen=True)
class Member:
    """A team member tracked by the dashboard."""

    id: str
    team_id: str
    handle: str
    display_name: str


@dataclass(frozen=True)
class Challenge:
    """A single CTF challenge."""

    id: str
    team_id: str
    title: str
    category: str
    difficulty: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None


@dataclass(frozen=True)
class Solve:
    """A flag solve attributed to a member for a challenge."""

    id: str
    challenge_id: str
    member_id: str
    flag: str = ""
    solved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class OverviewStats:
    """Headline counters rendered on the dashboard."""

    teams: int = 0
    members: int = 0
    challenges: int = 0
    solves: int = 0


@dataclass(frozen=True)
class MemberStats:
    """Aggregated solve statistics for one member."""

    member_id: str
    solves: int = 0


@dataclass(frozen=True)
class CategoryStats:
    """Solve statistics grouped by challenge category."""

    category: str
    challenges: int = 0
    solves: int = 0
