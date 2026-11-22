"""HTTP endpoints for the team roster feature."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from ctf_team_dashboard.dependencies import require_permission
from ctf_team_dashboard.features.team_roster.models import (
    Availability,
    Invitation,
    InvitationStatus,
    RosterAssignment,
    RosterMember,
    RosterRole,
    RosterStats,
)
from ctf_team_dashboard.features.team_roster.schemas import (
    AcceptanceResult,
    AvailabilityUpdate,
    InvitationAccept,
    InvitationCreate,
    InvitationRead,
    RoleChange,
    RosterAssignmentCreate,
    RosterAssignmentRead,
    RosterAssignmentUpdate,
    RosterMemberCreate,
    RosterMemberRead,
    RosterMemberUpdate,
    RosterStatsRead,
)
from ctf_team_dashboard.features.team_roster.service import RosterService
from ctf_team_dashboard.security.permissions import Permission

router = APIRouter(prefix="/api/roster", tags=["roster"])

ManagePermission = Annotated[object, Depends(require_permission(Permission.MEMBER_MANAGE))]


def get_roster_service() -> RosterService:
    """Dependency returning the roster service."""
    return RosterService()


RosterServiceDep = Annotated[RosterService, Depends(get_roster_service)]


def _member_read(member: RosterMember) -> RosterMemberRead:
    """Map a domain member onto its API representation."""
    return RosterMemberRead(
        id=member.id,
        team_id=member.team_id,
        handle=member.handle,
        display_name=member.display_name,
        role=member.role,
        specialty=member.specialty,
        timezone=member.timezone,
        availability=member.availability,
        capacity_hours=member.capacity_hours,
        joined_at=member.joined_at,
        initials=member.initials,
        rank=member.rank,
        availability_label=member.availability.label,
        accepts_work=member.accepts_work,
    )


def _invitation_read(invitation: Invitation) -> InvitationRead:
    """Map a domain invitation onto its API representation."""
    return InvitationRead(
        id=invitation.id,
        team_id=invitation.team_id,
        email=invitation.email,
        role=invitation.role,
        token=invitation.token,
        status=invitation.status,
        created_at=invitation.created_at,
        expires_at=invitation.expires_at,
        masked_token=invitation.masked_token,
        effective_status=invitation.effective_status(),
    )


def _assignment_read(assignment: RosterAssignment) -> RosterAssignmentRead:
    """Map a domain assignment onto its API representation."""
    return RosterAssignmentRead(
        id=assignment.id,
        member_id=assignment.member_id,
        challenge_id=assignment.challenge_id,
        hours=assignment.hours,
        assigned_at=assignment.assigned_at,
    )


def _stats_read(stats: RosterStats) -> RosterStatsRead:
    """Map roster statistics onto their API representation."""
    return RosterStatsRead(
        team_id=stats.team_id,
        total_members=stats.total_members,
        total_capacity_hours=stats.total_capacity_hours,
        assigned_hours=stats.assigned_hours,
        assignment_count=stats.assignment_count,
        pending_invitations=stats.pending_invitations,
        by_role={role.value: count for role, count in stats.by_role.items()},
        by_availability={state.value: count for state, count in stats.by_availability.items()},
        utilisation=round(stats.utilisation, 4),
        utilisation_percent=stats.utilisation_percent,
        remaining_hours=stats.remaining_hours,
        available_count=stats.available_count,
        lead_count=stats.lead_count,
    )


# ----------------------------------------------------------------------
# Members
# ----------------------------------------------------------------------
@router.get("", response_model=list[RosterMemberRead])
def list_members(
    service: RosterServiceDep,
    team_id: str | None = None,
    role: RosterRole | None = None,
    availability: Availability | None = None,
) -> list[RosterMemberRead]:
    """Return roster members, optionally filtered by team, role or availability."""
    return [_member_read(member) for member in service.list_members(team_id, role, availability)]


@router.post(
    "",
    response_model=RosterMemberRead,
    status_code=status.HTTP_201_CREATED,
)
def create_member(
    payload: RosterMemberCreate,
    service: RosterServiceDep,
    _principal: ManagePermission,
) -> RosterMemberRead:
    """Add a member to the roster."""
    member = service.add_member(
        team_id=payload.team_id,
        handle=payload.handle,
        display_name=payload.display_name,
        role=payload.role,
        specialty=payload.specialty,
        timezone=payload.timezone,
        availability=payload.availability,
        capacity_hours=payload.capacity_hours,
    )
    return _member_read(member)


@router.get("/stats", response_model=RosterStatsRead)
def get_stats(service: RosterServiceDep, team_id: str | None = None) -> RosterStatsRead:
    """Return aggregated roster statistics."""
    return _stats_read(service.stats(team_id))


# ----------------------------------------------------------------------
# Invitations
# ----------------------------------------------------------------------
@router.get("/invitations", response_model=list[InvitationRead])
def list_invitations(
    service: RosterServiceDep,
    team_id: str | None = None,
    status_filter: InvitationStatus | None = None,
) -> list[InvitationRead]:
    """Return invitations, optionally filtered by team and status."""
    return [
        _invitation_read(invitation)
        for invitation in service.list_invitations(team_id, status_filter)
    ]


@router.post(
    "/invitations",
    response_model=InvitationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_invitation(
    payload: InvitationCreate,
    service: RosterServiceDep,
    _principal: ManagePermission,
) -> InvitationRead:
    """Invite a person to join a team."""
    invitation = service.create_invitation(
        team_id=payload.team_id,
        email=payload.email,
        role=payload.role,
        expires_at=payload.expires_at,
    )
    return _invitation_read(invitation)


@router.post("/invitations/expire", response_model=int)
def expire_invitations(service: RosterServiceDep, _principal: ManagePermission) -> int:
    """Mark all overdue pending invitations as expired."""
    return service.expire_pending_invitations()


@router.post("/invitations/{invitation_id}/accept", response_model=AcceptanceResult)
def accept_invitation(
    invitation_id: str,
    payload: InvitationAccept,
    service: RosterServiceDep,
    _principal: ManagePermission,
) -> AcceptanceResult:
    """Accept an invitation and add the invited member to the roster."""
    member, invitation = service.accept_invitation(
        invitation_id,
        handle=payload.handle,
        display_name=payload.display_name,
    )
    return AcceptanceResult(member=_member_read(member), invitation=_invitation_read(invitation))


@router.post("/invitations/{invitation_id}/revoke", response_model=InvitationRead)
def revoke_invitation(
    invitation_id: str,
    service: RosterServiceDep,
    _principal: ManagePermission,
) -> InvitationRead:
    """Revoke a pending invitation."""
    return _invitation_read(service.revoke_invitation(invitation_id))


# ----------------------------------------------------------------------
# Assignments
# ----------------------------------------------------------------------
@router.get("/assignments", response_model=list[RosterAssignmentRead])
def list_assignments(
    service: RosterServiceDep,
    member_id: str | None = None,
    challenge_id: str | None = None,
) -> list[RosterAssignmentRead]:
    """Return work assignments, optionally filtered by member or challenge."""
    return [
        _assignment_read(assignment)
        for assignment in service.list_assignments(member_id, challenge_id)
    ]


@router.post(
    "/assignments",
    response_model=RosterAssignmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    payload: RosterAssignmentCreate,
    service: RosterServiceDep,
    _principal: ManagePermission,
) -> RosterAssignmentRead:
    """Reserve work for a roster member."""
    assignment = service.assign_hours(
        member_id=payload.member_id,
        challenge_id=payload.challenge_id,
        hours=payload.hours,
    )
    return _assignment_read(assignment)


@router.patch("/assignments/{assignment_id}", response_model=RosterAssignmentRead)
def update_assignment(
    assignment_id: str,
    payload: RosterAssignmentUpdate,
    service: RosterServiceDep,
    _principal: ManagePermission,
) -> RosterAssignmentRead:
    """Change the hours reserved by an assignment."""
    return _assignment_read(service.update_assignment_hours(assignment_id, payload.hours))


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: str,
    service: RosterServiceDep,
    _principal: ManagePermission,
) -> None:
    """Release an assignment."""
    service.remove_assignment(assignment_id)


# ----------------------------------------------------------------------
# Single member
# ----------------------------------------------------------------------
@router.get("/{member_id}", response_model=RosterMemberRead)
def get_member(member_id: str, service: RosterServiceDep) -> RosterMemberRead:
    """Return a single roster member."""
    return _member_read(service.get_member(member_id))


@router.patch("/{member_id}", response_model=RosterMemberRead)
def update_member(
    member_id: str,
    payload: RosterMemberUpdate,
    service: RosterServiceDep,
    _principal: ManagePermission,
) -> RosterMemberRead:
    """Update a roster member."""
    return _member_read(
        service.update_member(
            member_id,
            handle=payload.handle,
            display_name=payload.display_name,
            specialty=payload.specialty,
            timezone=payload.timezone,
            availability=payload.availability,
            capacity_hours=payload.capacity_hours,
        )
    )


@router.patch("/{member_id}/role", response_model=RosterMemberRead)
def change_member_role(
    member_id: str,
    payload: RoleChange,
    service: RosterServiceDep,
    _principal: ManagePermission,
) -> RosterMemberRead:
    """Change the role held by a roster member."""
    actor = service.get_member(payload.actor_id) if payload.actor_id else None
    return _member_read(service.change_role(member_id, payload.role, actor=actor))


@router.put("/{member_id}/availability", response_model=RosterMemberRead)
def change_member_availability(
    member_id: str,
    payload: AvailabilityUpdate,
    service: RosterServiceDep,
    _principal: ManagePermission,
) -> RosterMemberRead:
    """Publish a new availability state for a member."""
    return _member_read(service.set_availability(member_id, payload.availability))


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: str,
    service: RosterServiceDep,
    _principal: ManagePermission,
) -> None:
    """Remove a member and all of their assignments."""
    service.remove_member(member_id)
