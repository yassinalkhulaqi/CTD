"""Member oriented application services."""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from ctf_team_dashboard.domain.enums import EventKind, MemberRole, Presence
from ctf_team_dashboard.domain.models import Member, MemberContribution
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.repositories import Repositories

_HANDLE_PATTERN = re.compile(r"^[a-z0-9._-]{2,32}$")


class MemberService:
    """Business rules for managing team members and their contributions."""

    def __init__(self, repositories: Repositories | None = None) -> None:
        self.repositories = repositories or Repositories()

    def list_members(self, team_id: str | None = None) -> list[Member]:
        """Return members, optionally scoped to a team."""
        return self.repositories.members.list_all(team_id)

    def get_member(self, member_id: str) -> Member:
        """Return a member or raise :class:`NotFoundError`."""
        member = self.repositories.members.get(member_id)
        if member is None:
            raise NotFoundError(f"Member {member_id!r} does not exist")
        return member

    def create_member(
        self,
        *,
        team_id: str,
        handle: str,
        display_name: str = "",
        role: MemberRole = MemberRole.ANALYST,
        member_id: str | None = None,
    ) -> Member:
        """Create a member, enforcing unique handles inside a team."""
        if self.repositories.teams.get(team_id) is None:
            raise NotFoundError(f"Team {team_id!r} does not exist")
        normalised = handle.strip().lower()
        if not _HANDLE_PATTERN.match(normalised):
            raise ValidationError(
                "Handle must be 2-32 characters using letters, digits, dots, dashes or underscores"
            )
        if self.repositories.members.get_by_handle(team_id, normalised) is not None:
            raise ConflictError(f"Handle {normalised!r} is already used by this team")
        member = Member(
            id=member_id or f"member-{uuid.uuid4().hex[:12]}",
            team_id=team_id,
            handle=normalised,
            display_name=display_name.strip() or normalised,
            role=role,
        )
        self.repositories.members.create(member)
        self.repositories.events.append(
            EventKind.MEMBER_UPDATED,
            team_id=team_id,
            payload={"action": "created", "handle": member.handle},
        )
        return member

    def update_member(
        self,
        member_id: str,
        *,
        handle: str | None = None,
        display_name: str | None = None,
        role: MemberRole | None = None,
    ) -> Member:
        """Apply partial updates to a member.

        Args:
            member_id: Identifier of the member to update.
            handle: New unique handle.
            display_name: New display name.
            role: New role.

        Returns:
            The updated member.
        """
        member = self.get_member(member_id)
        resolved_handle = (handle if handle is not None else member.handle).strip().lower()
        if not _HANDLE_PATTERN.match(resolved_handle):
            raise ValidationError(
                "Handle must be 2-32 characters using letters, digits, dots, dashes or underscores"
            )
        existing = self.repositories.members.get_by_handle(member.team_id, resolved_handle)
        if existing is not None and existing.id != member.id:
            raise ConflictError(f"Handle {resolved_handle!r} is already used by this team")
        resolved_role = role if role is not None else member.role
        resolved_name = display_name if display_name is not None else member.display_name
        updated = Member(
            id=member.id,
            team_id=member.team_id,
            handle=resolved_handle,
            display_name=resolved_name.strip() or resolved_handle,
            role=resolved_role,
            presence=member.presence,
            joined_at=member.joined_at,
        )
        self.repositories.members.update(updated)
        self.repositories.events.append(
            EventKind.MEMBER_UPDATED,
            team_id=member.team_id,
            payload={"action": "updated", "handle": updated.handle},
        )
        return updated

    def set_presence(self, member_id: str, presence: Presence) -> Member:
        """Update the presence indicator of a member."""
        member = self.get_member(member_id)
        self.repositories.members.set_presence(member_id, presence)
        updated = Member(
            id=member.id,
            team_id=member.team_id,
            handle=member.handle,
            display_name=member.display_name,
            role=member.role,
            presence=presence,
            joined_at=member.joined_at,
        )
        self.repositories.events.append(
            EventKind.PRESENCE_CHANGED,
            team_id=member.team_id,
            payload={"handle": member.handle, "presence": presence.value},
        )
        return updated

    def delete_member(self, member_id: str) -> None:
        """Remove a member and the solves attributed to them."""
        member = self.get_member(member_id)
        self.repositories.members.delete(member_id)
        self.repositories.events.append(
            EventKind.MEMBER_UPDATED,
            team_id=member.team_id,
            payload={"action": "deleted", "handle": member.handle},
        )

    def contributions(self, team_id: str | None = None) -> list[MemberContribution]:
        """Return per-member contribution statistics ordered by points."""
        members = self.list_members(team_id)
        solves = self.repositories.solves.list_all(team_id=team_id)
        points: dict[str, int] = {}
        counts: dict[str, int] = {}
        first_seen: dict[str, datetime] = {}
        last_seen: dict[str, datetime] = {}
        for solve in solves:
            counts[solve.member_id] = counts.get(solve.member_id, 0) + 1
            points[solve.member_id] = points.get(solve.member_id, 0) + solve.points_awarded
            known = first_seen.get(solve.member_id)
            if known is None or solve.solved_at < known:
                first_seen[solve.member_id] = solve.solved_at
            latest = last_seen.get(solve.member_id)
            if latest is None or solve.solved_at > latest:
                last_seen[solve.member_id] = solve.solved_at

        rows = [
            MemberContribution(
                member_id=member.id,
                handle=member.handle,
                display_name=member.display_name,
                team_id=member.team_id,
                solves=counts.get(member.id, 0),
                points=points.get(member.id, 0),
                first_solve_at=first_seen.get(member.id),
                last_solve_at=last_seen.get(member.id),
            )
            for member in members
        ]
        return sorted(rows, key=lambda row: (-row.points, -row.solves, row.handle))
