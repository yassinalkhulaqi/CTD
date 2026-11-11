"""API key and session repositories."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from ctf_team_dashboard.domain.models import ApiKey, utcnow
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    dump_tags,
    format_datetime,
    parse_datetime,
    parse_tags,
    row_to_dict,
)


class ApiKeyRepository(BaseRepository):
    """Persistence operations for :class:`ApiKey` records."""

    table = "api_keys"

    @staticmethod
    def to_model(row: sqlite3.Row) -> ApiKey:
        """Map a database row onto the domain model."""
        data = row_to_dict(row)
        created_at = parse_datetime(str(data["created_at"]))
        return ApiKey(
            id=str(data["id"]),
            user_id=str(data["user_id"]),
            name=str(data["name"]),
            prefix=str(data["prefix"]),
            secret_hash=str(data["secret_hash"]),
            scopes=parse_tags(data["scopes"]),
            created_at=created_at if created_at is not None else utcnow(),
            last_used_at=parse_datetime(data["last_used_at"]),
            revoked_at=parse_datetime(data["revoked_at"]),
        )

    def list_for_user(self, user_id: str) -> list[ApiKey]:
        """Return every key owned by a user, newest first."""
        rows = self.fetch_all(
            "SELECT * FROM api_keys WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
        )
        return [self.to_model(row) for row in rows]

    def get(self, key_id: str) -> ApiKey | None:
        """Return a key by identifier."""
        row = self.fetch_one("SELECT * FROM api_keys WHERE id = ?", (key_id,))
        return self.to_model(row) if row is not None else None

    def get_by_prefix(self, prefix: str) -> ApiKey | None:
        """Return a key by its lookup prefix."""
        row = self.fetch_one("SELECT * FROM api_keys WHERE prefix = ?", (prefix,))
        return self.to_model(row) if row is not None else None

    def create(self, key: ApiKey) -> ApiKey:
        """Insert an API key and return the persisted record."""
        self.execute(
            """
            INSERT INTO api_keys
                (id, user_id, name, prefix, secret_hash, scopes, created_at,
                 last_used_at, revoked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                key.id,
                key.user_id,
                key.name,
                key.prefix,
                key.secret_hash,
                dump_tags(key.scopes),
                format_datetime(key.created_at),
                format_datetime(key.last_used_at),
                format_datetime(key.revoked_at),
            ),
        )
        return key

    def revoke(self, key_id: str, moment: datetime | None = None) -> bool:
        """Revoke a key; returns ``True`` when a row was updated."""
        return (
            self.execute(
                "UPDATE api_keys SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
                (format_datetime(moment or utcnow()), key_id),
            )
            > 0
        )

    def touch(self, key_id: str, moment: datetime | None = None) -> None:
        """Record the last time a key was used."""
        self.execute(
            "UPDATE api_keys SET last_used_at = ? WHERE id = ?",
            (format_datetime(moment or utcnow()), key_id),
        )

    def delete(self, key_id: str) -> bool:
        """Delete a key permanently."""
        return self.execute("DELETE FROM api_keys WHERE id = ?", (key_id,)) > 0


class SessionRepository(BaseRepository):
    """Persistence operations for refresh sessions."""

    table = "sessions"

    @staticmethod
    def to_model(row: sqlite3.Row) -> dict[str, Any]:
        """Map a database row onto a plain dictionary."""
        data = row_to_dict(row)
        return {
            "id": str(data["id"]),
            "user_id": str(data["user_id"]),
            "refresh_hash": str(data["refresh_hash"]),
            "created_at": data["created_at"],
            "expires_at": data["expires_at"],
            "revoked_at": data["revoked_at"],
            "user_agent": str(data["user_agent"]),
        }

    def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        """Return every session owned by a user."""
        rows = self.fetch_all(
            "SELECT * FROM sessions WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
        )
        return [self.to_model(row) for row in rows]

    def get(self, session_id: str) -> dict[str, Any] | None:
        """Return a session by identifier."""
        row = self.fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))
        return self.to_model(row) if row is not None else None

    def create(
        self,
        *,
        session_id: str,
        user_id: str,
        refresh_hash: str,
        expires_at: datetime,
        user_agent: str = "",
    ) -> dict[str, Any]:
        """Insert a session and return the persisted record."""
        self.execute(
            """
            INSERT INTO sessions
                (id, user_id, refresh_hash, created_at, expires_at, revoked_at, user_agent)
            VALUES (?, ?, ?, ?, ?, NULL, ?)
            """,
            (
                session_id,
                user_id,
                refresh_hash,
                format_datetime(utcnow()),
                format_datetime(expires_at),
                user_agent,
            ),
        )
        stored = self.get(session_id)
        return stored if stored is not None else {}

    def revoke(self, session_id: str, moment: datetime | None = None) -> bool:
        """Revoke a session; returns ``True`` when a row was updated."""
        return (
            self.execute(
                "UPDATE sessions SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
                (format_datetime(moment or utcnow()), session_id),
            )
            > 0
        )

    def revoke_all_for_user(self, user_id: str) -> int:
        """Revoke every active session of a user."""
        return self.execute(
            "UPDATE sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
            (format_datetime(utcnow()), user_id),
        )

    def prune_expired(self, moment: datetime | None = None) -> int:
        """Delete sessions that expired before ``moment``."""
        return self.execute(
            "DELETE FROM sessions WHERE expires_at < ? AND revoked_at IS NULL",
            (format_datetime(moment or utcnow()),),
        )

    def count_matching(self, where: str = "", params: Sequence[Any] = ()) -> int:
        """Return the number of sessions matching the optional filter."""
        clause = f" WHERE {where}" if where else ""
        value = self.fetch_value(f"SELECT COUNT(*) FROM sessions{clause}", params, 0)
        return int(value or 0)
