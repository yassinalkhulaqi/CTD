"""Business rules for the onboarding wizard and guided tour."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.onboarding_tour.models import (
    ChecklistItem,
    OnboardingProgress,
    OnboardingStep,
    ProgressSummary,
    ResumeState,
    SetupChecklist,
    StepKind,
    StepState,
    TargetValidation,
    WelcomeNote,
    build_resume_state,
    build_welcome_note,
    derive_next_step,
    dump_checklist_items,
    summarise_progress,
    validate_catalogue,
    validate_target,
)
from ctf_team_dashboard.features.onboarding_tour.store import (
    ChecklistRepository,
    OnboardingProgressRepository,
    OnboardingStepRepository,
)

DEFAULT_USER_ID = "demo-user"
MAX_CHECKLIST_ITEMS = 50

DEFAULT_STEPS: tuple[OnboardingStep, ...] = (
    OnboardingStep(
        id="step-welcome",
        slug="welcome",
        title="Welcome aboard",
        description=(
            "Meet your workspace. This tour highlights the surfaces you will use every event."
        ),
        target="#onboarding-welcome",
        order=1,
        completion_key="tour.welcome",
        kind=StepKind.WELCOME,
        estimated_seconds=45,
        hint="Read the welcome note, then continue when you are ready.",
        icon="sparkles",
    ),
    OnboardingStep(
        id="step-profile",
        slug="profile",
        title="Set up your profile",
        description="Choose a display name so teammates recognise your solves.",
        target="/settings",
        order=2,
        completion_key="tour.profile",
        kind=StepKind.SETUP,
        estimated_seconds=90,
        required=False,
        hint="You can always change this later in settings.",
        icon="user",
    ),
    OnboardingStep(
        id="step-workspace",
        slug="workspace",
        title="Explore the challenge board",
        description="Challenges are grouped by lifecycle state and category.",
        target='[data-tour="challenge-board"]',
        order=3,
        completion_key="tour.workspace",
        kind=StepKind.GUIDE,
        estimated_seconds=120,
        hint="Open a challenge card to see its description and hints.",
        icon="layout",
    ),
    OnboardingStep(
        id="step-first-flag",
        slug="first-flag",
        title="Submit your first flag",
        description="Flags are checked instantly and attributed to your team.",
        target="tour:submit-flag",
        order=4,
        completion_key="tour.first_flag",
        kind=StepKind.GUIDE,
        estimated_seconds=60,
        hint="Flag format is CTF{...}.",
        icon="flag",
    ),
    OnboardingStep(
        id="step-scoreboard",
        slug="scoreboard",
        title="Read the scoreboard",
        description="See live points, penalties and rank movement.",
        target="/analytics",
        order=5,
        completion_key="tour.scoreboard",
        kind=StepKind.GUIDE,
        estimated_seconds=60,
        required=False,
        hint="Scores refresh whenever a solve is recorded.",
        icon="chart",
    ),
    OnboardingStep(
        id="step-team",
        slug="team",
        title="Meet the roster",
        description="Check who is online and which roles your teammates hold.",
        target="#team-roster",
        order=6,
        completion_key="tour.team",
        kind=StepKind.GUIDE,
        estimated_seconds=45,
        hint="Presence updates in real time.",
        icon="users",
    ),
    OnboardingStep(
        id="step-review",
        slug="review",
        title="Review and finish",
        description="Your checklist is ready. Revisit any step from the stepper.",
        target="/onboarding",
        order=7,
        completion_key="tour.review",
        kind=StepKind.REVIEW,
        estimated_seconds=30,
        required=False,
        hint="Resetting the tour never deletes your notes or solves.",
        icon="check",
    ),
)

DEFAULT_CHECKLIST_ITEMS: tuple[ChecklistItem, ...] = (
    ChecklistItem("tour.welcome", "Read the welcome note", "Start with the basics"),
    ChecklistItem("profile_display_name", "Choose a display name", "Settings → profile"),
    ChecklistItem("tour.workspace", "Open the challenge board", "Browse at least one category"),
    ChecklistItem("tour.first_flag", "Submit a practice flag", "Flags are case sensitive"),
    ChecklistItem("enable_notifications", "Enable notifications", "Optional but useful"),
    ChecklistItem("tour.team", "Meet your teammates", "Say hello in the roster"),
)


@dataclass(frozen=True, slots=True)
class StepView:
    """A catalogue step enriched with its state for one user."""

    step: OnboardingStep
    state: StepState
    is_current: bool

    @property
    def is_resolved(self) -> bool:
        """Return whether the step has been completed or skipped."""
        return self.state in (StepState.COMPLETE, StepState.SKIPPED)

    @property
    def is_interactive(self) -> bool:
        """Return whether the user may act on the step right now."""
        return self.state in (StepState.ACTIVE, StepState.AVAILABLE)


@dataclass(frozen=True, slots=True)
class StepActionResult:
    """The outcome of completing or skipping a step."""

    step: OnboardingStep
    summary: ProgressSummary
    welcome: WelcomeNote
    message: str

    @property
    def finished(self) -> bool:
        """Return whether this action completed the whole tour."""
        return self.summary.is_finished


@dataclass(frozen=True, slots=True)
class ResetResult:
    """The outcome of resetting a user's onboarding state."""

    user_id: str
    removed_progress: int
    removed_checklist: bool
    checklist: SetupChecklist
    summary: ProgressSummary
    message: str


