"""Aggregate statistics services backing the dashboard overview."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from ctf_team_dashboard.domain.enums import ChallengeCategory, EventKind
from ctf_team_dashboard.domain.models import (
    ActivityEvent,
    CategoryBreakdown,
    Challenge,
    CompetitionWindow,
    Member,
    Solve,
    ensure_utc,
    utcnow,
)
from ctf_team_dashboard.models import CategoryStats, MemberStats
from ctf_team_dashboard.repositories import Repositories


class StatsService:
    """Derive the aggregated metrics shown by the dashboard."""

    def __init__(self, repositories: Repositories | None = None) -> None:
        self.repositories = repositories or Repositories()

    def overview(self) -> dict[str, float | int]:
        """Return the headline counters of the dashboard."""
        teams = self.repositories.teams.count_matching()
        members = self.repositories.members.count_matching()
        challenges = self.repositories.challenges.count_matching()
        solves = self.repositories.solves.count_matching()
        solved_challenges = self.repositories.challenges.count_matching(
            "status = ?", ("solved",)
        )
        points = int(
            self.repositories.solves.fetch_value(
                "SELECT COALESCE(SUM(points_awarded), 0) FROM solves"
            )
            or 0
        )
        active_members = self.repositories.members.count_matching("presence = ?", ("online",))
        completion = (solved_challenges / challenges) if challenges else 0.0
        return {
            "teams": teams,
            "members": members,
            "challenges": challenges,
            "solves": solves,
            "solved_challenges": solved_challenges,
            "completion_rate": round(completion, 4),
            "total_points": points,
            "active_members": active_members,
        }

    def categories(self) -> list[CategoryBreakdown]:
        """Return per-category solve statistics ordered by category name."""
        challenges = self.repositories.challenges.list_all()
        solves = self.repositories.solves.list_all()
        challenge_by_id = {challenge.id: challenge for challenge in challenges}
        breakdown: dict[ChallengeCategory, list[int]] = {}
        for challenge in challenges:
            entry = breakdown.setdefault(challenge.category, [0, 0])
            entry[0] += 1
        for solve in solves:
            solved_challenge = challenge_by_id.get(solve.challenge_id)
            if solved_challenge is None:
                continue
            entry = breakdown.setdefault(solved_challenge.category, [0, 0])
            entry[1] += 1
        return [
            CategoryBreakdown(
                category=category,
                challenges=counts[0],
                solves=counts[1],
            )
            for category, counts in sorted(breakdown.items(), key=lambda item: item[0].value)
        ]

    def competition_window(self) -> CompetitionWindow:
        """Return the earliest start and latest end across all challenges."""
        row = self.repositories.challenges.fetch_one(
            "SELECT MIN(starts_at) AS starts_at, MAX(ends_at) AS ends_at FROM challenges"
        )
        if row is None:
            return CompetitionWindow()
        starts_at = row["starts_at"]
        ends_at = row["ends_at"]
        parsed_start = _parse(starts_at)
        parsed_end = _parse(ends_at)
        return CompetitionWindow(starts_at=parsed_start, ends_at=parsed_end)

    def solve_timeline(self, hours: int = 24, team_id: str | None = None) -> list[int]:
        """Return the number of solves per hour for the trailing window."""
        now = utcnow()
        window_start = now - timedelta(hours=hours)
        buckets = [0] * hours
        solves = self.repositories.solves.solved_at_between(window_start, now, team_id)
        for solve in solves:
            offset = int((now - solve.solved_at).total_seconds() // 3600)
            index = max(0, min(hours - 1, hours - 1 - offset))
            buckets[index] += 1
        return buckets

    def solve_heatmap(self, team_id: str | None = None) -> list[list[int]]:
        """Return a 7x24 matrix of solves indexed by weekday and hour."""
        matrix = [[0 for _ in range(24)] for _ in range(7)]
        solves = self.repositories.solves.list_all(team_id=team_id)
        for solve in solves:
            weekday = solve.solved_at.weekday()
            matrix[weekday][solve.solved_at.hour] += 1
        return matrix

    def difficulty_breakdown(self) -> dict[str, int]:
        """Return the number of solves grouped by difficulty tier."""
        all_challenges = self.repositories.challenges.list_all()
        challenges = {challenge.id: challenge for challenge in all_challenges}
        counts: dict[str, int] = {}
        for solve in self.repositories.solves.list_all():
            solved_challenge = challenges.get(solve.challenge_id)
            if solved_challenge is None:
                continue
            key = solved_challenge.difficulty.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def recent_activity(self, limit: int = 20) -> list[ActivityEvent]:
        """Return the most recent activity events."""
        return self.repositories.events.recent(
            limit=limit,
            kinds=[
                EventKind.SOLVE_CREATED,
                EventKind.SOLVE_REMOVED,
                EventKind.CHALLENGE_CREATED,
                EventKind.CHALLENGE_UPDATED,
                EventKind.CHALLENGE_DELETED,
                EventKind.MEMBER_UPDATED,
                EventKind.PRESENCE_CHANGED,
            ],
        )

    def leaderboard(self) -> list[dict[str, float | int | str]]:
        """Return the team leaderboard enriched with completion rates."""
        teams = self.repositories.teams.list_all()
        members = self.repositories.members.list_all()
        challenges = self.repositories.challenges.list_all()
        solves = self.repositories.solves.list_all()

        challenge_by_id = {challenge.id: challenge for challenge in challenges}
        team_solves: dict[str, int] = {}
        team_points: dict[str, int] = {}
        for solve in solves:
            solved_challenge = challenge_by_id.get(solve.challenge_id)
            if solved_challenge is None:
                continue
            team_id = solved_challenge.team_id
            team_solves[team_id] = team_solves.get(team_id, 0) + 1
            team_points[team_id] = team_points.get(team_id, 0) + solve.points_awarded
        challenge_count: dict[str, int] = {}
        for challenge in challenges:
            challenge_count[challenge.team_id] = challenge_count.get(challenge.team_id, 0) + 1
        member_count: dict[str, int] = {}
        for member in members:
            member_count[member.team_id] = member_count.get(member.team_id, 0) + 1

        rows: list[dict[str, float | int | str]] = []
        for team in teams:
            solves_total = team_solves.get(team.id, 0)
            total = challenge_count.get(team.id, 0)
            rows.append(
                {
                    "team_id": team.id,
                    "team_name": team.name,
                    "solves": solves_total,
                    "points": team_points.get(team.id, 0),
                    "challenges": total,
                    "members": member_count.get(team.id, 0),
                    "completion_rate": round(solves_total / total, 4) if total else 0.0,
                }
            )
        rows.sort(key=lambda row: (-int(row["points"]), -int(row["solves"])))
        return rows


def _parse(value: object) -> datetime | None:
    """Parse a raw timestamp column into an aware datetime."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


