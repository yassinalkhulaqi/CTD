"""Persistence for the administration console feature."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from ctf_team_dashboard.domain.models import ensure_utc, utcnow
from ctf_team_dashboard.features.admin_console.models import (
    AccountControl,
    AccountStatus,
    ActionFilter,
    AdminAction,
    AdminActionKind,
    CaseFilter,
    CasePriority,
    CaseStatus,
    ModerationCase,
    ReportType,
    SystemHealth,
    TargetType,
)
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    dump_tags,
    format_datetime,
    parse_datetime,
    parse_tags,
    row_to_dict,
)


def _iso(value: datetime) -> str:
    """Serialise a datetime as a UTC ISO-8601 string."""
    serialised = format_datetime(ensure_utc(value))
    return serialised if serialised is not None else ensure_utc(value).isoformat()


def _moment(value: str | None) -> datetime:
    """Parse a stored timestamp, falling back to the current time."""
    parsed = parse_datetime(value)
    return parsed if parsed is not None else utcnow()


class ModerationCaseRepository(BaseRepository):
    """Store moderation cases in the ``v3_moderation_cases`` table."""

    table = "v3_moderation_cases"

    @staticmethod
    def to_model(row: sqlite3.Row) -> ModerationCase:
        """Map a database row onto a moderation case."""
        data = row_to_dict(row)
        return ModerationCase(
            id=str(data["id"]),
            report_type=ReportType.parse(str(data["report_type"]), ReportType.OTHER),
            target_id=str(data["target_id"]),
            reporter_id=str(data["reporter_id"]),
            status=CaseStatus.parse(str(data["status"]), CaseStatus.OPEN),
            priority=CasePriority.parse(str(data["priority"]), CasePriority.NORMAL),
            assignee_id=str(data["assignee_id"]) if data["assignee_id"] else None,
            resolution=str(data["resolution"]) if data["resolution"] else None,
            created_at=_moment(data["created_at"]),
        )

    def create(self, case: ModerationCase) -> ModerationCase:
        """Insert a new moderation case."""
        self.execute(
            """
            INSERT INTO v3_moderation_cases
                (id, report_type, target_id, reporter_id, status, priority,
                 assignee_id, resolution, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case.id,
                case.report_type.value,
                case.target_id,
                case.reporter_id,
                case.status.value,
                case.priority.value,
                case.assignee_id,
                case.resolution,
                _iso(case.created_at),
            ),
        )
        return case

    def get(self, case_id: str) -> ModerationCase | None:
        """Return a case by identifier."""
        row = self.fetch_one("SELECT * FROM v3_moderation_cases WHERE id = ?", (case_id,))
        return self.to_model(row) if row is not None else None

    def save(self, case: ModerationCase) -> ModerationCase:
        """Persist the current state of a moderation case."""
        self.execute(
            """
            UPDATE v3_moderation_cases
               SET report_type = ?, target_id = ?, reporter_id = ?, status = ?,
                   priority = ?, assignee_id = ?, resolution = ?, created_at = ?
             WHERE id = ?
            """,
            (
                case.report_type.value,
                case.target_id,
                case.reporter_id,
                case.status.value,
                case.priority.value,
                case.assignee_id,
                case.resolution,
                _iso(case.created_at),
                case.id,
            ),
        )
        return case

    def list_all(self) -> list[ModerationCase]:
        """Return every moderation case, newest first."""
        rows = self.fetch_all("SELECT * FROM v3_moderation_cases ORDER BY created_at DESC, id DESC")
        return [self.to_model(row) for row in rows]

    def filtered(self, spec: CaseFilter) -> list[ModerationCase]:
        """Return the page of cases matching a filter."""
        return spec.apply(self.list_all())

    def count_matching(self, spec: CaseFilter) -> int:
        """Return the number of cases matching a filter before pagination."""
        return len(spec.matching(self.list_all()))

    def count_status(self, status: CaseStatus) -> int:
        """Return the number of cases in a given status."""
        return self.count("status = ?", (status.value,))

    def count_priority(self, priority: CasePriority) -> int:
        """Return the number of cases with a given priority."""
        return self.count("priority = ?", (priority.value,))


