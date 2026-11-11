"""Backwards compatible facade over the domain layer.

The original scaffold exposed the domain records from this module. The records
now live in :mod:`ctf_team_dashboard.domain.models`; this module re-exports them
so that existing imports keep working.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ctf_team_dashboard.domain.enums import (
    ChallengeCategory,
    ChallengeStatus,
    Difficulty,
    EventKind,
    MemberRole,
    Presence,
)
from ctf_team_dashboard.domain.models import (
    ActivityEvent,
    CategoryBreakdown,
    Challenge,
    CompetitionWindow,
    Member,
    MemberContribution,
    Solve,
    Team,
    TeamScore,
    ensure_utc,
    utcnow,
)


@dataclass(frozen=True, slots=True)
class OverviewStats:
    """Headline counters rendered on the dashboard."""

    teams: int = 0
    members: int = 0
    challenges: int = 0
    solves: int = 0
    solved_challenges: int = 0
    completion_rate: float = 0.0
    total_points: int = 0
    active_members: int = 0


@dataclass(frozen=True, slots=True)
class MemberStats:
    """Aggregated solve statistics for one member."""

    member_id: str
    solves: int = 0
    points: int = 0
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class CategoryStats:
    """Solve statistics grouped by challenge category."""

    category: str
    challenges: int = 0
    solves: int = 0
    unsolved: int = 0
    solve_rate: float = 0.0


__all__ = [
    "ActivityEvent",
    "CategoryBreakdown",
    "CategoryStats",
    "Challenge",
    "ChallengeCategory",
    "ChallengeStatus",
    "CompetitionWindow",
    "Difficulty",
    "EventKind",
    "Member",
    "MemberContribution",
    "MemberRole",
    "MemberStats",
    "OverviewStats",
    "Presence",
    "Solve",
    "Team",
    "TeamScore",
    "ensure_utc",
    "utcnow",
]
