"""Domain entities and pure calculations for the onboarding tour.

The module has no dependency on persistence or HTTP. Every rule that decides
which step comes next, how far a user has progressed or whether a tour target
is well formed lives here so it can be tested without a database.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum

from ctf_team_dashboard.domain.models import ensure_utc, utcnow


class StepKind(str, Enum):
    """The role a step plays in the onboarding journey."""

    WELCOME = "welcome"
    SETUP = "setup"
    GUIDE = "guide"
    REVIEW = "review"


class StepState(str, Enum):
    """The state of a step relative to one user's progress."""

    LOCKED = "locked"
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETE = "complete"
    SKIPPED = "skipped"


class WelcomeTone(str, Enum):
    """The visual tone used by a generated welcome note."""

    INFO = "info"
    SUCCESS = "success"
    TIP = "tip"


@dataclass(frozen=True, slots=True)
class TargetValidation:
    """The outcome of validating a tour target selector."""

    valid: bool
    kind: str
    reason: str

    @property
    def label(self) -> str:
        """Return a short human readable description of the result."""
        return self.kind if self.valid else self.reason


_TARGET_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("anchor", re.compile(r"^#[a-z][a-z0-9-]*$"), "element id"),
    ("route", re.compile(r"^/(?:[a-z0-9-]+/?)*$"), "route path"),
    ("selector", re.compile(r'^\[data-tour="[a-z0-9-]+"\]$'), "tour anchor"),
    ("token", re.compile(r"^tour:[a-z0-9-]+$"), "tour token"),
)


def validate_target(target: str) -> TargetValidation:
    """Validate a tour target.

    Targets are intentionally restricted to four forms so the spotlight tour
    can never inject an arbitrary selector into the DOM: a hash anchor, an
    internal route, a ``data-tour`` attribute selector or a named tour token.

    Args:
        target: The raw target string supplied by a catalogue author.

    Returns:
        A validation result containing the target kind or a rejection reason.
    """
    cleaned = target.strip()
    if not cleaned:
        return TargetValidation(False, "", "A tour target is required")
    for kind, pattern, label in _TARGET_RULES:
        if pattern.fullmatch(cleaned):
            return TargetValidation(True, kind, label)
    return TargetValidation(
        False,
        "",
        'Targets must be a #id, /route, [data-tour="name"] or tour:name token',
    )


@dataclass(frozen=True, slots=True)
class OnboardingStep:
    """A single ordered step of the setup wizard."""

    id: str
    slug: str
    title: str
    description: str
    target: str
    order: int
    completion_key: str
    kind: StepKind = StepKind.GUIDE
    estimated_seconds: int = 60
    required: bool = True
    hint: str = ""
    icon: str = "compass"
    created_at: datetime = field(default_factory=utcnow)

    @property
    def target_validation(self) -> TargetValidation:
        """Return the validation result for this step's target."""
        return validate_target(self.target)

    @property
    def target_kind(self) -> str:
        """Return the recognised kind of the step target, when valid."""
        return self.target_validation.kind

    @property
    def is_welcome(self) -> bool:
        """Return whether the step is the opening welcome step."""
        return self.kind is StepKind.WELCOME

    @property
    def is_optional(self) -> bool:
        """Return whether a user may skip the step without blocking later steps."""
        return not self.required

    @property
    def duration_label(self) -> str:
        """Return a friendly estimate of the time the step takes."""
        if self.estimated_seconds < 60:
            return f"{self.estimated_seconds}s"
        minutes, seconds = divmod(self.estimated_seconds, 60)
        if seconds == 0:
            return f"{minutes} min"
        return f"{minutes} min {seconds}s"

    @property
    def ordinal(self) -> str:
        """Return the one-based order of the step as an ordinal string."""
        value = self.order
        if 10 <= value % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
        return f"{value}{suffix}"

    def matches(self, reference: str) -> bool:
        """Return whether a reference names this step.

        The router accepts a step identifier, its slug or its completion key,
        which keeps deep links readable and API clients flexible.

        Args:
            reference: The value supplied by the caller.

        Returns:
            ``True`` when any of the three identifiers match.
        """
        cleaned = reference.strip()
        return cleaned in {self.id, self.slug, self.completion_key}

    def with_order(self, order: int) -> OnboardingStep:
        """Return a copy positioned at a different order."""
        return replace(self, order=order)


