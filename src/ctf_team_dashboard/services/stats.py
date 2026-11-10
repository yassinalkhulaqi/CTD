"""Pure statistics helpers for the CTF Team Dashboard."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import datetime, timezone

from ctf_team_dashboard.models import (
    CategoryStats,
    Challenge,
    Member,
    MemberStats,
    OverviewStats,
    Solve,
)


def compute_overview(
    *,
    team_count: int,
    member_count: int,
    challenge_count: int,
    solve_count: int,
) -> OverviewStats:
    """Aggregate headline counters for the dashboard."""
    return OverviewStats(
        teams=team_count,
        members=member_count,
        challenges=challenge_count,
        solves=solve_count,
    )


def compute_member_stats(
    members: Sequence[Member],
    solves: Sequence[Solve],
    challenges: Sequence[Challenge],
) -> list[MemberStats]:
    """Aggregate solves per member across known challenges."""
    solved_challenge_ids = {challenge.id for challenge in challenges}
    solved_counts: dict[str, int] = {member.id: 0 for member in members}
    for solve in solves:
        if solve.challenge_id in solved_challenge_ids and solve.member_id in solved_counts:
            solved_counts[solve.member_id] += 1
    return [
        MemberStats(member_id=member.id, solves=solved_counts[member.id])
        for member in sorted(members, key=lambda member: member.handle)
    ]


def compute_category_stats(
    challenges: Sequence[Challenge],
    solves: Sequence[Solve],
) -> list[CategoryStats]:
    """Aggregate solve counts per challenge category."""
    challenge_by_id = {challenge.id: challenge for challenge in challenges}
    category_names: set[str] = set()
    challenge_counts: Counter[str] = Counter()
    solve_counts: Counter[str] = Counter()
    for challenge in challenges:
        category_names.add(challenge.category)
        challenge_counts[challenge.category] += 1
    for solve in solves:
        solved_challenge: Challenge | None = challenge_by_id.get(solve.challenge_id)
        if solved_challenge is None:
            continue
        solve_counts[solved_challenge.category] += 1
    return [
        CategoryStats(
            category=category,
            challenges=challenge_counts[category],
            solves=solve_counts[category],
        )
        for category in sorted(category_names)
    ]


def time_remaining(ends_at: datetime, now: datetime | None = None) -> float:
    """Return seconds remaining until the competition window closes."""
    current = now if now is not None else datetime.now(timezone.utc)
    return max(0.0, (ends_at - current).total_seconds())
