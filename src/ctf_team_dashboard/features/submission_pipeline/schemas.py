"""Typed request and response schemas of the submission pipeline API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ctf_team_dashboard.features.submission_pipeline.models import (
    MAX_FLAG_LENGTH,
    RuleKind,
    SubmissionStatus,
)


class PipelineModel(BaseModel):
    """Base model enabling conversion from the frozen domain objects."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SubmissionCreate(PipelineModel):
    """Payload used to submit a flag."""

    challenge_id: str = Field(min_length=1, max_length=128)
    member_id: str = Field(min_length=1, max_length=128)
    flag: str = Field(min_length=1, max_length=MAX_FLAG_LENGTH)

    @field_validator("challenge_id", "member_id", "flag")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        """Reject values that contain only whitespace."""
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class SubmissionRetry(PipelineModel):
    """Optional payload of a retry request."""

    flag: str | None = Field(default=None, max_length=MAX_FLAG_LENGTH)


class SubmissionRead(PipelineModel):
    """A submission as returned by the API."""

    id: str
    challenge_id: str
    member_id: str
    flag_cipher: str
    status: SubmissionStatus
    attempts: int
    created_at: datetime
    completed_at: datetime | None
    error: str | None
    accepted: bool
    stage_index: int
    is_pending: bool


class ProcessRequest(PipelineModel):
    """Options controlling one queue processing pass."""

    limit: int = Field(default=100, ge=1, le=500)


class QueueSummaryRead(PipelineModel):
    """Outcome of a queue processing pass."""

    processed: int
    accepted: int
    rejected: int
    skipped: int
    remaining: int
    total: int
    success_rate: float


class RetryPolicyRead(PipelineModel):
    """The active retry policy."""

    max_attempts: int
    backoff_seconds: float
    max_backoff_seconds: float


class MemberStatsRead(PipelineModel):
    """Submission statistics for one member."""

    member_id: str
    total: int
    accepted: int
    rejected: int
    pending: int
    acceptance_rate: float


class SubmissionStatsRead(PipelineModel):
    """Aggregated pipeline statistics."""

    total: int
    by_status: dict[str, int]
    by_member: list[MemberStatsRead]
    acceptance_rate: float
    average_attempts: float
    pending: int
    retries: int
    attempts: int


class ValidationRuleCreate(PipelineModel):
    """Payload used to create a validation rule."""

    name: str = Field(min_length=1, max_length=120)
    pattern: str = Field(min_length=1, max_length=512)
    description: str = Field(default="", max_length=400)
    enabled: bool = True
    priority: int = Field(default=100, ge=0, le=10_000)
    kind: RuleKind = RuleKind.FORMAT

    @field_validator("name", "pattern")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        """Reject whitespace-only names and patterns."""
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class ValidationRuleUpdate(PipelineModel):
    """Partial payload used to update a validation rule."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    pattern: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = Field(default=None, max_length=400)
    enabled: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=10_000)


class ValidationRuleRead(PipelineModel):
    """A validation rule as returned by the API."""

    id: str
    name: str
    pattern: str
    description: str
    enabled: bool
    priority: int
    kind: RuleKind


class PipelineErrorDetail(PipelineModel):
    """Structured detail attached to a pipeline error response."""

    code: str | None = None
    rule_id: str | None = None
    submission_id: str | None = None
    status: str | None = None
    attempts: int | None = None
    max_attempts: int | None = None


def error_details(raw: dict[str, Any]) -> PipelineErrorDetail:
    """Convert a domain error's detail mapping into a typed schema."""
    return PipelineErrorDetail(
        code=str(raw.get("code")) if raw.get("code") is not None else None,
        rule_id=str(raw.get("rule_id")) if raw.get("rule_id") is not None else None,
        submission_id=(
            str(raw.get("submission_id")) if raw.get("submission_id") is not None else None
        ),
        status=str(raw.get("status")) if raw.get("status") is not None else None,
        attempts=int(raw["attempts"]) if raw.get("attempts") is not None else None,
        max_attempts=(int(raw["max_attempts"]) if raw.get("max_attempts") is not None else None),
    )
