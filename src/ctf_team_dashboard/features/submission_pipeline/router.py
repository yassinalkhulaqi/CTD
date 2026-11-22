"""HTTP endpoints of the flag submission pipeline."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from ctf_team_dashboard.features.submission_pipeline.models import (
    MemberSubmissionStats,
    QueueSummary,
    Submission,
    SubmissionStats,
    ValidationRule,
)
from ctf_team_dashboard.features.submission_pipeline.schemas import (
    MemberStatsRead,
    ProcessRequest,
    QueueSummaryRead,
    SubmissionCreate,
    SubmissionRead,
    SubmissionRetry,
    SubmissionStatsRead,
    ValidationRuleCreate,
    ValidationRuleRead,
)
from ctf_team_dashboard.features.submission_pipeline.service import (
    SubmissionPipelineService,
)

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


def get_pipeline_service() -> SubmissionPipelineService:
    """Dependency returning the submission pipeline service."""
    return SubmissionPipelineService()


PipelineServiceDep = Annotated[SubmissionPipelineService, Depends(get_pipeline_service)]


def _to_read(submission: Submission) -> SubmissionRead:
    """Map a domain submission onto its API representation."""
    return SubmissionRead(
        id=submission.id,
        challenge_id=submission.challenge_id,
        member_id=submission.member_id,
        flag_cipher=submission.flag_cipher,
        status=submission.status,
        attempts=submission.attempts,
        created_at=submission.created_at,
        completed_at=submission.completed_at,
        error=submission.error,
        accepted=submission.accepted,
        stage_index=submission.stage_index,
        is_pending=submission.is_pending,
    )


def _to_summary(summary: QueueSummary) -> QueueSummaryRead:
    """Map a queue summary onto its API representation."""
    return QueueSummaryRead(
        processed=summary.processed,
        accepted=summary.accepted,
        rejected=summary.rejected,
        skipped=summary.skipped,
        remaining=summary.remaining,
        total=summary.total,
        success_rate=summary.success_rate,
    )


def _to_stats(stats: SubmissionStats) -> SubmissionStatsRead:
    """Map aggregate statistics onto their API representation."""
    members = [
        _to_member_stats(member)
        for member in stats.by_member
        if isinstance(member, MemberSubmissionStats)
    ]
    return SubmissionStatsRead(
        total=stats.total,
        by_status=dict(stats.by_status),
        by_member=members,
        acceptance_rate=stats.acceptance_rate,
        average_attempts=stats.average_attempts,
        pending=stats.pending,
        retries=stats.retries,
        attempts=stats.attempts,
    )


def _to_member_stats(member: MemberSubmissionStats) -> MemberStatsRead:
    """Map per-member statistics onto their API representation."""
    return MemberStatsRead(
        member_id=member.member_id,
        total=member.total,
        accepted=member.accepted,
        rejected=member.rejected,
        pending=member.pending,
        acceptance_rate=member.acceptance_rate,
    )


def _to_rule(rule: ValidationRule) -> ValidationRuleRead:
    """Map a validation rule onto its API representation."""
    return ValidationRuleRead(
        id=rule.id,
        name=rule.name,
        pattern=rule.pattern,
        description=rule.description,
        enabled=rule.enabled,
        priority=rule.priority,
        kind=rule.kind,
    )


@router.post("", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
def submit_flag(payload: SubmissionCreate, service: PipelineServiceDep) -> SubmissionRead:
    """Submit a flag for validation and enqueue it for processing."""
    submission = service.submit(
        challenge_id=payload.challenge_id,
        member_id=payload.member_id,
        flag=payload.flag,
    )
    return _to_read(submission)


@router.get("", response_model=list[SubmissionRead])
def list_submissions(
    service: PipelineServiceDep,
    status_filter: str | None = None,
    challenge_id: str | None = None,
    member_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    order: str = "desc",
) -> list[SubmissionRead]:
    """Return submissions filtered by status, challenge and member."""
    from ctf_team_dashboard.features.submission_pipeline.models import SubmissionStatus

    parsed = SubmissionStatus.parse(status_filter) if status_filter else None
    found = service.list_submissions(
        status=parsed,
        challenge_id=challenge_id,
        member_id=member_id,
        limit=limit,
        offset=offset,
        order=order,
    )
    return [_to_read(submission) for submission in found]


@router.get("/stats", response_model=SubmissionStatsRead)
def get_stats(service: PipelineServiceDep) -> SubmissionStatsRead:
    """Return aggregate pipeline statistics."""
    return _to_stats(service.stats())


@router.post("/process", response_model=QueueSummaryRead)
def process_queue(
    service: PipelineServiceDep,
    payload: ProcessRequest | None = None,
) -> QueueSummaryRead:
    """Process all due submissions and return a run summary."""
    limit = payload.limit if payload is not None else 100
    return _to_summary(service.process_queue(limit=limit))


@router.get("/rules", response_model=list[ValidationRuleRead])
def list_rules(service: PipelineServiceDep) -> list[ValidationRuleRead]:
    """Return the configured validation rules."""
    return [_to_rule(rule) for rule in service.list_rules()]


@router.post("/rules", response_model=ValidationRuleRead, status_code=status.HTTP_201_CREATED)
def create_rule(payload: ValidationRuleCreate, service: PipelineServiceDep) -> ValidationRuleRead:
    """Create a validation rule."""
    rule = service.create_rule(
        name=payload.name,
        pattern=payload.pattern,
        description=payload.description,
        enabled=payload.enabled,
        priority=payload.priority,
        kind=payload.kind,
    )
    return _to_rule(rule)


@router.get("/{submission_id}", response_model=SubmissionRead)
def get_submission(submission_id: str, service: PipelineServiceDep) -> SubmissionRead:
    """Return a single submission."""
    return _to_read(service.get_submission(submission_id))


@router.post("/{submission_id}/retry", response_model=SubmissionRead)
def retry_submission(
    submission_id: str,
    service: PipelineServiceDep,
    payload: SubmissionRetry | None = None,
) -> SubmissionRead:
    """Schedule another validation attempt for a rejected submission."""
    flag = payload.flag if payload is not None else None
    return _to_read(service.retry_submission(submission_id, flag=flag))
