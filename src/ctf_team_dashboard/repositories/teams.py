"""Team repository."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from typing import Any

from ctf_team_dashboard.domain.models import Team, utcnow
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    format_datetime,
    parse_datetime,
    row_to_dict,
)


class TeamRepository(BaseRepository):
    """Persistence operations for :class:`Team` records."""

    table = "teams"

    @staticmethod
    def to_model(row: sqlite3.Row) -> Team:
        """Map a database row onto the domain model."""
        data = row_to_dict(row)
        created_at = parse_datetime(str(data["created_at"]))
        return Team(
            id=str(data["id"]),
            name=str(data["name"]),
            slug=str(data["slug"]),
            color=str(data["color"]),
            description=str(data["description"]),
            created_at=created_at if created_at is not None else utcnow(),
        )

    def list_all(self) -> list[Team]:
        """Return every team ordered by name."""
        rows = self.fetch_all("SELECT * FROM teams ORDER BY name ASC")
        return [self.to_model(row) for row in rows]

    def get(self, team_id: str) -> Team | None:
        """Return a single team by identifier."""
        row = self.fetch_one("SELECT * FROM teams WHERE id = ?", (team_id,))
        return self.to_model(row) if row is not None else None

    def get_by_slug(self, slug: str) -> Team | None:
        """Return a single team by its URL slug."""
        row = self.fetch_one("SELECT * FROM teams WHERE slug = ?", (slug,))
        return self.to_model(row) if row is not None else None

    def create(self, team: Team) -> Team:
        """Insert a team and return the persisted record."""
        self.execute(
            """
            INSERT INTO teams (id, name, slug, color, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                team.id,
                team.name,
                team.slug,
                team.color,
                team.description,
                format_datetime(team.created_at),
            ),
        )
        return team

    def update(self, team: Team) -> Team:
        """Update a team in place and return the new state."""
        self.execute(
            """
            UPDATE teams
               SET name = ?, slug = ?, color = ?, description = ?
             WHERE id = ?
            """,
            (team.name, team.slug, team.color, team.description, team.id),
        )
        return team

    def delete(self, team_id: str) -> bool:
        """Delete a team; returns ``True`` when a row was removed."""
        return self.execute("DELETE FROM teams WHERE id = ?", (team_id,)) > 0

    def count_matching(self, where: str = "", params: Sequence[Any] = ()) -> int:
        """Return the number of teams matching the optional filter."""
        clause = f" WHERE {where}" if where else ""
        value = self.fetch_value(f"SELECT COUNT(*) FROM teams{clause}", params, 0)
        return int(value or 0)
