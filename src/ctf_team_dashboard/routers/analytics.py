"""Analytics endpoints computing the derived competition metrics."""

from __future__ import annotations

import itertools
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends

from ctf_team_dashboard.domain.enums import ChallengeCategory, Difficulty
from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.repositories import Repositories
from ctf_team_dashboard.schemas import (
    CategoryStats,
    DifficultyMatrix,
    SolveIntervalStats,
    TeamScoreRead,
    VelocityPoint,
)

router = APIRouter(tags=["analytics"])


def get_repositories() -> Repositories:
    """Dependency returning the repositories."""
    return Repositories()


RepositoriesDep = Annotated[Repositories, Depends(get_repositories)]


def _median(values: list[float]) -> float:
    """Return the median of a list of numbers."""
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return float(ordered[middle])
    return (float(ordered[middle - 1]) + float(ordered[middle])) / 2


@router.get("/api/analytics/velocity", response_model=list[VelocityPoint])
def get_velocity(
    repositories: RepositoriesDep,
    hours: int = 24,
    team_id: str | None = None,
) -> list[VelocityPoint]:
    """Return the hourly solve velocity of the trailing window.

    Args:
        repositories: The repositories used to read the solves.
        hours: The size of the trailing window in hours.
        team_id: Optional team filter.

    Returns:
        One point per hour, oldest first.
    """
    window = max(1, min(hours, 168))
    now = utcnow()
    start = now - timedelta(hours=window)

    buckets = [0] * window
    for solve in repositories.solves.solved_at_between(start, now, team_id):
        offset = int((now - solve.solved_at).total_seconds() // 3600)
        index = max(0, min(window - 1, window - 1 - offset))
        buckets[index] += 1

    points: list[VelocityPoint] = []
    for index in range(window):
        moment = start + timedelta(hours=index + 1)
        points.append(
            VelocityPoint(
                at=moment,
                count=buckets[index],
            )
        )
    return points


@router.get("/api/analytics/intervals", response_model=SolveIntervalStats)
def get_solve_intervals(
    repositories: RepositoriesDep,
    team_id: str | None = None,
) -> SolveIntervalStats:
    """Return the statistics of the intervals between two solves.

    Args:
        repositories: The repositories used to read the solves.
        team_id: Optional team filter.

    Returns:
        The interval statistics.
    """
    solves = repositories.solves.list_all(team_id=team_id)
    timestamps = sorted(solve.solved_at for solve in solves)
    intervals = [
        (right - left).total_seconds()
        for left, right in itertools.pairwise(timestamps)
        if (right - left).total_seconds() > 0
    ]

    fastest = min(intervals) if intervals else 0.0
    slowest = max(intervals) if intervals else 0.0
    return SolveIntervalStats(
        count=len(intervals),
        median_seconds=round(_median(intervals), 3),
        fastest_seconds=round(fastest, 3),
        slowest_seconds=round(slowest, 3),
        average_seconds=round(sum(intervals) / len(intervals), 3) if intervals else 0.0,
    )


@router.get("/api/analytics/difficulty", response_model=DifficultyMatrix)
def get_difficulty_matrix(repositories: RepositoriesDep) -> DifficultyMatrix:
    """Return the solve counts grouped by difficulty and category.

    Args:
        repositories: The repositories used to read the challenges.

    Returns:
        The difficulty matrix.
    """
    challenges = {challenge.id: challenge for challenge in repositories.challenges.list_all()}
    counts: dict[str, dict[str, int]] = {
        difficulty.value: {category.value: 0 for category in ChallengeCategory}
        for difficulty in Difficulty
    }
    totals: dict[str, int] = {difficulty.value: 0 for difficulty in Difficulty}

    for solve in repositories.solves.list_all():
        challenge = challenges.get(solve.challenge_id)
        if challenge is None:
            continue
        counts[challenge.difficulty.value][challenge.category.value] += 1
        totals[challenge.difficulty.value] += 1

    return DifficultyMatrix(
        difficulties=[difficulty.value for difficulty in Difficulty],
        categories=[category.value for category in ChallengeCategory],
        counts=counts,
        totals=totals,
    )


@router.get("/api/analytics/categories", response_model=list[CategoryStats])
def get_category_analytics(repositories: RepositoriesDep) -> list[CategoryStats]:
    """Return the per-category statistics of the competition.

    Args:
        repositories: The repositories used to read the challenges.

    Returns:
        The category statistics.
    """
    from ctf_team_dashboard.services.stats import StatsService

    service = StatsService(repositories)
    return [
        CategoryStats(
            category=entry.category,
            label=entry.category.label,
            accent=entry.category.accent,
            challenges=entry.challenges,
            solves=entry.solves,
            solve_rate=round(entry.solve_rate, 4),
            unsolved=entry.unsolved,
        )
        for entry in service.categories()
    ]


@router.get("/api/analytics/leaderboard", response_model=list[TeamScoreRead])
def get_leaderboard(repositories: RepositoriesDep) -> list[TeamScoreRead]:
    """Return the leaderboard enriched with the completion rate.

    Args:
        repositories: The repositories used to read the teams.

    Returns:
        The leaderboard rows.
    """
    from ctf_team_dashboard.services.stats import StatsService

    service = StatsService(repositories)
    return [
        TeamScoreRead(
            team_id=str(row["team_id"]),
            team_name=str(row["team_name"]),
            solves=int(row["solves"]),
            points=int(row["points"]),
            challenges=int(row["challenges"]),
            members=int(row["members"]),
            completion_rate=float(row["completion_rate"]),
        )
        for row in service.leaderboard()
    ]


@router.get("/api/analytics/heatmap", response_model=list[list[int]])
def get_heatmap(repositories: RepositoriesDep, team_id: str | None = None) -> list[list[int]]:
    """Return a 7x24 matrix of solves indexed by weekday and hour.

    Args:
        repositories: The repositories used to read the solves.
        team_id: Optional team filter.

    Returns:
        The heatmap matrix.
    """
    from ctf_team_dashboard.services.stats import StatsService

    return StatsService(repositories).solve_heatmap(team_id)


@router.get("/api/analytics/summary", response_model=dict[str, float])
def get_summary(repositories: RepositoriesDep) -> dict[str, float]:
    """Return the headline analytics of the competition.

    Args:
        repositories: The repositories used to read the data.

    Returns:
        The analytics summary.
    """
    from ctf_team_dashboard.services.stats import StatsService

    service = StatsService(repositories)
    overview = service.overview()
    window = service.competition_window()
    return {
        "completion_rate": float(overview["completion_rate"]),
        "total_points": float(overview["total_points"]),
        "solves_per_hour": float(overview["solves"]) / 24 if overview["solves"] else 0.0,
        "seconds_remaining": window.seconds_remaining(),
        "progress": window.progress(),
    }

