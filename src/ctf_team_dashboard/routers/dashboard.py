"""Aggregated dashboard endpoint returning a single round trip payload."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends

from ctf_team_dashboard.domain.enums import ChallengeCategory
from ctf_team_dashboard.schemas import (
    ActivityEventRead,
    CategoryStats,
    DashboardSnapshot,
    MemberContributionRead,
    OverviewStats,
    TeamScoreRead,
)
from ctf_team_dashboard.services.members import MemberService
from ctf_team_dashboard.services.stats import StatsService
from ctf_team_dashboard.services.teams import TeamService

router = APIRouter(tags=["dashboard"])


def get_dashboard_services() -> tuple[StatsService, TeamService, MemberService]:
    """Dependency returning the services backing the dashboard payload."""
    return StatsService(), TeamService(), MemberService()


ServicesDep = Annotated[
    tuple[StatsService, TeamService, MemberService], Depends(get_dashboard_services)
]


@router.get("/api/dashboard", response_model=DashboardSnapshot)
def get_dashboard(
    services: ServicesDep,
    team_id: str | None = None,
) -> DashboardSnapshot:
    """Return the aggregated payload powering the overview dashboard.

    Args:
        services: The services used to compute the payload.
        team_id: Optional team filter applied to the contributions.

    Returns:
        The dashboard snapshot.
    """
    stats_service, team_service, member_service = services

    overview = stats_service.overview()
    categories = stats_service.categories()
    contributions = member_service.contributions(team_id)
    events = stats_service.recent_activity(limit=12)
    window = stats_service.competition_window()

    return DashboardSnapshot(
        overview=OverviewStats(
            teams=int(overview["teams"]),
            members=int(overview["members"]),
            challenges=int(overview["challenges"]),
            solves=int(overview["solves"]),
            solved_challenges=int(overview["solved_challenges"]),
            completion_rate=float(overview["completion_rate"]),
            total_points=int(overview["total_points"]),
            active_members=int(overview["active_members"]),
        ),
        scoreboard=[
            TeamScoreRead(
                team_id=row.team_id,
                team_name=row.team_name,
                solves=row.solves,
                points=row.points,
                challenges=row.challenges,
                members=row.members,
                completion_rate=round(row.completion_rate, 4),
            )
            for row in team_service.scoreboard()
        ],
        categories=[
            CategoryStats(
                category=entry.category,
                label=entry.category.label,
                accent=entry.category.accent,
                challenges=entry.challenges,
                solves=entry.solves,
                solve_rate=round(entry.solve_rate, 4),
                unsolved=entry.unsolved,
            )
            for entry in categories
        ],
        contributions=[
            MemberContributionRead(
                member_id=row.member_id,
                handle=row.handle,
                display_name=row.display_name,
                team_id=row.team_id,
                solves=row.solves,
                points=row.points,
                average_points=round(row.average_points, 2),
                first_solve_at=row.first_solve_at,
                last_solve_at=row.last_solve_at,
            )
            for row in contributions
        ],
        recent_events=[
            ActivityEventRead(
                id=event.id,
                team_id=event.team_id,
                kind=event.kind.value,
                payload=event.payload,
                occurred_at=event.occurred_at,
            )
            for event in events
        ],
        competition_seconds_remaining=round(window.seconds_remaining(), 3),
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/api/dashboard/categories", response_model=list[CategoryStats])
def get_dashboard_categories(services: ServicesDep) -> list[CategoryStats]:
    """Return the category statistics used by the dashboard charts."""
    stats_service = services[0]
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
        for entry in stats_service.categories()
    ]


@router.get("/api/dashboard/categories/{category}", response_model=CategoryStats)
def get_dashboard_category(
    category: ChallengeCategory, services: ServicesDep
) -> CategoryStats:
    """Return the statistics of a single category."""
    stats_service = services[0]
    for entry in stats_service.categories():
        if entry.category is category:
            return CategoryStats(
                category=entry.category,
                label=entry.category.label,
                accent=entry.category.accent,
                challenges=entry.challenges,
                solves=entry.solves,
                solve_rate=round(entry.solve_rate, 4),
                unsolved=entry.unsolved,
            )
    return CategoryStats(
        category=category,
        label=category.label,
        accent=category.accent,
        challenges=0,
        solves=0,
        solve_rate=0.0,
        unsolved=0,
    )