class OnboardingService:
    """Coordinate the catalogue, progress records and setup checklist."""

    def __init__(
        self,
        steps: OnboardingStepRepository | None = None,
        progress: OnboardingProgressRepository | None = None,
        checklists: ChecklistRepository | None = None,
    ) -> None:
        self.steps = steps or OnboardingStepRepository()
        self.progress = progress or OnboardingProgressRepository()
        self.checklists = checklists or ChecklistRepository()

    def ensure_catalogue(self) -> int:
        """Validate and seed the default catalogue, returning inserted rows."""
        problems = validate_catalogue(DEFAULT_STEPS)
        if problems:
            raise ValidationError(
                "The onboarding catalogue is invalid", details={"problems": list(problems)}
            )
        return self.steps.seed(DEFAULT_STEPS)

    def _ensure_checklist(self, user_id: str) -> SetupChecklist:
        """Return a user's checklist, creating the default one on first use."""
        existing = self.checklists.get(user_id)
        if existing is not None:
            return existing
        initial = SetupChecklist(
            user_id=user_id, items_json=dump_checklist_items(DEFAULT_CHECKLIST_ITEMS)
        )
        return self.checklists.save(initial)

    def resolve_step(self, reference: str) -> OnboardingStep:
        """Resolve a step reference or raise :class:`NotFoundError`."""
        self.ensure_catalogue()
        step = self.steps.find(reference)
        if step is None:
            raise NotFoundError(f"Onboarding step {reference!r} does not exist")
        return step

    def list_steps(self, user_id: str = DEFAULT_USER_ID) -> tuple[StepView, ...]:
        """Return every step with its derived state for a user."""
        summary = self.get_summary(user_id)
        current = summary.next_step
        current_id = current.id if current is not None else ""
        return tuple(
            StepView(step=step, state=state, is_current=step.id == current_id)
            for step, state in summary.step_states
        )

    def get_summary(self, user_id: str = DEFAULT_USER_ID) -> ProgressSummary:
        """Return the complete progress summary for a user."""
        self.ensure_catalogue()
        checklist = self._ensure_checklist(user_id)
        steps = self.steps.all_ordered()
        progress = self.progress.list_for_user(user_id)
        return summarise_progress(user_id, steps, progress, checklist)

    def next_step(self, user_id: str = DEFAULT_USER_ID) -> OnboardingStep | None:
        """Return the next actionable step for a user."""
        self.ensure_catalogue()
        return derive_next_step(self.steps.all_ordered(), self.progress.list_for_user(user_id))

    def resume_state(self, user_id: str = DEFAULT_USER_ID) -> ResumeState:
        """Return the resume banner state for a user."""
        summary = self.get_summary(user_id)
        return build_resume_state(summary.steps, summary.progress, summary.percent)

    def welcome_note(self, user_id: str = DEFAULT_USER_ID) -> WelcomeNote:
        """Generate the contextual welcome note for a user."""
        return build_welcome_note(self.get_summary(user_id))

    def checklist(self, user_id: str = DEFAULT_USER_ID) -> SetupChecklist:
        """Return the setup checklist of a user."""
        return self._ensure_checklist(user_id)

    def _record(self, user_id: str, step: OnboardingStep, skipped: bool) -> OnboardingProgress:
        """Write a progress record using a fresh UTC timestamp."""
        return OnboardingProgress(
            user_id=user_id,
            step_id=step.id,
            completed_at=utcnow(),
            skipped=skipped,
        )

    def _sync_checklist(self, user_id: str, step: OnboardingStep) -> None:
        """Tick the checklist item linked to a completed step, when present."""
        checklist = self._ensure_checklist(user_id)
        linked = checklist.get(step.completion_key)
        if linked is None or linked.done:
            return
        self.checklists.save(checklist.mark(step.completion_key, True))

    def complete_step(self, reference: str, user_id: str = DEFAULT_USER_ID) -> StepActionResult:
        """Mark a step complete and advance the journey.

        Args:
            reference: The step identifier, slug or completion key.
            user_id: The user whose progress is updated.

        Returns:
            The action result with a refreshed summary.

        Raises:
            NotFoundError: When the step is unknown.
            ConflictError: When the step has already been completed.
        """
        step = self.resolve_step(reference)
        existing = self.progress.get(user_id, step.id)
        if existing is not None and existing.is_complete:
            raise ConflictError(f"Step {step.slug!r} is already complete")
        self.progress.upsert(self._record(user_id, step, skipped=False))
        self._sync_checklist(user_id, step)
        summary = self.get_summary(user_id)
        return StepActionResult(
            step=step,
            summary=summary,
            welcome=build_welcome_note(summary),
            message=f"Completed step {step.ordinal}: {step.title}.",
        )

    def skip_step(self, reference: str, user_id: str = DEFAULT_USER_ID) -> StepActionResult:
        """Mark a step skipped so later steps unlock without credit.

        Args:
            reference: The step identifier, slug or completion key.
            user_id: The user whose progress is updated.

        Returns:
            The action result with a refreshed summary.

        Raises:
            NotFoundError: When the step is unknown.
            ConflictError: When the step was already resolved.
        """
        step = self.resolve_step(reference)
        existing = self.progress.get(user_id, step.id)
        if existing is not None:
            raise ConflictError(f"Step {step.slug!r} has already been resolved")
        self.progress.upsert(self._record(user_id, step, skipped=True))
        summary = self.get_summary(user_id)
        return StepActionResult(
            step=step,
            summary=summary,
            welcome=build_welcome_note(summary),
            message=f"Skipped step {step.ordinal}: {step.title}.",
        )

    def reset(self, user_id: str = DEFAULT_USER_ID) -> ResetResult:
        """Clear progress and restore the default checklist for a user."""
        removed = self.progress.delete_for_user(user_id)
        removed_checklist = self.checklists.delete(user_id)
        checklist = self._ensure_checklist(user_id)
        summary = self.get_summary(user_id)
        return ResetResult(
            user_id=user_id,
            removed_progress=removed,
            removed_checklist=removed_checklist,
            checklist=checklist,
            summary=summary,
            message="Onboarding progress reset. The tour is ready to start again.",
        )

    def replace_checklist(
        self, items: Iterable[ChecklistItem], user_id: str = DEFAULT_USER_ID
    ) -> SetupChecklist:
        """Replace the checklist of a user with a validated item list.

        Args:
            items: The replacement items.
            user_id: The owning user.

        Returns:
            The persisted checklist.

        Raises:
            ValidationError: When items are malformed, duplicated or too many.
        """
        collected = tuple(items)
        if len(collected) > MAX_CHECKLIST_ITEMS:
            raise ValidationError(f"A checklist cannot hold more than {MAX_CHECKLIST_ITEMS} items")
        seen: set[str] = set()
        for item in collected:
            if not item.id.strip() or not item.label.strip():
                raise ValidationError("Checklist items need an id and a label")
            if item.id in seen:
                raise ValidationError(f"Duplicate checklist item {item.id!r}")
            seen.add(item.id)
        return self.checklists.save(
            SetupChecklist(user_id=user_id, items_json=dump_checklist_items(collected))
        )

    def set_checklist_item(
        self,
        item_id: str,
        done: bool,
        user_id: str = DEFAULT_USER_ID,
        *,
        now: datetime | None = None,
    ) -> SetupChecklist:
        """Tick or untick a single checklist item.

        Args:
            item_id: The identifier of the item.
            done: The desired state.
            user_id: The owning user.
            now: Optional clock override.

        Returns:
            The updated checklist.

        Raises:
            NotFoundError: When the item does not exist.
        """
        checklist = self._ensure_checklist(user_id)
        if checklist.get(item_id) is None:
            raise NotFoundError(f"Checklist item {item_id!r} does not exist")
        return self.checklists.save(
            checklist.mark(item_id, done, now=now if now is not None else utcnow())
        )

    def check_target(self, target: str) -> TargetValidation:
        """Validate a target and raise :class:`ValidationError` when invalid."""
        result = validate_target(target)
        if not result.valid:
            raise ValidationError(result.reason)
        return result


def derive_view_states(states: tuple[StepView, ...]) -> tuple[str, ...]:
    """Return the state value of each step view, handy for analytics logs."""
    return tuple(view.state.value for view in states)
