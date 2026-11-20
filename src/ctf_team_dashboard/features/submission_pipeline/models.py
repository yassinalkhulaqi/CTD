"""Domain model of the flag submission pipeline.

The pipeline moves a submission through a small, explicit state machine. Every
rule that decides whether a flag is well formed, unique or correct lives here
as a pure function so it can be exercised without a database or an HTTP server.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any

from ctf_team_dashboard.domain.enums import StrEnum
from ctf_team_dashboard.domain.models import ensure_utc, utcnow
from ctf_team_dashboard.errors import ValidationError

DEFAULT_FLAG_PATTERN = r"^flag\{[a-z0-9_]+\}$"
MAX_FLAG_LENGTH = 256
MAX_ATTEMPTS = 5


class SubmissionStatus(StrEnum):
    """Lifecycle of a submitted flag."""

    QUEUED = "queued"
    VALIDATING = "validating"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    RETRYING = "retrying"

    @property
    def is_terminal(self) -> bool:
        """Return whether no further transition is expected."""
        return self in (SubmissionStatus.ACCEPTED,)

    @property
    def is_pending(self) -> bool:
        """Return whether the submission still needs queue processing."""
        return self in (SubmissionStatus.QUEUED, SubmissionStatus.RETRYING)

    @property
    def is_active(self) -> bool:
        """Return whether work is currently being performed on the submission."""
        return self in (SubmissionStatus.VALIDATING, SubmissionStatus.RETRYING)

    @property
    def is_retryable(self) -> bool:
        """Return whether the status permits a manual retry."""
        return self is SubmissionStatus.REJECTED

    @property
    def stage_index(self) -> int:
        """Return the position of the status in the visual pipeline."""
        return list(SubmissionStatus).index(self)

    @property
    def label(self) -> str:
        """Return a human readable status label."""
        return {
            SubmissionStatus.QUEUED: "Queued",
            SubmissionStatus.VALIDATING: "Validating",
            SubmissionStatus.ACCEPTED: "Accepted",
            SubmissionStatus.REJECTED: "Rejected",
            SubmissionStatus.RETRYING: "Retrying",
        }[self]

    @property
    def tone(self) -> str:
        """Return the semantic colour tone used by the user interface."""
        return {
            SubmissionStatus.QUEUED: "neutral",
            SubmissionStatus.VALIDATING: "info",
            SubmissionStatus.ACCEPTED: "success",
            SubmissionStatus.REJECTED: "danger",
            SubmissionStatus.RETRYING: "warning",
        }[self]


ALLOWED_TRANSITIONS: Mapping[SubmissionStatus, frozenset[SubmissionStatus]] = {
    SubmissionStatus.QUEUED: frozenset({SubmissionStatus.VALIDATING, SubmissionStatus.REJECTED}),
    SubmissionStatus.VALIDATING: frozenset({SubmissionStatus.ACCEPTED, SubmissionStatus.REJECTED}),
    SubmissionStatus.RETRYING: frozenset({SubmissionStatus.VALIDATING, SubmissionStatus.REJECTED}),
    SubmissionStatus.REJECTED: frozenset({SubmissionStatus.RETRYING}),
    SubmissionStatus.ACCEPTED: frozenset(),
}

PIPELINE_STAGES: tuple[SubmissionStatus, ...] = (
    SubmissionStatus.QUEUED,
    SubmissionStatus.VALIDATING,
    SubmissionStatus.ACCEPTED,
)


def can_transition(current: SubmissionStatus, target: SubmissionStatus) -> bool:
    """Return whether the state machine permits a transition.

    Args:
        current: The status the submission is in.
        target: The status it should move to.

    Returns:
        ``True`` when the transition is legal.
    """
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())


def assert_transition(current: SubmissionStatus, target: SubmissionStatus) -> None:
    """Validate a status transition.

    Args:
        current: The status the submission is in.
        target: The status it should move to.

    Raises:
        ValidationError: When the transition is not part of the state machine.
    """
    if not can_transition(current, target):
        detail = f"{current.value} -> {target.value}"
        raise ValidationError(
            f"Illegal submission status transition: {detail}",
            details={"transition": detail},
        )


def normalize_flag(raw: str) -> str:
    """Normalise a raw flag into its canonical comparison form.

    Flags are trimmed, lower-cased, stripped of surrounding quote characters
    and have internal whitespace collapsed into underscores. The result is the
    single representation used for validation, digesting and acceptance.

    Args:
        raw: The flag exactly as entered by a member.

    Returns:
        The canonical form of the flag.
    """
    cleaned = raw.strip().lower()
    while len(cleaned) >= 2 and cleaned[0] in "\"'`" and cleaned[-1] == cleaned[0]:
        cleaned = cleaned[1:-1].strip()
    return re.sub(r"\s+", "_", cleaned)


def flag_digest(challenge_id: str, flag: str) -> str:
    """Return the stable digest used to deduplicate submissions.

    Args:
        challenge_id: The challenge the flag belongs to.
        flag: The normalised flag value.

    Returns:
        A 64 character hexadecimal digest.
    """
    payload = f"{challenge_id.strip().lower()}\x00{normalize_flag(flag)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cipher_flag(flag: str) -> str:
    """Return a display-safe, partially masked representation of a flag.

    The pipeline intentionally avoids persisting plaintext flags in the live
    log. Enough of the prefix and suffix is retained for a member to recognise
    their own submission without exposing the answer to onlookers.

    Args:
        flag: The normalised flag value.

    Returns:
        The masked representation.
    """
    value = normalize_flag(flag)
    if len(value) <= 8:
        return value[:2] + "*" * max(0, len(value) - 2)
    return f"{value[:5]}{'*' * min(10, len(value) - 9)}{value[-4:]}"


def slugify_flag(title: str) -> str:
    """Convert a challenge title into the token used by its seeded flag.

    Args:
        title: The human readable challenge title.

    Returns:
        A lower-case, underscore separated token.
    """
    token = re.sub(r"[^a-z0-9]+", "_", title.strip().lower())
    return token.strip("_") or "challenge"


def expected_flag(title: str) -> str:
    """Return the deterministic flag that solves a seeded challenge.

    Args:
        title: The challenge title.

    Returns:
        The expected ``flag{...}`` value.
    """
    return f"flag{{{slugify_flag(title)}}}"


def backoff_delay(attempt: int, policy: RetryPolicy) -> float:
    """Return the delay before the given attempt is allowed to run.

    Args:
        attempt: The 1-based attempt number that just completed.
        policy: The retry policy controlling the backoff curve.

    Returns:
        A non-negative number of seconds.
    """
    if attempt <= 0:
        return 0.0
    delay = policy.backoff_seconds * float(2 ** (attempt - 1))
    return float(min(policy.max_backoff_seconds, delay))


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Rules controlling how often a failed submission may be retried."""

    max_attempts: int = 3
    backoff_seconds: float = 2.0
    max_backoff_seconds: float = 60.0

    def __post_init__(self) -> None:
        """Reject policies that could never retry or loop forever."""
        if self.max_attempts < 1:
            raise ValidationError("max_attempts must be at least 1")
        if self.backoff_seconds < 0:
            raise ValidationError("backoff_seconds must not be negative")
        if self.max_backoff_seconds < 0:
            raise ValidationError("max_backoff_seconds must not be negative")

    def can_retry(self, attempts: int) -> bool:
        """Return whether another attempt is permitted.

        Args:
            attempts: The number of attempts already consumed.

        Returns:
            ``True`` when the attempt budget is not exhausted.
        """
        return 0 < attempts < self.max_attempts

    def delay_for(self, attempts: int) -> float:
        """Return the backoff delay after ``attempts`` consumed attempts."""
        return backoff_delay(attempts, self)

    def schedule_after(self, attempts: int, now: datetime | None = None) -> datetime:
        """Return the first timestamp at which a retry may be processed."""
        origin = ensure_utc(now if now is not None else utcnow())
        from datetime import timedelta

        return origin + timedelta(seconds=self.delay_for(attempts))

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> RetryPolicy:
        """Build a policy from a mapping of user supplied values."""
        return cls(
            max_attempts=int(raw.get("max_attempts", 3)),
            backoff_seconds=float(raw.get("backoff_seconds", 2.0)),
            max_backoff_seconds=float(raw.get("max_backoff_seconds", 60.0)),
        )