# ----------------------------------------------------------------------
# Pure helpers
#
# These functions are side effect free and operate on in-memory collections.
# They are kept separate from :class:`StatsService` so that they can be reused
# by the realtime event stream and by unit tests without touching the database.
# ----------------------------------------------------------------------
def compute_overview(
    *,
    team_count: int,
    member_count: int,
    challenge_count: int,
    solve_count: int,
) -> dict[str, float | int]:
    """Aggregate headline counters for the dashboard."""
    return {
        "teams": team_count,
        "members": member_count,
        "challenges": challenge_count,
        "solves": solve_count,
    }


def compute_member_stats(
    members: Sequence[Member],
    solves: Sequence[Solve],
    challenges: Sequence[Challenge],
) -> list[MemberStats]:
    """Aggregate solves per member across known challenges."""
    known_challenge_ids = {challenge.id for challenge in challenges}
    counts: dict[str, int] = {member.id: 0 for member in members}
    points: dict[str, int] = {member.id: 0 for member in members}
    for solve in solves:
        if solve.challenge_id not in known_challenge_ids:
            continue
        if solve.member_id not in counts:
            continue
        counts[solve.member_id] += 1
        points[solve.member_id] += solve.points_awarded
    return [
        MemberStats(member_id=member.id, solves=counts[member.id], points=points[member.id])
        for member in sorted(members, key=lambda item: item.handle)
    ]


def compute_category_stats(
    challenges: Sequence[Challenge],
    solves: Sequence[Solve],
) -> list[CategoryStats]:
    """Aggregate solve counts per challenge category."""
    challenge_by_id = {challenge.id: challenge for challenge in challenges}
    challenge_counts: dict[str, int] = {}
    solve_counts: dict[str, int] = {}
    for challenge in challenges:
        key = ChallengeCategory.parse(str(challenge.category), ChallengeCategory.MISC).value
        challenge_counts[key] = challenge_counts.get(key, 0) + 1
    for solve in solves:
        solved_challenge = challenge_by_id.get(solve.challenge_id)
        if solved_challenge is None:
            continue
        category = ChallengeCategory.parse(
            str(solved_challenge.category), ChallengeCategory.MISC
        )
        key = category.value
        solve_counts[key] = solve_counts.get(key, 0) + 1
    return [
        CategoryStats(
            category=category,
            challenges=challenge_counts.get(category, 0),
            solves=solve_counts.get(category, 0),
            unsolved=max(0, challenge_counts.get(category, 0) - solve_counts.get(category, 0)),
            solve_rate=(
                solve_counts.get(category, 0) / challenge_counts[category]
                if challenge_counts.get(category)
                else 0.0
            ),
        )
        for category in sorted(set(challenge_counts) | set(solve_counts))
    ]


def time_remaining(ends_at: datetime, now: datetime | None = None) -> float:
    """Return seconds remaining until the competition window closes."""
    current = now if now is not None else utcnow()
    return max(0.0, (ensure_utc(ends_at) - ensure_utc(current)).total_seconds())