class AdminActionRepository(BaseRepository):
    """Store the append-only audit trail in ``v3_admin_actions``."""

    table = "v3_admin_actions"

    @staticmethod
    def to_model(row: sqlite3.Row) -> AdminAction:
        """Map a database row onto an audit entry."""
        data = row_to_dict(row)
        return AdminAction(
            id=str(data["id"]),
            actor_id=str(data["actor_id"]),
            target_type=TargetType.parse(str(data["target_type"]), TargetType.SYSTEM),
            target_id=str(data["target_id"]),
            action=AdminActionKind.parse(str(data["action"]), AdminActionKind.CASE_OPENED),
            reason=str(data["reason"]) if data["reason"] else "",
            created_at=_moment(data["created_at"]),
        )

    def create(self, entry: AdminAction) -> AdminAction:
        """Append an action to the audit trail."""
        self.execute(
            """
            INSERT INTO v3_admin_actions
                (id, actor_id, target_type, target_id, action, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.id,
                entry.actor_id,
                entry.target_type.value,
                entry.target_id,
                entry.action.value,
                entry.reason,
                _iso(entry.created_at),
            ),
        )
        return entry

    def get(self, action_id: str) -> AdminAction | None:
        """Return one audit entry by identifier."""
        row = self.fetch_one("SELECT * FROM v3_admin_actions WHERE id = ?", (action_id,))
        return self.to_model(row) if row is not None else None

    def list_all(self) -> list[AdminAction]:
        """Return every audit entry, newest first."""
        rows = self.fetch_all("SELECT * FROM v3_admin_actions ORDER BY created_at DESC, id DESC")
        return [self.to_model(row) for row in rows]

    def filtered(self, spec: ActionFilter) -> list[AdminAction]:
        """Return the page of audit entries matching a filter."""
        return spec.apply(self.list_all())

    def count_matching(self, spec: ActionFilter) -> int:
        """Return the number of audit entries matching a filter."""
        return len([entry for entry in self.list_all() if spec.matches(entry)])

    def count_since(self, moment: datetime) -> int:
        """Return the number of actions recorded since a timestamp."""
        value = self.fetch_value(
            "SELECT COUNT(*) FROM v3_admin_actions WHERE created_at >= ?",
            (_iso(moment),),
            0,
        )
        return int(value or 0)

    def for_target(self, target_type: TargetType, target_id: str) -> list[AdminAction]:
        """Return every action recorded for one target."""
        rows = self.fetch_all(
            """
            SELECT * FROM v3_admin_actions
             WHERE target_type = ? AND target_id = ?
             ORDER BY created_at DESC, id DESC
            """,
            (target_type.value, target_id),
        )
        return [self.to_model(row) for row in rows]


class AccountControlRepository(BaseRepository):
    """Store suspension controls in ``v3_account_controls``."""

    table = "v3_account_controls"

    @staticmethod
    def to_model(row: sqlite3.Row) -> AccountControl:
        """Map a database row onto an account control."""
        data = row_to_dict(row)
        return AccountControl(
            user_id=str(data["user_id"]),
            status=AccountStatus.parse(str(data["status"]), AccountStatus.ACTIVE),
            flags=parse_tags(data["flags"]),
            updated_at=_moment(data["updated_at"]),
        )

    def create(self, control: AccountControl) -> AccountControl:
        """Insert an account control."""
        self.execute(
            """
            INSERT INTO v3_account_controls (user_id, status, flags, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                control.user_id,
                control.status.value,
                dump_tags(control.flags),
                _iso(control.updated_at),
            ),
        )
        return control

    def get(self, user_id: str) -> AccountControl | None:
        """Return the control attached to a user, if one exists."""
        row = self.fetch_one("SELECT * FROM v3_account_controls WHERE user_id = ?", (user_id,))
        return self.to_model(row) if row is not None else None

    def upsert(self, control: AccountControl) -> AccountControl:
        """Insert or update the control attached to a user."""
        existing = self.get(control.user_id)
        if existing is None:
            return self.create(control)
        self.execute(
            """
            UPDATE v3_account_controls
               SET status = ?, flags = ?, updated_at = ?
             WHERE user_id = ?
            """,
            (
                control.status.value,
                dump_tags(control.flags),
                _iso(control.updated_at),
                control.user_id,
            ),
        )
        return control

    def list_all(self) -> list[AccountControl]:
        """Return every account control ordered by user identifier."""
        rows = self.fetch_all("SELECT * FROM v3_account_controls ORDER BY user_id ASC")
        return [self.to_model(row) for row in rows]

    def count_suspended(self) -> int:
        """Return the number of suspended accounts."""
        return self.count("status = ?", (AccountStatus.SUSPENDED.value,))

    def delete(self, user_id: str) -> bool:
        """Remove a control and return whether a row was deleted."""
        return self.execute("DELETE FROM v3_account_controls WHERE user_id = ?", (user_id,)) > 0


