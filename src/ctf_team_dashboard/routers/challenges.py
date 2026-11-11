"""Challenge endpoints for the CTF Team Dashboard."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from ctf_team_dashboard.dependencies import require_permission
from ctf_team_dashboard.domain.enums import ChallengeCategory, ChallengeStatus
from ctf_team_dashboard.domain.models import Challenge
from ctf_team_dashboard.schemas import (
    ChallengeCreate,
    ChallengeRead,
    ChallengeStatusUpdate,
    ChallengeUpdate,
)
from ctf_team_dashboard.security.permissions import Permission
from ctf_team_dashboard.services.challenges import ChallengeService

router = APIRouter(tags=["challenges"])


def get_challenge_service() -> ChallengeService:
    """Dependency returning the challenge service."""
    return ChallengeService()


ChallengeServiceDep = Annotated[ChallengeService, Depends(get_challenge_service)]


def _to_read(challenge: Challenge) -> ChallengeRead:
    """Map a domain challenge onto its API representation."""
    return ChallengeRead(
        id=challenge.id,
        team_id=challenge.team_id,
        title=challenge.title,
        category=challenge.category,
        difficulty=challenge.difficulty,
        points=challenge.points,
        description=challenge.description,
        status=challenge.status,
        tags=list(challenge.tags),
        starts_at=challenge.starts_at,
        ends_at=challenge.ends_at,
        created_at=challenge.created_at,
        seconds_remaining=round(challenge.seconds_remaining(), 3),
    )


@router.get("/api/challenges", response_model=list[ChallengeRead])
def list_challenges(
    service: ChallengeServiceDep,
    team_id: str | None = None,
    category: ChallengeCategory | None = None,
    status_filter: Annotated[ChallengeStatus | None, Query(alias="status")] = None,
) -> list[ChallengeRead]:
    """Return challenges filtered by team, category and status."""
    found = service.list_challenges(team_id, category=category, status=status_filter)
    return [_to_read(challenge) for challenge in found]


@router.get("/api/challenges/board", response_model=dict[str, list[ChallengeRead]])
def get_board(
    service: ChallengeServiceDep, team_id: str
) -> dict[str, list[ChallengeRead]]:
    """Return the challenge board grouped by lifecycle status."""
    board = service.board(team_id)
    return {
        status_value: [_to_read(item) for item in items]
        for status_value, items in board.items()
    }


@router.get("/api/challenges/{challenge_id}", response_model=ChallengeRead)
def get_challenge(challenge_id: str, service: ChallengeServiceDep) -> ChallengeRead:
    """Return a single challenge."""
    return _to_read(service.get_challenge(challenge_id))


@router.post(
    "/api/challenges",
    response_model=ChallengeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_challenge(
    payload: ChallengeCreate,
    service: ChallengeServiceDep,
    _principal: object = Depends(require_permission(Permission.CHALLENGE_CREATE)),
) -> ChallengeRead:
    """Create a challenge."""
    challenge = service.create_challenge(
        team_id=payload.team_id,
        title=payload.title,
        category=payload.category,
        difficulty=payload.difficulty,
        points=payload.points,
        description=payload.description,
        status=payload.status,
        tags=payload.tags,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    return _to_read(challenge)


@router.patch("/api/challenges/{challenge_id}", response_model=ChallengeRead)
def update_challenge(
    challenge_id: str,
    payload: ChallengeUpdate,
    service: ChallengeServiceDep,
    _principal: object = Depends(require_permission(Permission.CHALLENGE_UPDATE)),
) -> ChallengeRead:
    """Update an existing challenge."""
    return _to_read(
        service.update_challenge(
            challenge_id,
            title=payload.title,
            category=payload.category,
            difficulty=payload.difficulty,
            points=payload.points,
            description=payload.description,
            status=payload.status,
            tags=payload.tags,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
        )
    )


@router.put("/api/challenges/{challenge_id}/status", response_model=ChallengeRead)
def set_challenge_status(
    challenge_id: str,
    payload: ChallengeStatusUpdate,
    service: ChallengeServiceDep,
    _principal: object = Depends(require_permission(Permission.CHALLENGE_UPDATE)),
) -> ChallengeRead:
    """Move a challenge between lifecycle states."""
    return _to_read(service.set_status(challenge_id, payload.status))


@router.delete("/api/challenges/{challenge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_challenge(
    challenge_id: str,
    service: ChallengeServiceDep,
    _principal: object = Depends(require_permission(Permission.CHALLENGE_DELETE)),
) -> None:
    """Delete a challenge."""
    service.delete_challenge(challenge_id)