class RuleKind(StrEnum):
    """The purpose of a validation rule."""

    FORMAT = "format"
    ACCEPTANCE = "acceptance"


@dataclass(frozen=True, slots=True)
class ValidationRule:
    """A regular expression rule applied to normalised flags."""

    id: str
    name: str
    pattern: str
    description: str = ""
    enabled: bool = True
    priority: int = 100
    kind: RuleKind = RuleKind.FORMAT

    def __post_init__(self) -> None:
        """Ensure the stored pattern is a valid regular expression."""
        try:
            re.compile(self.pattern)
        except re.error as exc:
            raise ValidationError(
                f"Rule {self.name!r} has an invalid pattern: {exc}",
                details={"rule_id": self.id},
            ) from exc

    def matches(self, flag: str) -> bool:
        """Return whether the normalised flag satisfies the rule."""
        return re.fullmatch(self.pattern, normalize_flag(flag)) is not None

    def hint(self) -> str:
        """Return the hint shown when this rule fails."""
        return self.description or f"Flag must match {self.name}"

    def with_changes(self, **changes: Any) -> ValidationRule:
        """Return a copy with the supplied fields replaced."""
        return replace(self, **changes)


DEFAULT_RULES: tuple[ValidationRule, ...] = (
    ValidationRule(
        id="rule-format",
        name="Flag wrapper",
        pattern=DEFAULT_FLAG_PATTERN,
        description=(
            "Flags use the flag{...} wrapper with lower-case letters, digits and underscores."
        ),
        priority=10,
    ),
    ValidationRule(
        id="rule-length",
        name="Flag length",
        pattern=r"^.{8,256}$",
        description="Flags must be between 8 and 256 characters long.",
        priority=20,
    ),
)