@dataclass(frozen=True, slots=True)
class OnboardingProgress:
    """A user's resolution of one onboarding step."""

    user_id: str
    step_id: str
    completed_at: datetime
    skipped: bool = False

    @property
    def is_complete(self) -> bool:
        """Return whether the step was completed rather than skipped."""
        return not self.skipped

    @property
    def state(self) -> StepState:
        """Return the step state implied by this record."""
        return StepState.SKIPPED if self.skipped else StepState.COMPLETE

    @property
    def status_label(self) -> str:
        """Return a human readable status for timeline displays."""
        return "Skipped" if self.skipped else "Completed"

    def elapsed_seconds(self, now: datetime | None = None) -> float:
        """Return how long ago the step was resolved.

        Args:
            now: Optional clock override, useful for deterministic tests.

        Returns:
            Non-negative seconds since the record was written.
        """
        current = utcnow() if now is None else ensure_utc(now)
        return max(0.0, (current - ensure_utc(self.completed_at)).total_seconds())


@dataclass(frozen=True, slots=True)
class ChecklistItem:
    """One actionable item of the setup checklist."""

    id: str
    label: str
    detail: str = ""
    target: str = ""
    done: bool = False

    @property
    def status(self) -> str:
        """Return the text shown beside the item in the UI."""
        return "Done" if self.done else "To do"

    def toggled(self) -> ChecklistItem:
        """Return a copy with the completion flag inverted."""
        return replace(self, done=not self.done)


def parse_checklist_items(raw: str | None) -> tuple[ChecklistItem, ...]:
    """Parse the JSON payload stored on a checklist row.

    Malformed or unexpected payloads degrade to an empty checklist instead of
    breaking the wizard, because the payload is user editable from the API.

    Args:
        raw: The JSON encoded item list.

    Returns:
        The parsed items in their stored order.
    """
    if not raw:
        return ()
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return ()
    if not isinstance(decoded, list):
        return ()
    items: list[ChecklistItem] = []
    for entry in decoded:
        if not isinstance(entry, dict):
            continue
        item_id = entry.get("id")
        label = entry.get("label")
        if not isinstance(item_id, str) or not isinstance(label, str):
            continue
        if not item_id or not label:
            continue
        detail = entry.get("detail")
        target = entry.get("target")
        items.append(
            ChecklistItem(
                id=item_id,
                label=label,
                detail=detail if isinstance(detail, str) else "",
                target=target if isinstance(target, str) else "",
                done=bool(entry.get("done", False)),
            )
        )
    return tuple(items)


