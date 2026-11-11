"""Audit trail of the sensitive operations performed on the dashboard."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("ctf_team_dashboard.audit")


class AuditAction(str, Enum):
    """The actions recorded in the audit trail."""

    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGOUT = "auth.logout"
    TOKEN_REFRESH = "auth.token.refresh"
    API_KEY_CREATED = "auth.api_key.created"
    API_KEY_REVOKED = "auth.api_key.revoked"
    PERMISSION_DENIED = "auth.permission.denied"
    RATE_LIMITED = "security.rate_limited"
    FLAG_SUBMITTED = "challenge.flag.submitted"
    SOLVE_RECORDED = "challenge.solve.recorded"
    SOLVE_REMOVED = "challenge.solve.removed"
    CHALLENGE_CREATED = "challenge.created"
    CHALLENGE_UPDATED = "challenge.updated"
    CHALLENGE_DELETED = "challenge.deleted"
    TEAM_CREATED = "team.created"
    TEAM_UPDATED = "team.updated"
    TEAM_DELETED = "team.deleted"
    MEMBER_CREATED = "member.created"
    MEMBER_UPDATED = "member.updated"
    MEMBER_DELETED = "member.deleted"
    NOTE_CREATED = "challenge.note.created"
    NOTE_UPDATED = "challenge.note.updated"
    NOTE_DELETED = "challenge.note.deleted"


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """A single entry of the audit trail."""

    action: AuditAction
    actor: str
    team_id: str | None = None
    target: str | None = None
    outcome: str = "success"
    details: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON serialisable representation of the entry."""
        return {
            "action": self.action.value,
            "actor": self.actor,
            "team_id": self.team_id,
            "target": self.target,
            "outcome": self.outcome,
            "details": self.details,
            "occurred_at": self.occurred_at.isoformat(),
        }

    def to_json(self) -> str:
        """Return the entry encoded as a JSON document."""
        return json.dumps(self.to_dict(), separators=(",", ":"), default=str)


class AuditLog:
    """An in-memory audit trail with a bounded size."""

    def __init__(self, *, max_entries: int = 1000) -> None:
        self.max_entries = max_entries
        self._entries: list[AuditEntry] = []

    def record(
        self,
        action: AuditAction,
        *,
        actor: str,
        team_id: str | None = None,
        target: str | None = None,
        outcome: str = "success",
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """Record an action in the audit trail.

        Args:
            action: The audited action.
            actor: The identity of the caller.
            team_id: The team the action relates to.
            target: The resource the action applies to.
            outcome: The outcome of the action.
            details: Additional context.

        Returns:
            The recorded entry.
        """
        entry = AuditEntry(
            action=action,
            actor=actor,
            team_id=team_id,
            target=target,
            outcome=outcome,
            details=details or {},
        )
        self._entries.append(entry)
        if len(self._entries) > self.max_entries:
            del self._entries[: len(self._entries) - self.max_entries]
        logger.info("audit %s", entry.to_json())
        return entry

    def recent(self, *, limit: int = 100, action: AuditAction | None = None) -> list[AuditEntry]:
        """Return the most recent entries of the trail.

        Args:
            limit: The maximum number of entries.
            action: Optional action filter.

        Returns:
            The entries, newest first.
        """
        entries = [
            entry
            for entry in reversed(self._entries)
            if action is None or entry.action is action
        ]
        return entries[: max(1, min(limit, self.max_entries))]

    def clear(self) -> None:
        """Remove every entry from the trail."""
        self._entries.clear()

    @property
    def size(self) -> int:
        """Return the number of recorded entries."""
        return len(self._entries)


_audit_log = AuditLog()


def get_audit_log() -> AuditLog:
    """Return the process wide audit trail."""
    return _audit_log


def record(
    action: AuditAction,
    *,
    actor: str,
    team_id: str | None = None,
    target: str | None = None,
    outcome: str = "success",
    details: dict[str, Any] | None = None,
) -> AuditEntry:
    """Record an action in the process wide audit trail."""
    return get_audit_log().record(
        action,
        actor=actor,
        team_id=team_id,
        target=target,
        outcome=outcome,
        details=details,
    )


def redact(value: str) -> str:
    """Return a redacted representation of a sensitive value.

    Args:
        value: The value to redact.

    Returns:
        The redacted value.
    """
    if not value:
        return ""
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