@dataclass(frozen=True, slots=True)
class ValidationOutcome:
    """The result of validating one normalised flag."""

    accepted: bool
    code: str
    message: str
    rule_id: str | None = None

    @property
    def hint(self) -> str:
        """Return the message suited to a validation hint."""
        return self.message

    @property
    def is_format_error(self) -> bool:
        """Return whether the failure was a format problem."""
        return self.code.startswith("format_")


def accepted_outcome() -> ValidationOutcome:
    """Return the outcome of a flag that passed every check."""
    return ValidationOutcome(
        accepted=True,
        code="accepted",
        message="Flag matches the challenge and was accepted.",
    )


def rejected_outcome(code: str, message: str, rule_id: str | None = None) -> ValidationOutcome:
    """Return a failure outcome with the supplied code and message."""
    return ValidationOutcome(accepted=False, code=code, message=message, rule_id=rule_id)


def validate_flag_format(flag: str, rules: Sequence[ValidationRule]) -> ValidationOutcome:
    """Apply every enabled format rule to a flag.

    Args:
        flag: The normalised flag value.
        rules: The rules to apply, evaluated in priority order.

    Returns:
        The first failure, or an accepted outcome when every rule passes.
    """
    candidate = normalize_flag(flag)
    if not candidate:
        return rejected_outcome("format_empty", "A flag is required.")
    if len(candidate) > MAX_FLAG_LENGTH:
        return rejected_outcome(
            "format_too_long", f"Flags must be at most {MAX_FLAG_LENGTH} characters long."
        )
    ordered = sorted((rule for rule in rules if rule.enabled), key=lambda rule: rule.priority)
    for rule in ordered:
        if not rule.matches(candidate):
            return rejected_outcome("format_invalid", rule.hint(), rule.id)
    return accepted_outcome()


@dataclass(frozen=True, slots=True)
class Submission:
    """A flag submitted by a member for a challenge."""

    id: str
    challenge_id: str
    member_id: str
    flag_cipher: str
    status: SubmissionStatus
    attempts: int = 0
    created_at: datetime = field(default_factory=utcnow)
    completed_at: datetime | None = None
    error: str | None = None
    flag_digest: str = ""
    next_attempt_at: datetime | None = None
    accepted: bool = False

    @property
    def is_terminal(self) -> bool:
        """Return whether the submission reached a final state."""
        return self.status.is_terminal

    @property
    def is_pending(self) -> bool:
        """Return whether the submission still needs processing."""
        return self.status.is_pending

    @property
    def is_retryable(self) -> bool:
        """Return whether the status permits a retry."""
        return self.status.is_retryable

    @property
    def stage_index(self) -> int:
        """Return the visual pipeline stage reached by this submission."""
        return self.status.stage_index

    def can_retry(self, policy: RetryPolicy | None = None) -> bool:
        """Return whether the attempt budget allows another retry."""
        active = policy or RetryPolicy()
        return self.status.is_retryable and active.can_retry(self.attempts)

    def is_due(self, now: datetime | None = None) -> bool:
        """Return whether a pending submission has passed its backoff window."""
        if not self.is_pending:
            return False
        if self.next_attempt_at is None:
            return True
        current = ensure_utc(now if now is not None else utcnow())
        return current >= ensure_utc(self.next_attempt_at)

    def elapsed_seconds(self, now: datetime | None = None) -> float:
        """Return the seconds since the submission was created."""
        current = ensure_utc(now if now is not None else utcnow())
        return max(0.0, (current - ensure_utc(self.created_at)).total_seconds())

    def with_status(
        self,
        status: SubmissionStatus,
        *,
        error: str | None = None,
        completed_at: datetime | None = None,
        next_attempt_at: datetime | None = None,
        attempts: int | None = None,
    ) -> Submission:
        """Return a copy advanced to a new status."""
        assert_transition(self.status, status)
        return replace(
            self,
            status=status,
            error=error,
            completed_at=completed_at,
            next_attempt_at=next_attempt_at,
            attempts=self.attempts if attempts is None else attempts,
        )

    def with_flag(
        self,
        flag: str,
        *,
        digest: str,
        accepted: bool,
        error: str | None = None,
    ) -> Submission:
        """Return a copy carrying a replacement flag."""
        return replace(
            self,
            flag_cipher=cipher_flag(flag),
            flag_digest=digest,
            accepted=accepted,
            error=error,
        )


