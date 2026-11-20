"""HTTP endpoints of the onboarding wizard and guided tour."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ctf_team_dashboard.features.onboarding_tour.models import (
    ChecklistItem as ChecklistItemModel,
)
from ctf_team_dashboard.features.onboarding_tour.models import (
    OnboardingProgress,
    OnboardingStep,
    ProgressSummary,
    SetupChecklist,
    StepState,
    TargetValidation,
    WelcomeNote,
)
from ctf_team_dashboard.features.onboarding_tour.schemas import (
    ChecklistItemRead,
    ChecklistItemUpdate,
    ChecklistRead,
    ChecklistUpdate,
    OnboardingStepRead,
    ProgressRecordRead,
    ProgressSummaryRead,
    ResetResponse,
    ResumeStateRead,
    StepActionResponse,
    TargetCheckRequest,
    TargetCheckResponse,
    WelcomeNoteRead,
)
from ctf_team_dashboard.features.onboarding_tour.service import (
    DEFAULT_USER_ID,
    OnboardingService,
    StepActionResult,
)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


def get_onboarding_service() -> OnboardingService:
    """Dependency returning an onboarding service bound to the current database."""
    return OnboardingService()


OnboardingServiceDep = Annotated[OnboardingService, Depends(get_onboarding_service)]


def _step_read(
    step: OnboardingStep,
    state: StepState | None = None,
    is_current: bool = False,
) -> OnboardingStepRead:
    """Map a domain step onto its API representation."""
    return OnboardingStepRead(
        id=step.id,
        slug=step.slug,
        title=step.title,
        description=step.description,
        target=step.target,
        order=step.order,
        completion_key=step.completion_key,
        kind=step.kind,
        estimated_seconds=step.estimated_seconds,
        required=step.required,
        hint=step.hint,
        icon=step.icon,
        created_at=step.created_at,
        state=state,
        is_current=is_current,
        target_kind=step.target_kind,
        duration_label=step.duration_label,
    )


def _item_read(item: ChecklistItemModel) -> ChecklistItemRead:
    """Map a checklist item onto its API representation."""
    return ChecklistItemRead(
        id=item.id,
        label=item.label,
        detail=item.detail,
        target=item.target,
        done=item.done,
        status=item.status,
    )


def _checklist_read(checklist: SetupChecklist) -> ChecklistRead:
    """Map a checklist onto its API representation."""
    items = checklist.items()
    return ChecklistRead(
        user_id=checklist.user_id,
        items=[_item_read(item) for item in items],
        completed=sum(1 for item in items if item.done),
        total=len(items),
        percent=checklist.percent,
        updated_at=checklist.updated_at,
    )


def _record_read(record: OnboardingProgress) -> ProgressRecordRead:
    """Map a progress record onto its API representation."""
    return ProgressRecordRead(
        user_id=record.user_id,
        step_id=record.step_id,
        completed_at=record.completed_at,
        skipped=record.skipped,
        status_label=record.status_label,
    )


def _note_read(note: WelcomeNote) -> WelcomeNoteRead:
    """Map a welcome note onto its API representation."""
    return WelcomeNoteRead(
        id=note.id,
        user_id=note.user_id,
        title=note.title,
        body=note.body,
        tone=note.tone.value,
        word_count=note.word_count,
        reading_seconds=note.reading_seconds,
        created_at=note.created_at,
    )


def _summary_read(summary: ProgressSummary, note: WelcomeNote) -> ProgressSummaryRead:
    """Map an aggregate summary onto its API representation."""
    current = summary.next_step
    current_id = current.id if current is not None else ""
    states = {step.id: state for step, state in summary.step_states}
    return ProgressSummaryRead(
        user_id=summary.user_id,
        status=summary.status,
        total=summary.total,
        completed=summary.completed_count,
        skipped=summary.skipped_count,
        remaining=summary.remaining_count,
        percent=summary.percent,
        checklist_percent=summary.checklist_percent,
        steps=[
            _step_read(step, states.get(step.id), step.id == current_id) for step in summary.steps
        ],
        records=[_record_read(record) for record in summary.progress],
        next_step=_step_read(current) if current is not None else None,
        checklist=_checklist_read(summary.checklist),
        resume=ResumeStateRead(
            can_resume=summary.resume.can_resume,
            next_step_slug=summary.resume.next_step_slug,
            percent=summary.resume.percent,
            last_activity_at=summary.resume.last_activity_at,
            message=summary.resume.message,
        ),
        welcome_note=_note_read(note),
    )


def _action_read(result: StepActionResult) -> StepActionResponse:
    """Map a step action result onto its API representation."""
    return StepActionResponse(
        step=_step_read(result.step),
        message=result.message,
        finished=result.finished,
        progress=_summary_read(result.summary, result.welcome),
    )


@router.get("/steps", response_model=list[OnboardingStepRead])
def list_steps(
    service: OnboardingServiceDep,
    user_id: str = DEFAULT_USER_ID,
) -> list[OnboardingStepRead]:
    """Return every wizard step with the state derived for one user."""
    return [
        _step_read(view.step, view.state, view.is_current) for view in service.list_steps(user_id)
    ]


@router.get("/progress", response_model=ProgressSummaryRead)
def get_progress(
    service: OnboardingServiceDep,
    user_id: str = DEFAULT_USER_ID,
) -> ProgressSummaryRead:
    """Return the full progress summary of one user."""
    summary = service.get_summary(user_id)
    return _summary_read(summary, service.welcome_note(user_id))


@router.get("/next", response_model=OnboardingStepRead | None)
def get_next_step(
    service: OnboardingServiceDep,
    user_id: str = DEFAULT_USER_ID,
) -> OnboardingStepRead | None:
    """Return the next actionable step, when the tour is still in progress."""
    step = service.next_step(user_id)
    return _step_read(step) if step is not None else None


@router.post("/steps/{step_id}/complete", response_model=StepActionResponse)
def complete_step(
    step_id: str,
    service: OnboardingServiceDep,
    user_id: str = DEFAULT_USER_ID,
) -> StepActionResponse:
    """Mark a step complete, ticking any linked checklist item."""
    return _action_read(service.complete_step(step_id, user_id))


@router.post("/steps/{step_id}/skip", response_model=StepActionResponse)
def skip_step(
    step_id: str,
    service: OnboardingServiceDep,
    user_id: str = DEFAULT_USER_ID,
) -> StepActionResponse:
    """Skip a step so the journey advances without awarding completion."""
    return _action_read(service.skip_step(step_id, user_id))


@router.get("/checklist", response_model=ChecklistRead)
def get_checklist(
    service: OnboardingServiceDep,
    user_id: str = DEFAULT_USER_ID,
) -> ChecklistRead:
    """Return the setup checklist of one user."""
    return _checklist_read(service.checklist(user_id))


@router.put("/checklist", response_model=ChecklistRead)
def put_checklist(
    payload: ChecklistUpdate,
    service: OnboardingServiceDep,
    user_id: str = DEFAULT_USER_ID,
) -> ChecklistRead:
    """Replace the setup checklist of one user."""
    items = [
        ChecklistItemModel(
            id=item.id,
            label=item.label,
            detail=item.detail,
            target=item.target,
            done=item.done,
        )
        for item in payload.items
    ]
    return _checklist_read(service.replace_checklist(items, user_id))


@router.put("/checklist/{item_id}", response_model=ChecklistRead)
def put_checklist_item(
    item_id: str,
    payload: ChecklistItemUpdate,
    service: OnboardingServiceDep,
    user_id: str = DEFAULT_USER_ID,
) -> ChecklistRead:
    """Tick or untick a single checklist item."""
    return _checklist_read(service.set_checklist_item(item_id, payload.done, user_id))


@router.post("/reset", response_model=ResetResponse)
def reset_onboarding(
    service: OnboardingServiceDep,
    user_id: str = DEFAULT_USER_ID,
) -> ResetResponse:
    """Clear progress and restore the default checklist."""
    result = service.reset(user_id)
    return ResetResponse(
        user_id=result.user_id,
        removed_progress=result.removed_progress,
        removed_checklist=result.removed_checklist,
        message=result.message,
        checklist=_checklist_read(result.checklist),
        progress=_summary_read(result.summary, service.welcome_note(result.user_id)),
    )


@router.post("/targets/check", response_model=TargetCheckResponse)
def check_target(
    payload: TargetCheckRequest,
    service: OnboardingServiceDep,
) -> TargetCheckResponse:
    """Validate a spotlight target selector against the safe grammar."""
    validated: TargetValidation = service.check_target(payload.target)
    return TargetCheckResponse(
        target=payload.target,
        valid=validated.valid,
        kind=validated.kind,
        reason=validated.reason,
        label=validated.label,
    )