def dump_checklist_items(items: Iterable[ChecklistItem]) -> str:
    """Serialise checklist items into their JSON representation."""
    payload = [
        {
            "id": item.id,
            "label": item.label,
            "detail": item.detail,
            "target": item.target,
            "done": item.done,
        }
        for item in items
    ]
    return json.dumps(payload, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class SetupChecklist:
    """The persisted setup checklist of one user."""

    user_id: str
    items_json: str = "[]"
    updated_at: datetime = field(default_factory=utcnow)

    def items(self) -> tuple[ChecklistItem, ...]:
        """Return the parsed items of this checklist."""
        return parse_checklist_items(self.items_json)

    def get(self, item_id: str) -> ChecklistItem | None:
        """Return one item by identifier, when present."""
        for item in self.items():
            if item.id == item_id:
                return item
        return None

    @property
    def total(self) -> int:
        """Return the number of items on the checklist."""
        return len(self.items())

    @property
    def completed(self) -> int:
        """Return the number of ticked items."""
        return sum(1 for item in self.items() if item.done)

    @property
    def percent(self) -> int:
        """Return the checklist completion percentage."""
        return completion_percent(self.completed, self.total)

    def with_items(
        self, items: Iterable[ChecklistItem], *, now: datetime | None = None
    ) -> SetupChecklist:
        """Return a copy holding a new item list."""
        timestamp = utcnow() if now is None else ensure_utc(now)
        return SetupChecklist(self.user_id, dump_checklist_items(items), timestamp)

    def mark(self, item_id: str, done: bool, *, now: datetime | None = None) -> SetupChecklist:
        """Return a copy with one item marked complete or incomplete.

        Args:
            item_id: The identifier of the item to change.
            done: The desired completion state.
            now: Optional clock override.

        Returns:
            A new checklist; the original value is never mutated.
        """
        updated = tuple(
            replace(item, done=done) if item.id == item_id else item for item in self.items()
        )
        return self.with_items(updated, now=now)


@dataclass(frozen=True, slots=True)
class WelcomeNote:
    """A short note shown when a user resumes or finishes the tour."""

    id: str
    user_id: str
    title: str
    body: str
    tone: WelcomeTone = WelcomeTone.INFO
    created_at: datetime = field(default_factory=utcnow)

    @property
    def word_count(self) -> int:
        """Return the number of whitespace separated words in the note."""
        return len(self.body.split())

    @property
    def reading_seconds(self) -> int:
        """Return an estimated reading time in seconds."""
        return max(1, round(self.word_count / 3.5))

    @property
    def preview(self) -> str:
        """Return a compact one line preview of the note."""
        collapsed = " ".join(self.body.split())
        return collapsed[:120]


@dataclass(frozen=True, slots=True)
class ResumeState:
    """Everything the UI needs to offer a resume action."""

    can_resume: bool
    next_step_slug: str | None
    percent: int
    last_activity_at: datetime | None
    message: str


@dataclass(frozen=True, slots=True)
class ProgressSummary:
    """An aggregated view of one user's onboarding journey."""

    user_id: str
    steps: tuple[OnboardingStep, ...]
    progress: tuple[OnboardingProgress, ...]
    checklist: SetupChecklist

    @property
    def total(self) -> int:
        """Return the number of steps in the catalogue."""
        return len(self.steps)

    @property
    def completed_count(self) -> int:
        """Return the number of completed steps."""
        return sum(1 for record in self.progress if record.is_complete)

    @property
    def skipped_count(self) -> int:
        """Return the number of skipped steps."""
        return sum(1 for record in self.progress if record.skipped)

    @property
    def resolved_count(self) -> int:
        """Return the number of steps that no longer need attention."""
        return len(self.progress)

    @property
    def remaining_count(self) -> int:
        """Return the number of steps still awaiting a decision."""
        return max(0, self.total - self.resolved_count)

    @property
    def percent(self) -> int:
        """Return the percentage of steps that were actually completed."""
        return completion_percent(self.completed_count, self.total)

    @property
    def checklist_percent(self) -> int:
        """Return the completion percentage of the setup checklist."""
        return self.checklist.percent

    @property
    def is_finished(self) -> bool:
        """Return whether every step has been resolved."""
        return self.total > 0 and self.remaining_count == 0

    @property
    def next_step(self) -> OnboardingStep | None:
        """Return the first step that has not been resolved."""
        return derive_next_step(self.steps, self.progress)

    @property
    def step_states(self) -> tuple[tuple[OnboardingStep, StepState], ...]:
        """Return each step paired with its derived state."""
        return derive_step_states(self.steps, self.progress)

    @property
    def resume(self) -> ResumeState:
        """Return the resume banner state for this summary."""
        return build_resume_state(self.steps, self.progress, self.percent)

    @property
    def status(self) -> str:
        """Return a short status label for the progress header."""
        if self.total == 0:
            return "no-catalogue"
        if self.is_finished:
            return "complete"
        if self.completed_count == 0 and self.skipped_count == 0:
            return "not-started"
        return "in-progress"


def completion_percent(completed: int, total: int) -> int:
    """Return a clamped integer percentage.

    Args:
        completed: The number of finished items.
        total: The number of items in total.

    Returns:
        An integer from 0 to 100; an empty catalogue reports zero.
    """
    if total <= 0:
        return 0
    ratio = max(0, min(completed, total)) / total
    return int(ratio * 100)


def ordered_steps(steps: Iterable[OnboardingStep]) -> tuple[OnboardingStep, ...]:
    """Return steps sorted by order and then by slug for stable output."""
    return tuple(sorted(steps, key=lambda step: (step.order, step.slug)))


def unique_steps(steps: Iterable[OnboardingStep]) -> tuple[OnboardingStep, ...]:
    """Return steps with duplicate slugs removed, keeping the lowest order."""
    seen: set[str] = set()
    unique: list[OnboardingStep] = []
    for step in ordered_steps(steps):
        if step.slug in seen:
            continue
        seen.add(step.slug)
        unique.append(step)
    return tuple(unique)


def progress_by_step(progress: Iterable[OnboardingProgress]) -> dict[str, OnboardingProgress]:
    """Index progress records by their step identifier."""
    return {record.step_id: record for record in progress}


def derive_next_step(
    steps: Iterable[OnboardingStep], progress: Iterable[OnboardingProgress]
) -> OnboardingStep | None:
    """Return the first ordered step that has not been resolved.

    Skipped steps are treated as resolved so a user can move past an optional
    step without getting stuck, while skipped steps still do not contribute to
    the completion percentage.

    Args:
        steps: The onboarding catalogue.
        progress: The records already written for a user.

    Returns:
        The next actionable step, or ``None`` when the tour is finished.
    """
    resolved = {record.step_id for record in progress}
    return next((step for step in ordered_steps(steps) if step.id not in resolved), None)


def derive_step_states(
    steps: Iterable[OnboardingStep], progress: Iterable[OnboardingProgress]
) -> tuple[tuple[OnboardingStep, StepState], ...]:
    """Derive the state of every step, honouring required-step prerequisites.

    A step becomes :attr:`StepState.ACTIVE` when it is the next unresolved
    step. Later steps are :attr:`StepState.AVAILABLE` only when every earlier
    *required* step has been resolved; otherwise they remain locked. Earlier
    optional steps never lock the journey.

    Args:
        steps: The onboarding catalogue.
        progress: The records already written for a user.

    Returns:
        Ordered step/state pairs.
    """
    records = progress_by_step(progress)
    ordered = ordered_steps(steps)
    next_step = derive_next_step(ordered, records.values())
    next_id = next_step.id if next_step is not None else ""
    states: list[tuple[OnboardingStep, StepState]] = []
    blocking = False
    for step in ordered:
        record = records.get(step.id)
        if record is not None:
            states.append((step, record.state))
        elif blocking:
            states.append((step, StepState.LOCKED))
        elif step.id == next_id:
            states.append((step, StepState.ACTIVE))
        else:
            states.append((step, StepState.AVAILABLE))
        if step.required and record is None:
            blocking = True
    return tuple(states)


def validate_catalogue(steps: Iterable[OnboardingStep]) -> tuple[str, ...]:
    """Return a list of problems found in a step catalogue.

    Args:
        steps: The catalogue to inspect.

    Returns:
        Zero or more human readable problem descriptions.
    """
    problems: list[str] = []
    catalogue = tuple(steps)
    if not catalogue:
        return ("The onboarding catalogue is empty",)
    slugs: set[str] = set()
    keys: set[str] = set()
    orders: set[int] = set()
    for step in ordered_steps(catalogue):
        if not step.slug.strip():
            problems.append(f"Step {step.id!r} has an empty slug")
        elif step.slug in slugs:
            problems.append(f"Duplicate step slug {step.slug!r}")
        else:
            slugs.add(step.slug)
        if not step.completion_key.strip():
            problems.append(f"Step {step.id!r} has an empty completion key")
        elif step.completion_key in keys:
            problems.append(f"Duplicate completion key {step.completion_key!r}")
        else:
            keys.add(step.completion_key)
        if step.order < 1:
            problems.append(f"Step {step.id!r} has a non-positive order")
        elif step.order in orders:
            problems.append(f"Duplicate step order {step.order}")
        else:
            orders.add(step.order)
        if not step.title.strip():
            problems.append(f"Step {step.id!r} has an empty title")
        target = validate_target(step.target)
        if not target.valid:
            problems.append(f"Step {step.id!r} has an invalid target: {target.reason}")
    return tuple(problems)


def build_resume_state(
    steps: Iterable[OnboardingStep],
    progress: Iterable[OnboardingProgress],
    percent: int,
) -> ResumeState:
    """Build the resume banner state from a catalogue and progress records."""
    records = tuple(progress)
    next_step = derive_next_step(steps, records)
    if not records:
        return ResumeState(
            False,
            next_step.slug if next_step else None,
            percent,
            None,
            "Start the tour when you are ready.",
        )
    last = max(records, key=lambda record: record.completed_at)
    if next_step is None:
        return ResumeState(
            False,
            None,
            percent,
            last.completed_at,
            "You have finished the tour. Nice work!",
        )
    return ResumeState(
        True,
        next_step.slug,
        percent,
        last.completed_at,
        f"Pick up where you left off: {next_step.title}.",
    )


def summarise_progress(
    user_id: str,
    steps: Iterable[OnboardingStep],
    progress: Iterable[OnboardingProgress],
    checklist: SetupChecklist | None = None,
) -> ProgressSummary:
    """Build a progress summary, normalising the catalogue on the way in."""
    resolved = checklist or SetupChecklist(user_id=user_id)
    return ProgressSummary(
        user_id=user_id,
        steps=ordered_steps(steps),
        progress=tuple(progress),
        checklist=resolved,
    )


def build_welcome_note(summary: ProgressSummary) -> WelcomeNote:
    """Generate a contextual welcome note for a progress summary."""
    base = f"note-welcome-{summary.user_id}"
    if summary.status == "complete":
        return WelcomeNote(
            id=base,
            user_id=summary.user_id,
            title="You are all set",
            body=(
                "Your workspace is ready. The challenge board, scoreboard and "
                "team roster are now yours to explore."
            ),
            tone=WelcomeTone.SUCCESS,
        )
    if summary.status == "not-started":
        return WelcomeNote(
            id=base,
            user_id=summary.user_id,
            title="Welcome to the team",
            body=(
                "This short tour shows you where challenges live, how flags are "
                "submitted and where your team's progress is tracked."
            ),
            tone=WelcomeTone.INFO,
        )
    return WelcomeNote(
        id=base,
        user_id=summary.user_id,
        title="Keep going",
        body=(
            f"You are {summary.percent}% through setup. Finish the remaining "
            f"{summary.remaining_count} step(s) to unlock the full dashboard."
        ),
        tone=WelcomeTone.TIP,
    )
