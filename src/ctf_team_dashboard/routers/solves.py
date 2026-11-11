"""Solve endpoints for the CTF Team Dashboard."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from ctf_team_dashboard.dependencies import require_permission
from ctf_team_dashboard.domain.models import Solve
from ctf_team_dashboard.schemas import SolveCreate, SolveRead
from ctf_team_dashboard.security.permissions import Permission
from ctf_team_dashboard.services.solves import SolveService

router = APIRouter(tags=["solves"])


def get_solve_service() -> SolveService:
    """Dependency returning the solve service."""
    return SolveService()


SolveServiceDep = Annotated[SolveService, Depends(get_solve_service)]


def _to_read(solve: Solve) -> SolveRead:
    """Map a domain solve onto its API representation."""
    return SolveRead(
        id=solve.id,
        challenge_id=solve.challenge_id,
        member_id=solve.member_id,
        flag=solve.flag,
        points_awarded=solve.points_awarded,
        solved_at=solve.solved_at,
    )


@router.get("/api/solves", response_model=list[SolveRead])
def list_solves(
    service: SolveServiceDep,
    member_id: str | None = None,
    challenge_id: str | None = None,
    team_id: str | None = None,
) -> list[SolveRead]:
    """Return solves filtered by member, challenge and team."""
    found = service.list_solves(
        member_id=member_id, challenge_id=challenge_id, team_id=team_id
    )
    return [_to_read(solve) for solve in found]


@router.get("/api/solves/velocity", response_model=list[int])
def get_velocity(service: SolveServiceDep, team_id: str | None = None) -> list[int]:
    """Return the number of solves per hour over the last 24 hours."""
    return service.solve_velocity(team_id)


@router.get("/api/solves/{solve_id}", response_model=SolveRead)
def get_solve(solve_id: str, service: SolveServiceDep) -> SolveRead:
    """Return a single solve."""
    return _to_read(service.get_solve(solve_id))


@router.post(
    "/api/solves",
    response_model=SolveRead,
    status_code=status.HTTP_201_CREATED,
)
def record_solve(
    payload: SolveCreate,
    service: SolveServiceDep,
    _principal: object = Depends(require_permission(Permission.SOLVE_CREATE)),
) -> SolveRead:
    """Record a solve and award the challenge points."""
    solve = service.record_solve(
        challenge_id=payload.challenge_id,
        member_id=payload.member_id,
        flag=payload.flag,
        points_awarded=payload.points_awarded,
    )
    return _to_read(solve)


@router.delete("/api/solves/{solve_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_solve(
    solve_id: str,
    service: SolveServiceDep,
    _principal: object = Depends(require_permission(Permission.SOLVE_DELETE)),
) -> None:
    """Withdraw a solve."""
    service.delete_solve(solve_id)
