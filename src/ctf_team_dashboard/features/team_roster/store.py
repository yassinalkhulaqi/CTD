"""SQLite persistence for the team roster feature.

Every query is parameterised and filter clauses are selected from a fixed set
of fragments, so caller supplied values can never alter the SQL structure.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.features.team_roster.models import (
    Availability,
    Invitation,
    InvitationStatus,
    RosterAssignment,
    RosterMember,
    RosterRole,
)
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    format_datetime,
    parse_datetime,
    row_to_dict,
)

_MEMBER_COLUMNS = (
    "id, team_id, handle, display_name, role, specialty, timezone, "
    "availability, capacity_hours, joined_at"
)
_INVITATION_COLUMNS = "id, team_id, email, role, token, status, created_at, expires_at"
_ASSIGNMENT_COLUMNS = "id, member_id, challenge_id, hours, assigned_at"


class RosterMemberRepository(BaseRepository):
    """Persistence operations for roster members."""

    table = "v3_roster_members"

    @staticmethod
    def to_model(row: sqlite3.Row) -> RosterMember:
        """Map a database row onto a :class:`RosterMember`."""
        data = row_to_dict(row)
        joined_at = parse_datetime(str(data["joined_at"]))
        return RosterMember(
            id=str(data["id"]),
            team_id=str(data["team_id"]),
            handle=str(data["handle"]),
            display_name=str(data["display_name"]),
            role=RosterRole.parse(str(data["role"]), RosterRole.MEMBER),
            specialty=str(data["specialty"]),
            timezone=str(data["timezone"]),
            availability=Availability.parse(str(data["availability"]), Availability.OFFLINE),
            capacity_hours=float(data["capacity_hours"]),
            joined_at=joined_at if joined_at is not None else utcnow(),
        )

    def list_all(
        self,
        *,
        team_id: str | None = None,
        role: RosterRole | None = None,
        availability: Availability | None = None,
    ) -> list[RosterMember]:
        """Return members ordered by role seniority and handle."""
        clauses: list[str] = []
        params: list[Any] = []
        if team_id is not None:
            clauses.append("team_id = ?")
            params.append(team_id)
        if role is not None:
            clauses.append("role = ?")
            params.append(role.value)
        if availability is not None:
            clauses.append("availability = ?")
            params.append(availability.value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.fetch_all(
            f"SELECT {_MEMBER_COLUMNS} FROM {self.table}{where} ORDER BY role DESC, handle ASC",
            params,
        )
        return [self.to_model(row) for row in rows]

    def get(self, member_id: str) -> RosterMember | None:
        """Return a member by identifier, when one exists."""
        row = self.fetch_one(
            f"SELECT {_MEMBER_COLUMNS} FROM {self.table} WHERE id = ?", (member_id,)
        )
        return self.to_model(row) if row is not None else None

    def get_by_handle(self, team_id: str, handle: str) -> RosterMember | None:
        """Return a member by the team scoped handle."""
        row = self.fetch_one(
            f"SELECT {_MEMBER_COLUMNS} FROM {self.table} WHERE team_id = ? AND handle = ?",
            (team_id, handle),
        )
        return self.to_model(row) if row is not None else None

    def create(self, member: RosterMember) -> RosterMember:
        """Insert a member and return the persisted record."""
        self.execute(
            f"INSERT INTO {self.table} ({_MEMBER_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                member.id,
                member.team_id,
                member.handle,
                member.display_name,
                member.role.value,
                member.specialty,
                member.timezone,
                member.availability.value,
                member.capacity_hours,
                format_datetime(member.joined_at),
            ),
        )
        return member

    def update(self, member: RosterMember) -> RosterMember:
        """Persist all mutable columns of a member."""
        self.execute(
            f"UPDATE {self.table} SET handle = ?, display_name = ?, role = ?,"
            " specialty = ?, timezone = ?, availability = ?, capacity_hours = ?"
            " WHERE id = ?",
            (
                member.handle,
                member.display_name,
                member.role.value,
                member.specialty,
                member.timezone,
                member.availability.value,
                member.capacity_hours,
                member.id,
            ),
        )
        return member

    def set_role(self, member_id: str, role: RosterRole) -> bool:
        """Update only the role column of a member."""
        return (
            self.execute(
                f"UPDATE {self.table} SET role = ? WHERE id = ?",
                (role.value, member_id),
            )
            > 0
        )

    def set_availability(self, member_id: str, availability: Availability) -> bool:
        """Update only the availability column of a member."""
        return (
            self.execute(
                f"UPDATE {self.table} SET availability = ? WHERE id = ?",
                (availability.value, member_id),
            )
            > 0
        )

    def delete(self, member_id: str) -> bool:
        """Delete a member and report whether a row was removed."""
        return self.execute(f"DELETE FROM {self.table} WHERE id = ?", (member_id,)) > 0

    def delete_by_team(self, team_id: str) -> int:
        """Delete every member of a team and return the removed count."""
        return self.execute(f"DELETE FROM {self.table} WHERE team_id = ?", (team_id,))

    def count_for_team(self, team_id: str | None = None) -> int:
        """Return the number of members, optionally scoped to one team."""
        if team_id is None:
            return self.count()
        return self.count("team_id = ?", (team_id,))

    def senior_members(self, team_id: str, role: RosterRole) -> list[RosterMember]:
        """Return members of a team holding at least the requested role."""
        rows = self.fetch_all(
            f"SELECT {_MEMBER_COLUMNS} FROM {self.table}"
            " WHERE team_id = ? AND role = ? ORDER BY handle ASC",
            (team_id, role.value),
        )
        return [self.to_model(row) for row in rows]


class InvitationRepository(BaseRepository):
    """Persistence operations for team invitations."""

    table = "v3_roster_invitations"

    @staticmethod
    def to_model(row: sqlite3.Row) -> Invitation:
        """Map a database row onto an :class:`Invitation`."""
        data = row_to_dict(row)
        created_at = parse_datetime(str(data["created_at"]))
        expires_at = parse_datetime(str(data["expires_at"]))
        return Invitation(
            id=str(data["id"]),
            team_id=str(data["team_id"]),
            email=str(data["email"]),
            role=RosterRole.parse(str(data["role"]), RosterRole.MEMBER),
            token=str(data["token"]),
            status=InvitationStatus.parse(str(data["status"]), InvitationStatus.PENDING),
            created_at=created_at if created_at is not None else utcnow(),
            expires_at=expires_at if expires_at is not None else utcnow(),
        )

    def list_all(
        self,
        *,
        team_id: str | None = None,
        status: InvitationStatus | None = None,
    ) -> list[Invitation]:
        """Return invitations ordered from newest to oldest."""
        clauses: list[str] = []
        params: list[Any] = []
        if team_id is not None:
            clauses.append("team_id = ?")
            params.append(team_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.fetch_all(
            f"SELECT {_INVITATION_COLUMNS} FROM {self.table}{where}"
            " ORDER BY created_at DESC, id DESC",
            params,
        )
        return [self.to_model(row) for row in rows]

    def get(self, invitation_id: str) -> Invitation | None:
        """Return an invitation by identifier, when one exists."""
        row = self.fetch_one(
            f"SELECT {_INVITATION_COLUMNS} FROM {self.table} WHERE id = ?",
            (invitation_id,),
        )
        return self.to_model(row) if row is not None else None

    def get_by_token(self, token: str) -> Invitation | None:
        """Return the invitation carrying a token, when one exists."""
        row = self.fetch_one(
            f"SELECT {_INVITATION_COLUMNS} FROM {self.table} WHERE token = ?", (token,)
        )
        return self.to_model(row) if row is not None else None

    def pending_for_email(self, team_id: str, email: str) -> list[Invitation]:
        """Return pending invitations for an email address inside a team."""
        rows = self.fetch_all(
            f"SELECT {_INVITATION_COLUMNS} FROM {self.table}"
            " WHERE team_id = ? AND email = ? AND status = ?",
            (team_id, email, InvitationStatus.PENDING.value),
        )
        return [self.to_model(row) for row in rows]

    def create(self, invitation: Invitation) -> Invitation:
        """Insert an invitation and return the persisted record."""
        self.execute(
            f"INSERT INTO {self.table} ({_INVITATION_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                invitation.id,
                invitation.team_id,
                invitation.email,
                invitation.role.value,
                invitation.token,
                invitation.status.value,
                format_datetime(invitation.created_at),
                format_datetime(invitation.expires_at),
            ),
        )
        return invitation

    def set_status(self, invitation_id: str, status: InvitationStatus) -> bool:
        """Persist a new lifecycle status for an invitation."""
        return (
            self.execute(
                f"UPDATE {self.table} SET status = ? WHERE id = ?",
                (status.value, invitation_id),
            )
            > 0
        )

    def expire_before(self, instant: datetime) -> int:
        """Mark pending invitations expired at or before ``instant``."""
        return self.execute(
            f"UPDATE {self.table} SET status = ? WHERE status = ? AND expires_at <= ?",
            (
                InvitationStatus.EXPIRED.value,
                InvitationStatus.PENDING.value,
                format_datetime(instant),
            ),
        )

    def delete(self, invitation_id: str) -> bool:
        """Delete an invitation and report whether a row was removed."""
        return self.execute(f"DELETE FROM {self.table} WHERE id = ?", (invitation_id,)) > 0

    def delete_by_team(self, team_id: str) -> int:
        """Delete every invitation of a team and return the removed count."""
        return self.execute(f"DELETE FROM {self.table} WHERE team_id = ?", (team_id,))

    def count_pending(self, team_id: str | None = None) -> int:
        """Return the number of pending invitations, optionally per team."""
        where = "status = ?"
        params: list[Any] = [InvitationStatus.PENDING.value]
        if team_id is not None:
            where += " AND team_id = ?"
            params.append(team_id)
        return self.count(where, params)


class RosterAssignmentRepository(BaseRepository):
    """Persistence operations for roster work assignments."""

    table = "v3_roster_assignments"

    @staticmethod
    def to_model(row: sqlite3.Row) -> RosterAssignment:
        """Map a database row onto a :class:`RosterAssignment`."""
        data = row_to_dict(row)
        assigned_at = parse_datetime(str(data["assigned_at"]))
        return RosterAssignment(
            id=str(data["id"]),
            member_id=str(data["member_id"]),
            challenge_id=str(data["challenge_id"]),
            hours=float(data["hours"]),
            assigned_at=assigned_at if assigned_at is not None else utcnow(),
        )

    def list_all(
        self, *, member_id: str | None = None, challenge_id: str | None = None
    ) -> list[RosterAssignment]:
        """Return assignments ordered from newest to oldest."""
        clauses: list[str] = []
        params: list[Any] = []
        if member_id is not None:
            clauses.append("member_id = ?")
            params.append(member_id)
        if challenge_id is not None:
            clauses.append("challenge_id = ?")
            params.append(challenge_id)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.fetch_all(
            f"SELECT {_ASSIGNMENT_COLUMNS} FROM {self.table}{where}"
            " ORDER BY assigned_at DESC, id DESC",
            params,
        )
        return [self.to_model(row) for row in rows]

    def get(self, assignment_id: str) -> RosterAssignment | None:
        """Return an assignment by identifier, when one exists."""
        row = self.fetch_one(
            f"SELECT {_ASSIGNMENT_COLUMNS} FROM {self.table} WHERE id = ?",
            (assignment_id,),
        )
        return self.to_model(row) if row is not None else None

    def get_for_member_challenge(
        self, member_id: str, challenge_id: str
    ) -> RosterAssignment | None:
        """Return an existing reservation of a challenge for a member."""
        row = self.fetch_one(
            f"SELECT {_ASSIGNMENT_COLUMNS} FROM {self.table}"
            " WHERE member_id = ? AND challenge_id = ?",
            (member_id, challenge_id),
        )
        return self.to_model(row) if row is not None else None

    def create(self, assignment: RosterAssignment) -> RosterAssignment:
        """Insert an assignment and return the persisted record."""
        self.execute(
            f"INSERT INTO {self.table} ({_ASSIGNMENT_COLUMNS}) VALUES (?, ?, ?, ?, ?)",
            (
                assignment.id,
                assignment.member_id,
                assignment.challenge_id,
                assignment.hours,
                format_datetime(assignment.assigned_at),
            ),
        )
        return assignment

    def update_hours(self, assignment_id: str, hours: float) -> bool:
        """Update the reserved hours of an assignment."""
        return (
            self.execute(
                f"UPDATE {self.table} SET hours = ? WHERE id = ?",
                (hours, assignment_id),
            )
            > 0
        )

    def delete(self, assignment_id: str) -> bool:
        """Delete an assignment and report whether a row was removed."""
        return self.execute(f"DELETE FROM {self.table} WHERE id = ?", (assignment_id,)) > 0

    def delete_by_member(self, member_id: str) -> int:
        """Delete every assignment held by a member."""
        return self.execute(f"DELETE FROM {self.table} WHERE member_id = ?", (member_id,))

    def delete_by_challenge(self, challenge_id: str) -> int:
        """Delete every assignment referring to a challenge."""
        return self.execute(f"DELETE FROM {self.table} WHERE challenge_id = ?", (challenge_id,))

    def sum_hours(self, member_id: str) -> float:
        """Return the total hours reserved by one member."""
        value = self.fetch_value(
            f"SELECT COALESCE(SUM(hours), 0) FROM {self.table} WHERE member_id = ?",
            (member_id,),
            0,
        )
        return round(float(value or 0), 2)

    def count_for_member(self, member_id: str) -> int:
        """Return the number of assignments held by one member."""
        return self.count("member_id = ?", (member_id,))

    def list_for_team(
        self, team_id: str, members: Sequence[RosterMember]
    ) -> list[RosterAssignment]:
        """Return assignments belonging to the supplied members of a team."""
        member_ids = [member.id for member in members if member.team_id == team_id]
        if not member_ids:
            return []
        placeholders = ", ".join("?" for _ in member_ids)
        rows = self.fetch_all(
            f"SELECT {_ASSIGNMENT_COLUMNS} FROM {self.table}"
            f" WHERE member_id IN ({placeholders})"
            " ORDER BY assigned_at DESC, id DESC",
            member_ids,
        )
        return [self.to_model(row) for row in rows]
