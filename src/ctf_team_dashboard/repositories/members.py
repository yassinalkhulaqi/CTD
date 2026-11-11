"""Member repository."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from typing import Any

from ctf_team_dashboard.domain.enums import MemberRole, Presence
from ctf_team_dashboard.domain.models import Member, utcnow
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    format_datetime,
    parse_datetime,
    row_to_dict,
)


class MemberRepository(BaseRepository):
    """Persistence operations for :class:`Member` records."""

    table = "members"

    @staticmethod
    def to_model(row: sqlite3.Row) -> Member:
        """Map a database row onto the domain model."""
        data = row_to_dict(row)
        joined_at = parse_datetime(str(data["joined_at"]))
        return Member(
            id=str(data["id"]),
            team_id=str(data["team_id"]),
            handle=str(data["handle"]),
            display_name=str(data["display_name"]),
            role=MemberRole.parse(str(data["role"]), MemberRole.ANALYST),
            presence=Presence.parse(str(data["presence"]), Presence.OFFLINE),
            joined_at=joined_at if joined_at is not None else utcnow(),
        )

    def list_all(self, team_id: str | None = None) -> list[Member]:
        """Return members, optionally restricted to a single team."""
        if team_id is None:
            rows = self.fetch_all("SELECT * FROM members ORDER BY handle ASC")
        else:
            rows = self.fetch_all(
                "SELECT * FROM members WHERE team_id = ? ORDER BY handle ASC", (team_id,)
            )
        return [self.to_model(row) for row in rows]

    def get(self, member_id: str) -> Member | None:
        """Return a single member by identifier."""
        row = self.fetch_one("SELECT * FROM members WHERE id = ?", (member_id,))
        return self.to_model(row) if row is not None else None

    def get_by_handle(self, team_id: str, handle: str) -> Member | None:
        """Return a member by team and handle."""
        row = self.fetch_one(
            "SELECT * FROM members WHERE team_id = ? AND handle = ?", (team_id, handle)
        )
        return self.to_model(row) if row is not None else None

    def create(self, member: Member) -> Member:
        """Insert a member and return the persisted record."""
        self.execute(
            """
            INSERT INTO members
                (id, team_id, handle, display_name, role, presence, joined_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                member.id,
                member.team_id,
                member.handle,
                member.display_name,
                member.role.value,
                member.presence.value,
                format_datetime(member.joined_at),
            ),
        )
        return member

    def update(self, member: Member) -> Member:
        """Update a member in place and return the new state."""
        self.execute(
            """
            UPDATE members
               SET handle = ?, display_name = ?, role = ?, presence = ?
             WHERE id = ?
            """,
            (
                member.handle,
                member.display_name,
                member.role.value,
                member.presence.value,
                member.id,
            ),
        )
        return member

    def set_presence(self, member_id: str, presence: Presence) -> bool:
        """Update only the presence flag of a member."""
        return (
            self.execute(
                "UPDATE members SET presence = ? WHERE id = ?", (presence.value, member_id)
            )
            > 0
        )

    def delete(self, member_id: str) -> bool:
        """Delete a member; returns ``True`` when a row was removed."""
        return self.execute("DELETE FROM members WHERE id = ?", (member_id,)) > 0

    def count_matching(self, where: str = "", params: Sequence[Any] = ()) -> int:
        """Return the number of members matching the optional filter."""
        clause = f" WHERE {where}" if where else ""
        value = self.fetch_value(f"SELECT COUNT(*) FROM members{clause}", params, 0)
        return int(value or 0)