class HealthCheckRepository(BaseRepository):
    """Store infrastructure snapshots in ``v3_health_checks``."""

    table = "v3_health_checks"

    @staticmethod
    def to_model(row: sqlite3.Row) -> SystemHealth:
        """Map a database row onto a health snapshot."""
        data = row_to_dict(row)
        return SystemHealth(
            id=str(data["id"]),
            checked_at=_moment(data["checked_at"]),
            database_ok=bool(data["database_ok"]),
            api_latency_ms=float(data["api_latency_ms"]),
            cache_hit_ratio=float(data["cache_hit_ratio"]),
            queue_depth=int(data["queue_depth"]),
        )

    def create(self, check: SystemHealth) -> SystemHealth:
        """Insert a health snapshot."""
        self.execute(
            """
            INSERT INTO v3_health_checks
                (id, checked_at, database_ok, api_latency_ms, cache_hit_ratio,
                 queue_depth)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                check.id,
                _iso(check.checked_at),
                1 if check.database_ok else 0,
                check.api_latency_ms,
                check.cache_hit_ratio,
                check.queue_depth,
            ),
        )
        return check

    def get(self, check_id: str) -> SystemHealth | None:
        """Return a health snapshot by identifier."""
        row = self.fetch_one("SELECT * FROM v3_health_checks WHERE id = ?", (check_id,))
        return self.to_model(row) if row is not None else None

    def list_recent(self, limit: int = 50) -> list[SystemHealth]:
        """Return the most recent health snapshots."""
        rows = self.fetch_all(
            """
            SELECT * FROM v3_health_checks
             ORDER BY checked_at DESC, id DESC
             LIMIT ?
            """,
            (limit,),
        )
        return [self.to_model(row) for row in rows]

    def latest(self) -> SystemHealth | None:
        """Return the newest health snapshot, if any exist."""
        row = self.fetch_one(
            """
            SELECT * FROM v3_health_checks
             ORDER BY checked_at DESC, id DESC
             LIMIT 1
            """
        )
        return self.to_model(row) if row is not None else None

    def count_since(self, moment: datetime) -> int:
        """Return the number of snapshots recorded since a timestamp."""
        value = self.fetch_value(
            "SELECT COUNT(*) FROM v3_health_checks WHERE checked_at >= ?",
            (_iso(moment),),
            0,
        )
        return int(value or 0)

    def remove_before(self, moment: datetime) -> int:
        """Delete snapshots older than a timestamp and return the row count."""
        return self.execute("DELETE FROM v3_health_checks WHERE checked_at < ?", (_iso(moment),))


def repository_status_counts(repository: ModerationCaseRepository) -> dict[str, int]:
    """Return case counts keyed by status value."""
    return {status.value: repository.count_status(status) for status in CaseStatus}


def repository_priority_counts(repository: ModerationCaseRepository) -> dict[str, int]:
    """Return case counts keyed by priority value."""
    return {priority.value: repository.count_priority(priority) for priority in CasePriority}


def as_params(values: Sequence[Any]) -> tuple[Any, ...]:
    """Convert a sequence of SQL parameters into the tuple sqlite expects."""
    return tuple(values)
