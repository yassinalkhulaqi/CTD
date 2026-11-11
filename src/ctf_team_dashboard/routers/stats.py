"""Statistics endpoints for the CTF Team Dashboard."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ctf_team_dashboard.domain.models import ActivityEvent
from ctf_team_dashboard.repositories import Repositories
from ctf_team_dashboard.schemas import (
    ActivityEventRead,
    CategoryStats,
    OverviewStats,
    TeamScoreRead,
)
from ctf_team_dashboard.services.stats import StatsService

router = APIRouter(tags=["stats"])


def get_stats_service() -> StatsService:
    """Dependency returning the stats service."""
    return StatsService()


StatsServiceDep = Annotated[StatsService, Depends(get_stats_service)]


def _event_to_read(event: ActivityEvent) -> ActivityEventRead:
    """Map a domain event onto its API representation."""
    return ActivityEventRead(
        id=event.id,
        team_id=event.team_id,
        kind=event.kind.value,
        payload=event.payload,
        occurred_at=event.occurred_at,
    )


@router.get("/api/stats/overview", response_model=OverviewStats)
def get_overview(service: StatsServiceDep) -> OverviewStats:
    """Return headline counters for the dashboard."""
    data = service.overview()
    return OverviewStats(
        teams=int(data["teams"]),
        members=int(data["members"]),
        challenges=int(data["challenges"]),
        solves=int(data["solves"]),
        solved_challenges=int(data["solved_challenges"]),
        completion_rate=float(data["completion_rate"]),
        total_points=int(data["total_points"]),
        active_members=int(data["active_members"]),
    )


@router.get("/api/stats/categories", response_model=list[CategoryStats])
def get_categories(service: StatsServiceDep) -> list[CategoryStats]:
    """Return solve statistics grouped by challenge category."""
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


@router.get("/api/stats/leaderboard", response_model=list[TeamScoreRead])
def get_leaderboard(service: StatsServiceDep) -> list[TeamScoreRead]:
    """Return the team leaderboard enriched with completion rates."""
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


@router.get("/api/stats/timeline", response_model=list[int])
def get_timeline(
    service: StatsServiceDep, hours: int = 24, team_id: str | None = None
) -> list[int]:
    """Return the number of solves per hour for the trailing window."""
    return service.solve_timeline(hours=max(1, min(hours, 168)), team_id=team_id)


@router.get("/api/stats/heatmap", response_model=list[list[int]])
def get_heatmap(
    service: StatsServiceDep, team_id: str | None = None
) -> list[list[int]]:
    """Return a 7x24 matrix of solves indexed by weekday and hour."""
    return service.solve_heatmap(team_id)


@router.get("/api/stats/difficulty", response_model=dict[str, int])
def get_difficulty(service: StatsServiceDep) -> dict[str, int]:
    """Return the number of solves grouped by difficulty tier."""
    return service.difficulty_breakdown()


@router.get("/api/stats/competition", response_model=dict[str, float])
def get_competition(service: StatsServiceDep) -> dict[str, float]:
    """Return the competition window timing information."""
    window = service.competition_window()
    return {
        "seconds_remaining": round(window.seconds_remaining(), 3),
        "seconds_elapsed": round(window.seconds_elapsed(), 3),
        "total_seconds": round(window.total_seconds(), 3),
        "progress": round(window.progress(), 4),
    }


@router.get("/api/stats/activity", response_model=list[ActivityEventRead])
def get_activity(service: StatsServiceDep, limit: int = 20) -> list[ActivityEventRead]:
    """Return the most recent activity events."""
    events = service.recent_activity(limit=max(1, min(limit, 200)))
    return [_event_to_read(event) for event in events]


@router.get("/api/stats/events", response_model=list[ActivityEventRead])
def get_events(
    service: StatsServiceDep, limit: int = 50, team_id: str | None = None
) -> list[ActivityEventRead]:
    """Return the raw event feed used by the realtime dashboard."""
    repositories = Repositories()
    events = repositories.events.recent(
        team_id=team_id, limit=max(1, min(limit, 200)), kinds=None
    )
    return [_event_to_read(event) for event in events]
