"""Typed request and response schemas of the onboarding API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ctf_team_dashboard.features.onboarding_tour.models import StepKind, StepState
from ctf_team_dashboard.schemas import ApiModel


class OnboardingStepRead(ApiModel):
    """A wizard step as returned by the API."""

    id: str
    slug: str
    title: str
    description: str
    target: str
    order: int
    completion_key: str
    kind: StepKind
    estimated_seconds: int
    required: bool
    hint: str
    icon: str
    created_at: datetime
    state: StepState | None = None
    is_current: bool = False
    target_kind: str = ""
    duration_label: str = ""


class ProgressRecordRead(ApiModel):
    """A single persisted progress record."""

    user_id: str
    step_id: str
    completed_at: datetime
    skipped: bool
    status_label: str


class ChecklistItemInput(ApiModel):
    """An item supplied by a checklist update request."""

    id: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=160)
    detail: str = Field(default="", max_length=280)
    target: str = Field(default="", max_length=160)
    done: bool = False


class ChecklistItemRead(ApiModel):
    """A checklist item as returned by the API."""

    id: str
    label: str
    detail: str
    target: str
    done: bool
    status: str


class ChecklistRead(ApiModel):
    """A full checklist with derived counters."""

    user_id: str
    items: list[ChecklistItemRead]
    completed: int
    total: int
    percent: int
    updated_at: datetime


class ResumeStateRead(ApiModel):
    """The state of the resume banner."""

    can_resume: bool
    next_step_slug: str | None
    percent: int
    last_activity_at: datetime | None
    message: str


class WelcomeNoteRead(ApiModel):
    """A generated note shown on the wizard landing screen."""

    id: str
    user_id: str
    title: str
    body: str
    tone: str
    word_count: int
    reading_seconds: int
    created_at: datetime


class ProgressSummaryRead(ApiModel):
    """The aggregate progress payload consumed by the wizard."""

    user_id: str
    status: str
    total: int
    completed: int
    skipped: int
    remaining: int
    percent: int
    checklist_percent: int
    steps: list[OnboardingStepRead]
    records: list[ProgressRecordRead]
    next_step: OnboardingStepRead | None
    checklist: ChecklistRead
    resume: ResumeStateRead
    welcome_note: WelcomeNoteRead


class StepActionResponse(ApiModel):
    """Response returned after completing or skipping a step."""

    step: OnboardingStepRead
    message: str
    finished: bool
    progress: ProgressSummaryRead


class ResetResponse(ApiModel):
    """Response returned after resetting onboarding state."""

    user_id: str
    removed_progress: int
    removed_checklist: bool
    message: str
    checklist: ChecklistRead
    progress: ProgressSummaryRead


class ChecklistUpdate(ApiModel):
    """Payload used to replace the full checklist."""

    items: list[ChecklistItemInput] = Field(default_factory=list)


class ChecklistItemUpdate(ApiModel):
    """Payload used to tick a single checklist item."""

    done: bool


class TargetCheckRequest(BaseModel):
    """Payload used to validate a tour target before saving a catalogue."""

    model_config = ConfigDict(extra="forbid")

    target: str = Field(min_length=1, max_length=200)


class TargetCheckResponse(ApiModel):
    """The result of validating a tour target."""

    target: str
    valid: bool
    kind: str
    reason: str
    label: str
