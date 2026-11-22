"""Business rules for submitting, validating and retrying flags."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.submission_pipeline.models import (
    MAX_FLAG_LENGTH,
    QueueSummary,
    RetryPolicy,
    RuleKind,
    Submission,
    SubmissionFilters,
    SubmissionStats,
    SubmissionStatus,
    ValidationOutcome,
    ValidationRule,
    accepted_outcome,
    cipher_flag,
    expected_flag,
    flag_digest,
    normalize_flag,
    rejected_outcome,
    validate_flag_format,
)
from ctf_team_dashboard.features.submission_pipeline.store import (
    SubmissionPipelineStore,
    SubmissionRepository,
    ValidationRuleRepository,
)
from ctf_team_dashboard.repositories import Repositories


class SubmissionPipelineService:
    """Orchestrate validation, deduplication, processing and retries."""

    def __init__(
        self,
        store: SubmissionPipelineStore | None = None,
        repositories: Repositories | None = None,
    ) -> None:
        self.store = store or SubmissionPipelineStore()
        self.repositories = repositories or Repositories()
        self.submissions: SubmissionRepository = self.store.submissions
        self.rules_repo: ValidationRuleRepository = self.store.rules
        self.rules_repo.ensure_defaults()

    # ------------------------------------------------------------------
    # Submission lifecycle
    # ------------------------------------------------------------------
    def submit(
        self,
        *,
        challenge_id: str,
        member_id: str,
        flag: str,
    ) -> Submission:
        """Validate and enqueue a flag submission.

        Args:
            challenge_id: The challenge being attempted.
            member_id: The member submitting the flag.
            flag: The raw flag as entered by the member.

        Returns:
            The newly created queued submission.

        Raises:
            NotFoundError: When the challenge or member does not exist.
            ValidationError: When the flag fails format validation.
            ConflictError: When the same flag was already submitted for the
                challenge.
        """
        challenge = self.repositories.challenges.get(challenge_id)
        if challenge is None:
            raise NotFoundError(f"Challenge {challenge_id!r} does not exist")
        if self.repositories.members.get(member_id) is None:
            raise NotFoundError(f"Member {member_id!r} does not exist")

        candidate = normalize_flag(flag)
        outcome = validate_flag_format(candidate, self.active_rules())
        if not outcome.accepted:
            raise ValidationError(
                outcome.message,
                details={"code": outcome.code, "rule_id": outcome.rule_id},
            )

        digest = flag_digest(challenge_id, candidate)
        duplicate = self.submissions.find_duplicate(challenge_id, digest)
        if duplicate is not None:
            raise ConflictError(
                "This flag was already submitted for the challenge",
                details={"submission_id": duplicate.id, "status": duplicate.status.value},
            )

        accepted = candidate == expected_flag(challenge.title)
        submission = Submission(
            id=f"sub-{uuid.uuid4().hex[:12]}",
            challenge_id=challenge_id,
            member_id=member_id,
            flag_cipher=cipher_flag(candidate),
            status=SubmissionStatus.QUEUED,
            attempts=0,
            created_at=utcnow(),
            flag_digest=digest,
            accepted=accepted,
        )
        self.submissions.create(submission)
        return submission

    def get_submission(self, submission_id: str) -> Submission:
        """Return a submission or raise :class:`NotFoundError`."""
        submission = self.submissions.get(submission_id)
        if submission is None:
            raise NotFoundError(f"Submission {submission_id!r} does not exist")
        return submission

    def list_submissions(
        self,
        *,
        status: SubmissionStatus | None = None,
        challenge_id: str | None = None,
        member_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
        order: str = "desc",
    ) -> list[Submission]:
        """Return submissions matching the supplied filters."""
        filters = SubmissionFilters(
            status=status,
            challenge_id=challenge_id,
            member_id=member_id,
            limit=limit,
            offset=offset,
            order=order,
        )
        return self.submissions.list_submissions(filters)

    def retry_submission(
        self,
        submission_id: str,
        *,
        flag: str | None = None,
        policy: RetryPolicy | None = None,
        now: datetime | None = None,
    ) -> Submission:
        """Schedule another validation attempt for a rejected submission.

        A corrected flag may be supplied: it is validated and re-digested in
        exactly the same way as a fresh submission, which lets a member fix a
        typo without creating a duplicate queue entry.

        Args:
            submission_id: The rejected submission to retry.
            flag: An optional replacement flag.
            policy: The retry policy controlling the attempt budget and delay.
            now: Optional clock used when scheduling the next attempt.

        Returns:
            The submission in the ``retrying`` state.

        Raises:
            NotFoundError: When the submission does not exist.
            ValidationError: When the status or attempt budget forbids a retry,
                or when a replacement flag is malformed.
            ConflictError: When a replacement flag duplicates another entry.
        """
        submission = self.get_submission(submission_id)
        active = policy or RetryPolicy()
        if not submission.status.is_retryable:
            raise ValidationError(
                f"Only rejected submissions can be retried (status is {submission.status.value})",
                details={"status": submission.status.value},
            )
        if not active.can_retry(submission.attempts):
            raise ValidationError(
                "The retry policy attempt budget is exhausted",
                details={"attempts": submission.attempts, "max_attempts": active.max_attempts},
            )

        updated = submission
        if flag is not None:
            candidate = normalize_flag(flag)
            outcome = validate_flag_format(candidate, self.active_rules())
            if not outcome.accepted:
                raise ValidationError(
                    outcome.message,
                    details={"code": outcome.code, "rule_id": outcome.rule_id},
                )
            digest = flag_digest(submission.challenge_id, candidate)
            duplicate = self.submissions.find_duplicate(submission.challenge_id, digest)
            if duplicate is not None and duplicate.id != submission.id:
                raise ConflictError(
                    "This flag was already submitted for the challenge",
                    details={"submission_id": duplicate.id},
                )
            challenge = self.repositories.challenges.get(submission.challenge_id)
            title = challenge.title if challenge is not None else ""
            updated = submission.with_flag(
                candidate,
                digest=digest,
                accepted=candidate == expected_flag(title),
                error=None,
            )

        scheduled = updated.with_status(
            SubmissionStatus.RETRYING,
            error=None,
            next_attempt_at=active.schedule_after(updated.attempts, now),
        )
        self.submissions.update(scheduled)
        return scheduled

    def process_queue(
        self,
        *,
        now: datetime | None = None,
        limit: int = 100,
    ) -> QueueSummary:
        """Process every due queued or retrying submission.

        Args:
            now: Optional clock, useful for deterministic tests.
            limit: Maximum number of submissions handled in one pass.

        Returns:
            A summary of the pass.
        """
        moment = now if now is not None else utcnow()
        pending_before = self.submissions.pending_count()
        due = self.submissions.retry_queue(moment, limit)
        summary = QueueSummary()
        for submission in due:
            validating = submission.with_status(
                SubmissionStatus.VALIDATING,
                attempts=submission.attempts + 1,
                error=None,
                next_attempt_at=None,
            )
            self.submissions.update(validating)

            outcome = self._decide(validating)
            final_status = (
                SubmissionStatus.ACCEPTED if outcome.accepted else SubmissionStatus.REJECTED
            )
            completed = validating.with_status(
                final_status,
                error=None if outcome.accepted else outcome.code,
                completed_at=moment,
            )
            self.submissions.update(completed)
            summary = summary.with_processed(outcome)

        return QueueSummary(
            processed=summary.processed,
            accepted=summary.accepted,
            rejected=summary.rejected,
            skipped=pending_before - summary.processed,
            remaining=self.submissions.pending_count(),
            errors=summary.errors,
        )

    def _decide(self, submission: Submission) -> ValidationOutcome:
        """Return the deterministic acceptance decision for a submission."""
        if submission.accepted:
            return accepted_outcome()
        return rejected_outcome(
            "flag_mismatch",
            "The flag did not match the seeded answer for this challenge.",
        )

    # ------------------------------------------------------------------
    # Aggregation and rule management
    # ------------------------------------------------------------------
    def stats(self) -> SubmissionStats:
        """Return queue statistics grouped by status and member."""
        return self.submissions.aggregate()

    def active_rules(self) -> Sequence[ValidationRule]:
        """Return the enabled rules, seeding the defaults on first use."""
        return self.store.active_rules()

    def list_rules(self) -> list[ValidationRule]:
        """Return every configured validation rule."""
        return self.rules_repo.list_rules()

    def get_rule(self, rule_id: str) -> ValidationRule:
        """Return a rule or raise :class:`NotFoundError`."""
        rule = self.rules_repo.get(rule_id)
        if rule is None:
            raise NotFoundError(f"Validation rule {rule_id!r} does not exist")
        return rule

    def create_rule(
        self,
        *,
        name: str,
        pattern: str,
        description: str = "",
        enabled: bool = True,
        priority: int = 100,
        kind: RuleKind = RuleKind.FORMAT,
    ) -> ValidationRule:
        """Add a validation rule.

        Args:
            name: Short rule name shown in validation hints.
            pattern: Regular expression matched against normalised flags.
            description: Hint displayed when the rule rejects a flag.
            enabled: Whether the rule participates in validation.
            priority: Lower values are evaluated first.
            kind: The purpose of the rule.

        Returns:
            The persisted rule.

        Raises:
            ValidationError: When the pattern is not a valid regular expression.
        """
        cleaned = name.strip()
        if not cleaned:
            raise ValidationError("A validation rule needs a name")
        if not pattern.strip():
            raise ValidationError("A validation rule needs a pattern")
        rule = ValidationRule(
            id=f"rule-{uuid.uuid4().hex[:10]}",
            name=cleaned,
            pattern=pattern,
            description=description.strip(),
            enabled=enabled,
            priority=priority,
            kind=kind,
        )
        self.rules_repo.create(rule)
        return rule

    def update_rule(
        self,
        rule_id: str,
        *,
        name: str | None = None,
        pattern: str | None = None,
        description: str | None = None,
        enabled: bool | None = None,
        priority: int | None = None,
    ) -> ValidationRule:
        """Update the mutable properties of a rule."""
        current = self.get_rule(rule_id)
        updated = current.with_changes(
            name=current.name if name is None else name.strip(),
            pattern=current.pattern if pattern is None else pattern,
            description=current.description if description is None else description.strip(),
            enabled=current.enabled if enabled is None else enabled,
            priority=current.priority if priority is None else priority,
        )
        self.rules_repo.update(updated)
        return updated

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule; returns whether a row was removed."""
        return self.rules_repo.delete(rule_id)


def is_seeded_answer(challenge_title: str, flag: str) -> bool:
    """Return whether a normalised flag solves the seeded challenge."""
    return normalize_flag(flag) == expected_flag(challenge_title)


def validate_without_storage(flag: str, rules: Sequence[ValidationRule]) -> ValidationOutcome:
    """Validate a flag without touching persistence (used by the UI hints)."""
    return validate_flag_format(normalize_flag(flag), rules)


MAX_SUBMISSION_FLAG_LENGTH = MAX_FLAG_LENGTH
