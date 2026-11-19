"""User repository."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from ctf_team_dashboard.domain.enums import MemberRole
from ctf_team_dashboard.domain.models import User, utcnow
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    format_datetime,
    parse_datetime,
    row_to_dict,
)


class UserRepository(BaseRepository):
    """Persistence operations for :class:`User` records."""

    table = "users"

    @staticmethod
    def to_model(row: sqlite3.Row) -> User:
        """Map a database row onto the domain model."""
        data = row_to_dict(row)
        created_at = parse_datetime(str(data["created_at"]))
        return User(
            id=str(data["id"]),
            username=str(data["username"]),
            email=str(data["email"]),
            password_hash=str(data["password_hash"]),
            role=MemberRole.parse(str(data["role"]), MemberRole.VIEWER),
            team_id=str(data["team_id"]) if data["team_id"] else None,
            is_active=bool(data["is_active"]),
            created_at=created_at if created_at is not None else utcnow(),
            last_login_at=parse_datetime(data["last_login_at"]),
        )

    def list_all(self) -> list[User]:
        """Return every user ordered by username."""
        rows = self.fetch_all("SELECT * FROM users ORDER BY username ASC")
        return [self.to_model(row) for row in rows]

    def get(self, user_id: str) -> User | None:
        """Return a user by identifier."""
        row = self.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
        return self.to_model(row) if row is not None else None

    def get_by_username(self, username: str) -> User | None:
        """Return a user by username, case insensitively."""
        row = self.fetch_one("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,))
        return self.to_model(row) if row is not None else None

    def get_by_email(self, email: str) -> User | None:
        """Return a user by email, case insensitively."""
        row = self.fetch_one("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email,))
        return self.to_model(row) if row is not None else None

    def create(self, user: User) -> User:
        """Insert a user and return the persisted record."""
        self.execute(
            """
            INSERT INTO users
                (id, username, email, password_hash, role, team_id, is_active,
                 created_at, last_login_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user.id,
                user.username,
                user.email,
                user.password_hash,
                user.role.value,
                user.team_id,
                1 if user.is_active else 0,
                format_datetime(user.created_at),
                format_datetime(user.last_login_at),
            ),
        )
        return user

    def update(self, user: User) -> User:
        """Update a user in place and return the new state."""
        self.execute(
            """
            UPDATE users
               SET username = ?, email = ?, password_hash = ?, role = ?,
                   team_id = ?, is_active = ?, last_login_at = ?
             WHERE id = ?
            """,
            (
                user.username,
                user.email,
                user.password_hash,
                user.role.value,
                user.team_id,
                1 if user.is_active else 0,
                format_datetime(user.last_login_at),
                user.id,
            ),
        )
        return user

    def record_login(self, user_id: str, moment: datetime | None = None) -> None:
        """Stamp the last successful login timestamp."""
        self.execute(
            "UPDATE users SET last_login_at = ? WHERE id = ?",
            (format_datetime(moment or utcnow()), user_id),
        )

    def delete(self, user_id: str) -> bool:
        """Delete a user; returns ``True`` when a row was removed."""
        return self.execute("DELETE FROM users WHERE id = ?", (user_id,)) > 0

    def count_matching(self, where: str = "", params: Sequence[Any] = ()) -> int:
        """Return the number of users matching the optional filter."""
        clause = f" WHERE {where}" if where else ""
        value = self.fetch_value(f"SELECT COUNT(*) FROM users{clause}", params, 0)
        return int(value or 0)
