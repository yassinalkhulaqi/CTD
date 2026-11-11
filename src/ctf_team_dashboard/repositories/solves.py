"""Solve repository."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from ctf_team_dashboard.domain.models import Solve, utcnow
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    format_datetime,
    parse_datetime,
    row_to_dict,
)


class SolveRepository(BaseRepository):
    """Persistence operations for :class:`Solve` records."""

    table = "solves"

    @staticmethod
    def to_model(row: sqlite3.Row) -> Solve:
        """Map a database row onto the domain model."""
        data = row_to_dict(row)
        solved_at = parse_datetime(str(data["solved_at"]))
        return Solve(
            id=str(data["id"]),
            challenge_id=str(data["challenge_id"]),
            member_id=str(data["member_id"]),
            flag=str(data["flag"]),
            points_awarded=int(data["points_awarded"]),
            solved_at=solved_at if solved_at is not None else utcnow(),
        )

    def list_all(
        self,
        *,
        member_id: str | None = None,
        challenge_id: str | None = None,
        team_id: str | None = None,
    ) -> list[Solve]:
        """Return solves filtered by member, challenge and team."""
        clauses: list[str] = []
        params: list[Any] = []
        if member_id is not None:
            clauses.append("s.member_id = ?")
            params.append(member_id)
        if challenge_id is not None:
            clauses.append("s.challenge_id = ?")
            params.append(challenge_id)
        if team_id is not None:
            clauses.append("c.team_id = ?")
            params.append(team_id)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.fetch_all(
            """
            SELECT s.* FROM solves AS s
            JOIN challenges AS c ON c.id = s.challenge_id
            """
            f"{where}"
            " ORDER BY s.solved_at ASC",
            params,
        )
        return [self.to_model(row) for row in rows]

    def get(self, solve_id: str) -> Solve | None:
        """Return a single solve by identifier."""
        row = self.fetch_one("SELECT * FROM solves WHERE id = ?", (solve_id,))
        return self.to_model(row) if row is not None else None

    def get_for_pair(self, challenge_id: str, member_id: str) -> Solve | None:
        """Return the solve recorded for a challenge/member pair."""
        row = self.fetch_one(
            "SELECT * FROM solves WHERE challenge_id = ? AND member_id = ?",
            (challenge_id, member_id),
        )
        return self.to_model(row) if row is not None else None

    def create(self, solve: Solve) -> Solve:
        """Insert a solve and return the persisted record."""
        self.execute(
            """
            INSERT INTO solves
                (id, challenge_id, member_id, flag, points_awarded, solved_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                solve.id,
                solve.challenge_id,
                solve.member_id,
                solve.flag,
                solve.points_awarded,
                format_datetime(solve.solved_at),
            ),
        )
        return solve

    def update(self, solve: Solve) -> Solve:
        """Update a solve in place and return the new state."""
        self.execute(
            """
            UPDATE solves
               SET flag = ?, points_awarded = ?, solved_at = ?
             WHERE id = ?
            """,
            (
                solve.flag,
                solve.points_awarded,
                format_datetime(solve.solved_at),
                solve.id,
            ),
        )
        return solve

    def delete(self, solve_id: str) -> bool:
        """Delete a solve; returns ``True`` when a row was removed."""
        return self.execute("DELETE FROM solves WHERE id = ?", (solve_id,)) > 0

    def count_matching(self, where: str = "", params: Sequence[Any] = ()) -> int:
        """Return the number of solves matching the optional filter."""
        clause = f" WHERE {where}" if where else ""
        value = self.fetch_value(f"SELECT COUNT(*) FROM solves{clause}", params, 0)
        return int(value or 0)

    def solved_at_between(
        self, start: datetime, end: datetime, team_id: str | None = None
    ) -> list[Solve]:
        """Return solves that happened inside a half-open time window."""
        clauses = ["s.solved_at >= ?", "s.solved_at < ?"]
        params: list[Any] = [format_datetime(start), format_datetime(end)]
        if team_id is not None:
            clauses.append("c.team_id = ?")
            params.append(team_id)
        where = " AND ".join(clauses)
        rows = self.fetch_all(
            """
            SELECT s.* FROM solves AS s
            JOIN challenges AS c ON c.id = s.challenge_id
            """
            f" WHERE {where}"
            " ORDER BY s.solved_at ASC",
            params,
        )
        return [self.to_model(row) for row in rows]
