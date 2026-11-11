"""Team endpoints for the CTF Team Dashboard."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from ctf_team_dashboard.schemas import (
    TeamCreate,
    TeamRead,
    TeamScoreRead,
    TeamUpdate,
)
from ctf_team_dashboard.services.teams import TeamService

router = APIRouter(tags=["teams"])


def get_team_service() -> TeamService:
    """Dependency returning the team service."""
    return TeamService()


TeamServiceDep = Annotated[TeamService, Depends(get_team_service)]


@router.get("/api/teams", response_model=list[TeamRead])
def list_teams(service: TeamServiceDep) -> list[TeamRead]:
    """Return all tracked teams."""
    return [
        TeamRead(
            id=team.id,
            name=team.name,
            slug=team.slug,
            color=team.color,
            description=team.description,
            created_at=team.created_at,
            initials=team.initials,
        )
        for team in service.list_teams()
    ]


@router.get("/api/teams/scoreboard", response_model=list[TeamScoreRead])
def get_scoreboard(service: TeamServiceDep) -> list[TeamScoreRead]:
    """Return the aggregated team leaderboard."""
    return [
        TeamScoreRead(
            team_id=score.team_id,
            team_name=score.team_name,
            solves=score.solves,
            points=score.points,
            challenges=score.challenges,
            members=score.members,
            completion_rate=round(score.completion_rate, 4),
        )
        for score in service.scoreboard()
    ]


@router.get("/api/teams/{team_id}", response_model=TeamRead)
def get_team(team_id: str, service: TeamServiceDep) -> TeamRead:
    """Return a single team."""
    team = service.get_team(team_id)
    return TeamRead(
        id=team.id,
        name=team.name,
        slug=team.slug,
        color=team.color,
        description=team.description,
        created_at=team.created_at,
        initials=team.initials,
    )


@router.post(
    "/api/teams",
    response_model=TeamRead,
    status_code=status.HTTP_201_CREATED,
)
def create_team(payload: TeamCreate, service: TeamServiceDep) -> TeamRead:
    """Create a new team."""
    team = service.create_team(
        name=payload.name,
        slug=payload.slug,
        color=payload.color,
        description=payload.description,
    )
    return TeamRead(
        id=team.id,
        name=team.name,
        slug=team.slug,
        color=team.color,
        description=team.description,
        created_at=team.created_at,
        initials=team.initials,
    )


@router.patch("/api/teams/{team_id}", response_model=TeamRead)
def update_team(team_id: str, payload: TeamUpdate, service: TeamServiceDep) -> TeamRead:
    """Update an existing team."""
    team = service.update_team(
        team_id,
        name=payload.name,
        color=payload.color,
        description=payload.description,
    )
    return TeamRead(
        id=team.id,
        name=team.name,
        slug=team.slug,
        color=team.color,
        description=team.description,
        created_at=team.created_at,
        initials=team.initials,
    )


@router.delete("/api/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(team_id: str, service: TeamServiceDep) -> None:
    """Delete a team and every dependent record."""
    service.delete_team(team_id)
