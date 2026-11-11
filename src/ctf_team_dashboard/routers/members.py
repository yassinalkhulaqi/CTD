"""Member endpoints for the CTF Team Dashboard."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from ctf_team_dashboard.domain.models import Member
from ctf_team_dashboard.schemas import (
    MemberContributionRead,
    MemberCreate,
    MemberRead,
    MemberUpdate,
    PresenceUpdate,
)
from ctf_team_dashboard.services.members import MemberService

router = APIRouter(tags=["members"])


def get_member_service() -> MemberService:
    """Dependency returning the member service."""
    return MemberService()


MemberServiceDep = Annotated[MemberService, Depends(get_member_service)]


def _to_read(member: Member) -> MemberRead:
    """Map a domain member onto its API representation."""
    return MemberRead(
        id=member.id,
        team_id=member.team_id,
        handle=member.handle,
        display_name=member.display_name,
        role=member.role,
        presence=member.presence,
        joined_at=member.joined_at,
        is_online=member.is_online,
    )


@router.get("/api/members", response_model=list[MemberRead])
def list_members(service: MemberServiceDep, team_id: str | None = None) -> list[MemberRead]:
    """Return every member, optionally scoped to a team."""
    return [_to_read(member) for member in service.list_members(team_id)]


@router.get("/api/members/contributions", response_model=list[MemberContributionRead])
def list_contributions(
    service: MemberServiceDep, team_id: str | None = None
) -> list[MemberContributionRead]:
    """Return per-member contribution statistics."""
    return [
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
        for row in service.contributions(team_id)
    ]


@router.get("/api/members/{member_id}", response_model=MemberRead)
def get_member(member_id: str, service: MemberServiceDep) -> MemberRead:
    """Return a single member."""
    return _to_read(service.get_member(member_id))


@router.post(
    "/api/members",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
)
def create_member(payload: MemberCreate, service: MemberServiceDep) -> MemberRead:
    """Add a member to a team."""
    member = service.create_member(
        team_id=payload.team_id,
        handle=payload.handle,
        display_name=payload.display_name,
        role=payload.role,
    )
    return _to_read(member)


@router.patch("/api/members/{member_id}", response_model=MemberRead)
def update_member(
    member_id: str, payload: MemberUpdate, service: MemberServiceDep
) -> MemberRead:
    """Update an existing member."""
    return _to_read(
        service.update_member(
            member_id,
            handle=payload.handle,
            display_name=payload.display_name,
            role=payload.role,
        )
    )


@router.put("/api/members/{member_id}/presence", response_model=MemberRead)
def set_presence(
    member_id: str, payload: PresenceUpdate, service: MemberServiceDep
) -> MemberRead:
    """Update the presence indicator of a member."""
    return _to_read(service.set_presence(member_id, payload.presence))


@router.delete("/api/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(member_id: str, service: MemberServiceDep) -> None:
    """Remove a member from their team."""
    service.delete_member(member_id)
