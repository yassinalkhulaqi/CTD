"""Business rules for the team roster feature."""

from __future__ import annotations

import uuid
from datetime import datetime

from ctf_team_dashboard.db.engine import Database
from ctf_team_dashboard.domain.models import ensure_utc, utcnow
from ctf_team_dashboard.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from ctf_team_dashboard.features.team_roster.models import (
    MAX_CAPACITY_HOURS,
    Availability,
    Invitation,
    InvitationStatus,
    RosterAssignment,
    RosterMember,
    RosterPermission,
    RosterRole,
    RosterStats,
    build_roster_stats,
    capacity_utilisation,
    default_expiry,
    generate_invite_token,
    is_expired,
    is_valid_email,
    is_valid_handle,
    is_valid_timezone,
    normalise_email,
    normalise_handle,
)
from ctf_team_dashboard.features.team_roster.store import (
    InvitationRepository,
    RosterAssignmentRepository,
    RosterMemberRepository,
)

_DISPLAY_NAME_LIMIT = 64
_SPECIALTY_LIMIT = 80
_MAX_ASSIGNMENT_HOURS = 24.0


class RosterService:
    """Coordinate member, invitation and assignment operations."""

    def __init__(self, database: Database | None = None) -> None:
        self.members = RosterMemberRepository(database)
        self.invitations = InvitationRepository(database)
        self.assignments = RosterAssignmentRepository(database)

    # ------------------------------------------------------------------
    # Members
    # ------------------------------------------------------------------
    def list_members(
        self,
        team_id: str | None = None,
        role: RosterRole | None = None,
        availability: Availability | None = None,
    ) -> list[RosterMember]:
        """Return members matching the optional filters."""
        return self.members.list_all(team_id=team_id, role=role, availability=availability)

    def get_member(self, member_id: str) -> RosterMember:
        """Return a member or raise :class:`NotFoundError`."""
        member = self.members.get(member_id)
        if member is None:
            raise NotFoundError(f"Roster member {member_id!r} does not exist")
        return member

    @staticmethod
    def validate_team_id(team_id: str) -> str:
        """Validate and normalise a team identifier."""
        normalised = team_id.strip()
        if not normalised:
            raise ValidationError("A team identifier is required")
        return normalised

    @staticmethod
    def validate_capacity(capacity_hours: float) -> float:
        """Validate the weekly hour budget of a member."""
        if capacity_hours < 0 or capacity_hours > MAX_CAPACITY_HOURS:
            raise ValidationError(f"Capacity must be between 0 and {MAX_CAPACITY_HOURS:g} hours")
        return round(capacity_hours, 2)

    @staticmethod
    def validate_timezone(timezone: str) -> str:
        """Validate a timezone name."""
        normalised = timezone.strip() or "UTC"
        if not is_valid_timezone(normalised):
            raise ValidationError(f"Invalid timezone {timezone!r}")
        return normalised

    def _validate_handle(self, team_id: str, handle: str, *, ignore_id: str | None) -> str:
        """Normalise a handle and reject duplicates inside a team."""
        normalised = normalise_handle(handle)
        if not is_valid_handle(normalised):
            raise ValidationError(
                "Handle must be 2-32 characters using letters, digits, dots, "
                "dashes or underscores and start with a letter or digit"
            )
        existing = self.members.get_by_handle(team_id, normalised)
        if existing is not None and existing.id != ignore_id:
            raise ConflictError(f"Handle {normalised!r} is already used by this team")
        return normalised

    @staticmethod
    def _validate_display_name(display_name: str) -> str:
        """Trim and validate a display name."""
        normalised = display_name.strip()
        if len(normalised) > _DISPLAY_NAME_LIMIT:
            raise ValidationError(f"Display name must be at most {_DISPLAY_NAME_LIMIT} characters")
        return normalised

    def add_member(
        self,
        *,
        team_id: str,
        handle: str,
        display_name: str = "",
        role: RosterRole = RosterRole.MEMBER,
        specialty: str = "",
        timezone: str = "UTC",
        availability: Availability = Availability.OFFLINE,
        capacity_hours: float = 8.0,
        member_id: str | None = None,
    ) -> RosterMember:
        """Add a member to a team roster, enforcing unique handles."""
        resolved_team = self.validate_team_id(team_id)
        resolved_handle = self._validate_handle(resolved_team, handle, ignore_id=None)
        if len(specialty) > _SPECIALTY_LIMIT:
            raise ValidationError(f"Specialty must be at most {_SPECIALTY_LIMIT} characters")
        member = RosterMember(
            id=member_id or f"roster-{uuid.uuid4().hex[:12]}",
            team_id=resolved_team,
            handle=resolved_handle,
            display_name=self._validate_display_name(display_name) or resolved_handle,
            role=role,
            specialty=specialty.strip(),
            timezone=self.validate_timezone(timezone),
            availability=availability,
            capacity_hours=self.validate_capacity(capacity_hours),
        )
        self.members.create(member)
        return member

    def update_member(
        self,
        member_id: str,
        *,
        handle: str | None = None,
        display_name: str | None = None,
        specialty: str | None = None,
        timezone: str | None = None,
        availability: Availability | None = None,
        capacity_hours: float | None = None,
    ) -> RosterMember:
        """Apply partial updates to a roster member."""
        member = self.get_member(member_id)
        resolved_handle = (
            self._validate_handle(member.team_id, handle, ignore_id=member.id)
            if handle is not None
            else member.handle
        )
        resolved_name = (
            self._validate_display_name(display_name)
            if display_name is not None
            else member.display_name
        )
        resolved_specialty = specialty.strip() if specialty is not None else member.specialty
        if len(resolved_specialty) > _SPECIALTY_LIMIT:
            raise ValidationError(f"Specialty must be at most {_SPECIALTY_LIMIT} characters")
        resolved_timezone = (
            self.validate_timezone(timezone) if timezone is not None else member.timezone
        )
        resolved_capacity = (
            self.validate_capacity(capacity_hours)
            if capacity_hours is not None
            else member.capacity_hours
        )
        if capacity_hours is not None and resolved_capacity < self.assigned_hours(member.id):
            raise ConflictError("Capacity cannot be lower than the already assigned hours")
        updated = member.with_details(
            handle=resolved_handle,
            display_name=resolved_name or resolved_handle,
            specialty=resolved_specialty,
            timezone=resolved_timezone,
            capacity_hours=resolved_capacity,
        )
        if availability is not None:
            updated = updated.with_availability(availability)
        self.members.update(updated)
        return updated

    def change_role(
        self,
        member_id: str,
        role: RosterRole,
        *,
        actor: RosterMember | None = None,
    ) -> RosterMember:
        """Change a member's role, guarding the last lead of a team."""
        member = self.get_member(member_id)
        if actor is not None and not actor.permits(RosterPermission.CHANGE_ROLES):
            raise PermissionDeniedError("The actor may not change roster roles")
        if member.role is RosterRole.LEAD and role is not RosterRole.LEAD:
            leads = self.members.senior_members(member.team_id, RosterRole.LEAD)
            if len(leads) <= 1:
                raise ConflictError("A team must retain at least one lead")
        self.members.set_role(member_id, role)
        return member.with_role(role)

    def set_availability(self, member_id: str, availability: Availability) -> RosterMember:
        """Publish a new availability state for a member."""
        member = self.get_member(member_id)
        self.members.set_availability(member_id, availability)
        return member.with_availability(availability)

    def remove_member(self, member_id: str) -> None:
        """Remove a member together with every assignment they hold."""
        member = self.get_member(member_id)
        if member.role is RosterRole.LEAD:
            leads = self.members.senior_members(member.team_id, RosterRole.LEAD)
            if len(leads) <= 1:
                raise ConflictError("A team must retain at least one lead")
        self.assignments.delete_by_member(member_id)
        self.members.delete(member_id)

    # ------------------------------------------------------------------
    # Assignments
    # ------------------------------------------------------------------
    def list_assignments(
        self, member_id: str | None = None, challenge_id: str | None = None
    ) -> list[RosterAssignment]:
        """Return assignments matching the optional filters."""
        return self.assignments.list_all(member_id=member_id, challenge_id=challenge_id)

    def get_assignment(self, assignment_id: str) -> RosterAssignment:
        """Return an assignment or raise :class:`NotFoundError`."""
        assignment = self.assignments.get(assignment_id)
        if assignment is None:
            raise NotFoundError(f"Roster assignment {assignment_id!r} does not exist")
        return assignment

    def assigned_hours(self, member_id: str) -> float:
        """Return the hours already reserved by a member."""
        self.get_member(member_id)
        return self.assignments.sum_hours(member_id)

    def utilisation_for(self, member_id: str) -> float:
        """Return the capacity utilisation ratio of a member."""
        member = self.get_member(member_id)
        return capacity_utilisation(self.assignments.sum_hours(member_id), member.capacity_hours)

    def _validate_hours(self, hours: float) -> float:
        """Validate an assignment's hour reservation."""
        if hours <= 0 or hours > _MAX_ASSIGNMENT_HOURS:
            raise ValidationError(
                f"Assignment hours must be greater than 0 and at most {_MAX_ASSIGNMENT_HOURS:g}"
            )
        return round(hours, 2)

    def _check_capacity(self, member: RosterMember, hours: float, *, exclude: str | None) -> None:
        """Reject a reservation that would exceed the member's capacity."""
        current = self.assignments.sum_hours(member.id)
        if exclude is not None:
            existing = self.assignments.get(exclude)
            if existing is not None and existing.member_id == member.id:
                current = round(current - existing.hours, 2)
        if current + hours > member.capacity_hours:
            raise ConflictError(
                f"{member.label} has only {round(max(0.0, member.capacity_hours - current), 2):g}h "
                "of free capacity left"
            )

    def assign_hours(
        self,
        *,
        member_id: str,
        challenge_id: str,
        hours: float,
        assignment_id: str | None = None,
    ) -> RosterAssignment:
        """Reserve work for a member, enforcing capacity and uniqueness."""
        member = self.get_member(member_id)
        if not challenge_id.strip():
            raise ValidationError("A challenge identifier is required")
        resolved_hours = self._validate_hours(hours)
        existing = self.assignments.get_for_member_challenge(member_id, challenge_id)
        if existing is not None and existing.id != assignment_id:
            raise ConflictError("This challenge is already assigned to the member")
        self._check_capacity(member, resolved_hours, exclude=assignment_id)
        assignment = RosterAssignment(
            id=assignment_id or f"assign-{uuid.uuid4().hex[:12]}",
            member_id=member_id,
            challenge_id=challenge_id,
            hours=resolved_hours,
        )
        if assignment_id is None:
            self.assignments.create(assignment)
        else:
            self.get_assignment(assignment_id)
            self.assignments.update_hours(assignment_id, resolved_hours)
        return assignment

    def update_assignment_hours(self, assignment_id: str, hours: float) -> RosterAssignment:
        """Change an existing reservation while respecting capacity."""
        assignment = self.get_assignment(assignment_id)
        member = self.get_member(assignment.member_id)
        resolved_hours = self._validate_hours(hours)
        self._check_capacity(member, resolved_hours, exclude=assignment.id)
        self.assignments.update_hours(assignment_id, resolved_hours)
        return assignment.with_hours(resolved_hours)

    def remove_assignment(self, assignment_id: str) -> None:
        """Release a reserved block of work."""
        self.get_assignment(assignment_id)
        self.assignments.delete(assignment_id)

    # ------------------------------------------------------------------
    # Invitations
    # ------------------------------------------------------------------
    def list_invitations(
        self,
        team_id: str | None = None,
        status: InvitationStatus | None = None,
        *,
        refresh: bool = True,
    ) -> list[Invitation]:
        """Return invitations, optionally expiring stale pending ones first."""
        if refresh:
            self.expire_pending_invitations()
        return self.invitations.list_all(team_id=team_id, status=status)

    def get_invitation(self, invitation_id: str) -> Invitation:
        """Return an invitation or raise :class:`NotFoundError`."""
        invitation = self.invitations.get(invitation_id)
        if invitation is None:
            raise NotFoundError(f"Invitation {invitation_id!r} does not exist")
        return invitation

    def get_invitation_by_token(self, token: str) -> Invitation:
        """Return an invitation by its token."""
        invitation = self.invitations.get_by_token(token)
        if invitation is None:
            raise NotFoundError("No invitation matches this token")
        return invitation

    @staticmethod
    def _validate_email(email: str) -> str:
        """Normalise and validate an invitation email address."""
        normalised = normalise_email(email)
        if not is_valid_email(normalised):
            raise ValidationError(f"{email!r} is not a valid email address")
        return normalised

    def _unique_token(self) -> str:
        """Generate a token that is not yet present in the store."""
        for _ in range(5):
            token = generate_invite_token()
            if self.invitations.get_by_token(token) is None:
                return token
        raise ConflictError("Unable to allocate a unique invitation token")

    def create_invitation(
        self,
        *,
        team_id: str,
        email: str,
        role: RosterRole = RosterRole.MEMBER,
        expires_at: datetime | None = None,
        invitation_id: str | None = None,
    ) -> Invitation:
        """Create an invitation, rejecting duplicate pending invitations."""
        resolved_team = self.validate_team_id(team_id)
        resolved_email = self._validate_email(email)
        moment = ensure_utc(utcnow())
        deadline = ensure_utc(expires_at) if expires_at is not None else None
        if deadline is not None and is_expired(deadline, moment):
            raise ValidationError("An invitation must expire in the future")
        self.expire_pending_invitations(moment)
        for pending in self.invitations.pending_for_email(resolved_team, resolved_email):
            if pending.effective_status(moment) is InvitationStatus.PENDING:
                raise ConflictError(
                    f"A pending invitation for {resolved_email} already exists in this team"
                )
        invitation = Invitation(
            id=invitation_id or f"invite-{uuid.uuid4().hex[:12]}",
            team_id=resolved_team,
            email=resolved_email,
            role=role,
            token=self._unique_token(),
            created_at=moment,
            expires_at=deadline if deadline is not None else default_expiry(moment),
        )
        self.invitations.create(invitation)
        return invitation

    def expire_pending_invitations(self, now: datetime | None = None) -> int:
        """Persist the expired state of every overdue pending invitation."""
        moment = ensure_utc(now if now is not None else utcnow())
        return self.invitations.expire_before(moment)

    def accept_invitation(
        self,
        invitation_id: str,
        *,
        handle: str,
        display_name: str = "",
        member_id: str | None = None,
    ) -> tuple[RosterMember, Invitation]:
        """Accept an invitation and materialise the invited roster member."""
        invitation = self.get_invitation(invitation_id)
        moment = ensure_utc(utcnow())
        if invitation.status is InvitationStatus.PENDING and invitation.is_expired(moment):
            self.invitations.set_status(invitation.id, InvitationStatus.EXPIRED)
            invitation = invitation.expired()
        if not invitation.can_be_accepted(moment):
            raise ConflictError(
                f"Invitation is {invitation.status.value} and can no longer be accepted"
            )
        member = self.add_member(
            team_id=invitation.team_id,
            handle=handle,
            display_name=display_name or invitation.email_local,
            role=invitation.role,
            availability=Availability.AVAILABLE,
            member_id=member_id,
        )
        accepted = invitation.accepted(moment)
        self.invitations.set_status(invitation.id, InvitationStatus.ACCEPTED)
        return member, accepted

    def accept_invitation_by_token(
        self, token: str, *, handle: str, display_name: str = ""
    ) -> tuple[RosterMember, Invitation]:
        """Accept an invitation identified by its token."""
        invitation = self.get_invitation_by_token(token)
        return self.accept_invitation(invitation.id, handle=handle, display_name=display_name)

    def revoke_invitation(self, invitation_id: str) -> Invitation:
        """Revoke a pending invitation."""
        invitation = self.get_invitation(invitation_id)
        moment = ensure_utc(utcnow())
        if invitation.status is InvitationStatus.PENDING and invitation.is_expired(moment):
            self.invitations.set_status(invitation.id, InvitationStatus.EXPIRED)
            invitation = invitation.expired()
        if not invitation.is_open:
            raise ConflictError(
                f"Invitation is {invitation.status.value} and can no longer be revoked"
            )
        revoked = invitation.revoked(moment)
        self.invitations.set_status(invitation.id, InvitationStatus.REVOKED)
        return revoked

    def delete_invitation(self, invitation_id: str) -> None:
        """Delete an invitation outright."""
        self.get_invitation(invitation_id)
        self.invitations.delete(invitation_id)

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------
    def stats(self, team_id: str | None = None) -> RosterStats:
        """Return roster statistics for a team or the whole dashboard."""
        members = self.list_members(team_id)
        member_ids = {member.id for member in members}
        assignments = [
            assignment
            for assignment in self.list_assignments()
            if assignment.member_id in member_ids
        ]
        invitations = self.list_invitations(team_id)
        return build_roster_stats(
            members,
            invitations,
            assignments,
            team_id=team_id,
        )

    def busiest_members(self, limit: int = 5) -> list[tuple[RosterMember, float]]:
        """Return members ordered by descending capacity utilisation."""
        rows = [
            (
                member,
                capacity_utilisation(self.assignments.sum_hours(member.id), member.capacity_hours),
            )
            for member in self.list_members()
        ]
        return sorted(rows, key=lambda row: (-row[1], row[0].handle))[:limit]
