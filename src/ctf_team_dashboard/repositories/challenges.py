"""Challenge repository."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from typing import Any

from ctf_team_dashboard.domain.enums import ChallengeCategory, ChallengeStatus, Difficulty
from ctf_team_dashboard.domain.models import Challenge, utcnow
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    dump_tags,
    format_datetime,
    parse_datetime,
    parse_tags,
    row_to_dict,
)


class ChallengeRepository(BaseRepository):
    """Persistence operations for :class:`Challenge` records."""

    table = "challenges"

    @staticmethod
    def to_model(row: sqlite3.Row) -> Challenge:
        """Map a database row onto the domain model."""
        data = row_to_dict(row)
        created_at = parse_datetime(str(data["created_at"]))
        return Challenge(
            id=str(data["id"]),
            team_id=str(data["team_id"]),
            title=str(data["title"]),
            category=ChallengeCategory.parse(str(data["category"]), ChallengeCategory.MISC),
            difficulty=Difficulty.parse(str(data["difficulty"]), Difficulty.EASY),
            points=int(data["points"]),
            description=str(data["description"]),
            status=ChallengeStatus.parse(str(data["status"]), ChallengeStatus.PENDING),
            tags=parse_tags(data["tags"]),
            starts_at=parse_datetime(data["starts_at"]),
            ends_at=parse_datetime(data["ends_at"]),
            created_at=created_at if created_at is not None else utcnow(),
        )

    def list_all(
        self,
        team_id: str | None = None,
        *,
        category: ChallengeCategory | None = None,
        status: ChallengeStatus | None = None,
    ) -> list[Challenge]:
        """Return challenges filtered by team, category and status."""
        clauses: list[str] = []
        params: list[Any] = []
        if team_id is not None:
            clauses.append("team_id = ?")
            params.append(team_id)
        if category is not None:
            clauses.append("category = ?")
            params.append(category.value)
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.fetch_all(f"SELECT * FROM challenges{where} ORDER BY created_at ASC", params)
        return [self.to_model(row) for row in rows]

    def get(self, challenge_id: str) -> Challenge | None:
        """Return a single challenge by identifier."""
        row = self.fetch_one("SELECT * FROM challenges WHERE id = ?", (challenge_id,))
        return self.to_model(row) if row is not None else None

    def create(self, challenge: Challenge) -> Challenge:
        """Insert a challenge and return the persisted record."""
        self.execute(
            """
            INSERT INTO challenges
                (id, team_id, title, category, difficulty, points, description,
                 status, tags, starts_at, ends_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                challenge.id,
                challenge.team_id,
                challenge.title,
                challenge.category.value,
                challenge.difficulty.value,
                challenge.points,
                challenge.description,
                challenge.status.value,
                dump_tags(challenge.tags),
                format_datetime(challenge.starts_at),
                format_datetime(challenge.ends_at),
                format_datetime(challenge.created_at),
            ),
        )
        return challenge

    def update(self, challenge: Challenge) -> Challenge:
        """Update a challenge in place and return the new state."""
        self.execute(
            """
            UPDATE challenges
               SET title = ?, category = ?, difficulty = ?, points = ?,
                   description = ?, status = ?, tags = ?, starts_at = ?, ends_at = ?
             WHERE id = ?
            """,
            (
                challenge.title,
                challenge.category.value,
                challenge.difficulty.value,
                challenge.points,
                challenge.description,
                challenge.status.value,
                dump_tags(challenge.tags),
                format_datetime(challenge.starts_at),
                format_datetime(challenge.ends_at),
                challenge.id,
            ),
        )
        return challenge

    def set_status(self, challenge_id: str, status: ChallengeStatus) -> bool:
        """Update only the lifecycle status of a challenge."""
        return (
            self.execute(
                "UPDATE challenges SET status = ? WHERE id = ?", (status.value, challenge_id)
            )
            > 0
        )

    def delete(self, challenge_id: str) -> bool:
        """Delete a challenge; returns ``True`` when a row was removed."""
        return self.execute("DELETE FROM challenges WHERE id = ?", (challenge_id,)) > 0

    def count_matching(self, where: str = "", params: Sequence[Any] = ()) -> int:
        """Return the number of challenges matching the optional filter."""
        clause = f" WHERE {where}" if where else ""
        value = self.fetch_value(f"SELECT COUNT(*) FROM challenges{clause}", params, 0)
        return int(value or 0)

    def solved_challenge_ids(self) -> set[str]:
        """Return the identifiers of every solved challenge."""
        rows = self.fetch_all(
            "SELECT id FROM challenges WHERE status = ?", (ChallengeStatus.SOLVED.value,)
        )
        return {str(row["id"]) for row in rows}
