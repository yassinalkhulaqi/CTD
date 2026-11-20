"""SQLite persistence for the submission pipeline.

Every query uses bound parameters and the shared :class:`BaseRepository`
helpers. Row mapping is centralised so the service layer only ever sees frozen
domain objects.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.features.submission_pipeline.models import (
    DEFAULT_RULES,
    MemberSubmissionStats,
    RuleKind,
    Submission,
    SubmissionFilters,
    SubmissionStats,
    SubmissionStatus,
    ValidationRule,
)
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    format_datetime,
    parse_datetime,
    row_to_dict,
)

SUBMISSION_COLUMNS = (
    "id",
    "challenge_id",
    "member_id",
    "flag_cipher",
    "status",
    "attempts",
    "created_at",
    "completed_at",
    "error",
    "flag_digest",
    "next_attempt_at",
    "accepted",
)


def _bool(value: Any) -> bool:
    """Convert a SQLite integer flag to a boolean."""
    return bool(value)


class SubmissionRepository(BaseRepository):
    """Persistence operations for :class:`Submission` records."""

    table = "v3_submissions"

    @staticmethod
    def to_model(row: sqlite3.Row) -> Submission:
        """Map a database row onto the domain model."""
        data = row_to_dict(row)
        created = parse_datetime(str(data["created_at"]))
        return Submission(
            id=str(data["id"]),
            challenge_id=str(data["challenge_id"]),
            member_id=str(data["member_id"]),
            flag_cipher=str(data["flag_cipher"]),
            status=SubmissionStatus.parse(str(data["status"])),
            attempts=int(data["attempts"]),
            created_at=created if created is not None else utcnow(),
            completed_at=parse_datetime(data.get("completed_at")),
            error=str(data["error"]) if data.get("error") else None,
            flag_digest=str(data.get("flag_digest") or ""),
            next_attempt_at=parse_datetime(data.get("next_attempt_at")),
            accepted=_bool(data.get("accepted", 0)),
        )

    def list_submissions(self, filters: SubmissionFilters | None = None) -> list[Submission]:
        """Return submissions matching the supplied filters."""
        active = filters or SubmissionFilters()
        where, params = active.where()
        clause = f" WHERE {where}" if where else ""
        sql = (
            f"SELECT * FROM {self.table}{clause}"
            f" ORDER BY created_at {active.order_clause()}, id {active.order_clause()}"
            " LIMIT ? OFFSET ?"
        )
        rows = self.fetch_all(sql, [*params, active.limit, active.offset])
        return [self.to_model(row) for row in rows]

    def get(self, submission_id: str) -> Submission | None:
        """Return a submission by identifier."""
        row = self.fetch_one(f"SELECT * FROM {self.table} WHERE id = ?", (submission_id,))
        return self.to_model(row) if row is not None else None

    def find_duplicate(self, challenge_id: str, digest: str) -> Submission | None:
        """Return an existing submission with the same challenge and digest."""
        row = self.fetch_one(
            f"SELECT * FROM {self.table} WHERE challenge_id = ? AND flag_digest = ? LIMIT 1",
            (challenge_id, digest),
        )
        return self.to_model(row) if row is not None else None

    def create(self, submission: Submission) -> Submission:
        """Insert a submission and return the persisted record."""
        self.execute(
            f"""
            INSERT INTO {self.table}
                (id, challenge_id, member_id, flag_cipher, status, attempts,
                 created_at, completed_at, error, flag_digest, next_attempt_at, accepted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._values(submission),
        )
        return submission

    def update(self, submission: Submission) -> Submission:
        """Persist the mutable fields of a submission."""
        self.execute(
            f"""
            UPDATE {self.table}
            SET flag_cipher = ?, status = ?, attempts = ?, completed_at = ?, error = ?,
                flag_digest = ?, next_attempt_at = ?, accepted = ?
            WHERE id = ?
            """,
            (
                submission.flag_cipher,
                submission.status.value,
                submission.attempts,
                format_datetime(submission.completed_at),
                submission.error,
                submission.flag_digest,
                format_datetime(submission.next_attempt_at),
                int(submission.accepted),
                submission.id,
            ),
        )
        return submission

    def delete(self, submission_id: str) -> bool:
        """Delete a submission; returns whether a row was removed."""
        return self.execute(f"DELETE FROM {self.table} WHERE id = ?", (submission_id,)) > 0

    def count_matching(self, filters: SubmissionFilters | None = None) -> int:
        """Return the number of submissions matching the filters."""
        active = filters or SubmissionFilters()
        where, params = active.where()
        clause = f" WHERE {where}" if where else ""
        value = self.fetch_value(f"SELECT COUNT(*) FROM {self.table}{clause}", params, 0)
        return int(value or 0)

    def retry_queue(self, now: datetime | None = None, limit: int = 100) -> list[Submission]:
        """Return pending submissions whose backoff window has elapsed."""
        moment = format_datetime(now if now is not None else utcnow())
        rows = self.fetch_all(
            f"""
            SELECT * FROM {self.table}
            WHERE status IN ('queued', 'retrying')
              AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
            ORDER BY created_at ASC, id ASC
            LIMIT ?
            """,
            (moment, limit),
        )
        return [self.to_model(row) for row in rows]

    def pending_count(self) -> int:
        """Return the number of submissions still awaiting processing."""
        value = self.fetch_value(
            f"SELECT COUNT(*) FROM {self.table} WHERE status IN ('queued', 'retrying')",
            (),
            0,
        )
        return int(value or 0)

    def status_counts(self) -> dict[str, int]:
        """Return the number of submissions in each status."""
        rows = self.fetch_all(f"SELECT status, COUNT(*) AS total FROM {self.table} GROUP BY status")
        return {str(row["status"]): int(row["total"]) for row in rows}

    def aggregate(self) -> SubmissionStats:
        """Compute the full aggregate used by the statistics cards."""
        rows = self.fetch_all(
            f"""
            SELECT member_id,
                   COUNT(*) AS total,
                   SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) AS accepted,
                   SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) AS rejected,
                   SUM(CASE WHEN status IN ('queued', 'retrying', 'validating')
                            THEN 1 ELSE 0 END) AS pending,
                   SUM(attempts) AS attempts,
                   SUM(CASE WHEN attempts > 1 THEN 1 ELSE 0 END) AS retries
            FROM {self.table}
            GROUP BY member_id
            ORDER BY member_id ASC
            """
        )
        members: list[MemberSubmissionStats] = []
        total = accepted = attempts = retries = 0
        for row in rows:
            member_total = int(row["total"] or 0)
            member_accepted = int(row["accepted"] or 0)
            members.append(
                MemberSubmissionStats(
                    member_id=str(row["member_id"]),
                    total=member_total,
                    accepted=member_accepted,
                    rejected=int(row["rejected"] or 0),
                    pending=int(row["pending"] or 0),
                )
            )
            total += member_total
            accepted += member_accepted
            attempts += int(row["attempts"] or 0)
            retries += int(row["retries"] or 0)
        return SubmissionStats(
            total=total,
            by_status=self.status_counts(),
            by_member=tuple(members),
            attempts=attempts,
            accepted=accepted,
            retries=retries,
        )

    @staticmethod
    def _values(submission: Submission) -> tuple[Any, ...]:
        """Return the ordered insert values of a submission."""
        return (
            submission.id,
            submission.challenge_id,
            submission.member_id,
            submission.flag_cipher,
            submission.status.value,
            submission.attempts,
            format_datetime(submission.created_at),
            format_datetime(submission.completed_at),
            submission.error,
            submission.flag_digest,
            format_datetime(submission.next_attempt_at),
            int(submission.accepted),
        )