@dataclass(frozen=True, slots=True)
class SubmissionFilters:
    """Optional filters applied when listing submissions."""

    status: SubmissionStatus | None = None
    challenge_id: str | None = None
    member_id: str | None = None
    limit: int = 100
    offset: int = 0
    order: str = "desc"

    def __post_init__(self) -> None:
        """Reject nonsensical pagination values."""
        if self.limit < 1 or self.limit > 500:
            raise ValidationError("limit must be between 1 and 500")
        if self.offset < 0:
            raise ValidationError("offset must not be negative")

    def where(self) -> tuple[str, list[Any]]:
        """Return the SQL fragment and parameters for the filters."""
        clauses: list[str] = []
        params: list[Any] = []
        if self.status is not None:
            clauses.append("status = ?")
            params.append(self.status.value)
        if self.challenge_id:
            clauses.append("challenge_id = ?")
            params.append(self.challenge_id)
        if self.member_id:
            clauses.append("member_id = ?")
            params.append(self.member_id)
        clause = " AND ".join(clauses)
        return clause, params

    def order_clause(self) -> str:
        """Return a safe ORDER BY clause for the requested order."""
        return "ASC" if self.order.lower() == "asc" else "DESC"


@dataclass(frozen=True, slots=True)
class MemberSubmissionStats:
    """Per-member submission totals."""

    member_id: str
    total: int = 0
    accepted: int = 0
    rejected: int = 0
    pending: int = 0

    @property
    def acceptance_rate(self) -> float:
        """Return the fraction of this member's submissions that were accepted."""
        if self.total <= 0:
            return 0.0
        return self.accepted / self.total


@dataclass(frozen=True, slots=True)
class SubmissionStats:
    """Aggregated queue health used by the statistics cards."""

    total: int = 0
    by_status: Mapping[str, int] = field(default_factory=dict)
    by_member: tuple[MemberSubmissionStats, ...] = ()
    attempts: int = 0
    accepted: int = 0
    retries: int = 0

    @property
    def acceptance_rate(self) -> float:
        """Return the accepted fraction of all submissions."""
        if self.total <= 0:
            return 0.0
        return self.accepted / self.total

    @property
    def average_attempts(self) -> float:
        """Return the mean number of attempts across all submissions."""
        if self.total <= 0:
            return 0.0
        return self.attempts / self.total

    @property
    def pending(self) -> int:
        """Return the number of submissions still awaiting processing."""
        return sum(
            self.by_status.get(status.value, 0) for status in SubmissionStatus if status.is_pending
        )


@dataclass(frozen=True, slots=True)
class QueueSummary:
    """Outcome of one pass over the submission queue."""

    processed: int = 0
    accepted: int = 0
    rejected: int = 0
    skipped: int = 0
    remaining: int = 0
    errors: tuple[str, ...] = ()

    @property
    def total(self) -> int:
        """Return the number of submissions that were evaluated."""
        return self.processed + self.skipped

    @property
    def success_rate(self) -> float:
        """Return the accepted fraction of processed submissions."""
        if self.processed <= 0:
            return 0.0
        return self.accepted / self.processed

    def with_processed(self, outcome: ValidationOutcome) -> QueueSummary:
        """Return a summary with one more submission processed."""
        return replace(
            self,
            processed=self.processed + 1,
            accepted=self.accepted + int(outcome.accepted),
            rejected=self.rejected + int(not outcome.accepted),
        )