class ValidationRuleRepository(BaseRepository):
    """Persistence operations for :class:`ValidationRule` records."""

    table = "v3_validation_rules"

    @staticmethod
    def to_model(row: sqlite3.Row) -> ValidationRule:
        """Map a database row onto the domain model."""
        data = row_to_dict(row)
        return ValidationRule(
            id=str(data["id"]),
            name=str(data["name"]),
            pattern=str(data["pattern"]),
            description=str(data.get("description") or ""),
            enabled=_bool(data.get("enabled", 1)),
            priority=int(data.get("priority", 100)),
            kind=RuleKind.parse(str(data.get("kind", RuleKind.FORMAT.value))),
        )

    def list_rules(self, *, enabled_only: bool = False) -> list[ValidationRule]:
        """Return rules ordered by priority."""
        where = "WHERE enabled = 1" if enabled_only else ""
        rows = self.fetch_all(f"SELECT * FROM {self.table} {where} ORDER BY priority ASC, id ASC")
        return [self.to_model(row) for row in rows]

    def get(self, rule_id: str) -> ValidationRule | None:
        """Return a rule by identifier."""
        row = self.fetch_one(f"SELECT * FROM {self.table} WHERE id = ?", (rule_id,))
        return self.to_model(row) if row is not None else None

    def create(self, rule: ValidationRule) -> ValidationRule:
        """Insert a validation rule."""
        self.execute(
            f"""
            INSERT INTO {self.table} (id, name, pattern, description, enabled, priority, kind)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            self._values(rule),
        )
        return rule

    def update(self, rule: ValidationRule) -> ValidationRule:
        """Update every mutable column of a validation rule."""
        self.execute(
            f"""
            UPDATE {self.table}
            SET name = ?, pattern = ?, description = ?, enabled = ?, priority = ?, kind = ?
            WHERE id = ?
            """,
            (
                rule.name,
                rule.pattern,
                rule.description,
                int(rule.enabled),
                rule.priority,
                rule.kind.value,
                rule.id,
            ),
        )
        return rule

    def delete(self, rule_id: str) -> bool:
        """Delete a validation rule."""
        return self.execute(f"DELETE FROM {self.table} WHERE id = ?", (rule_id,)) > 0

    def count_rules(self) -> int:
        """Return the number of stored rules."""
        value = self.fetch_value(f"SELECT COUNT(*) FROM {self.table}", (), 0)
        return int(value or 0)

    def ensure_defaults(self) -> int:
        """Insert the built-in rules when the table is empty."""
        if self.count_rules():
            return 0
        for rule in DEFAULT_RULES:
            self.create(rule)
        return len(DEFAULT_RULES)

    @staticmethod
    def _values(rule: ValidationRule) -> tuple[Any, ...]:
        """Return the ordered insert values of a rule."""
        return (
            rule.id,
            rule.name,
            rule.pattern,
            rule.description,
            int(rule.enabled),
            rule.priority,
            rule.kind.value,
        )


class SubmissionPipelineStore:
    """Convenience container bundling both feature repositories."""

    def __init__(self) -> None:
        self.submissions = SubmissionRepository()
        self.rules = ValidationRuleRepository()

    def list_submissions(self, filters: SubmissionFilters | None = None) -> list[Submission]:
        """Return submissions matching the filters."""
        return self.submissions.list_submissions(filters)

    def aggregate(self) -> SubmissionStats:
        """Return the aggregated submission statistics."""
        return self.submissions.aggregate()

    def active_rules(self) -> Sequence[ValidationRule]:
        """Return the enabled validation rules."""
        return self.rules.list_rules(enabled_only=True)
