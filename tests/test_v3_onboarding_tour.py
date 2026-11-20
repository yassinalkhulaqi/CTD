"""Tests for the onboarding wizard, guided tour and setup checklist."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.onboarding_tour import SCHEMA_SQL
from ctf_team_dashboard.features.onboarding_tour.models import (
    ChecklistItem,
    OnboardingProgress,
    OnboardingStep,
    ResumeState,
    SetupChecklist,
    StepState,
    WelcomeTone,
    build_resume_state,
    build_welcome_note,
    completion_percent,
    derive_next_step,
    derive_step_states,
    dump_checklist_items,
    ordered_steps,
    parse_checklist_items,
    summarise_progress,
    unique_steps,
    validate_catalogue,
    validate_target,
)
from ctf_team_dashboard.features.onboarding_tour.service import (
    DEFAULT_CHECKLIST_ITEMS,
    DEFAULT_STEPS,
    OnboardingService,
)
from ctf_team_dashboard.features.onboarding_tour.store import (
    ChecklistRepository,
    OnboardingProgressRepository,
    OnboardingStepRepository,
)


def step(
    step_id: str,
    order: int,
    slug: str | None = None,
    *,
    required: bool = True,
    completion_key: str | None = None,
) -> OnboardingStep:
    """Build a minimal catalogue step for pure logic tests."""
    return OnboardingStep(
        id=step_id,
        slug=slug or step_id,
        title=f"Step {order}",
        description="A test step",
        target=f"#{step_id}",
        order=order,
        completion_key=completion_key or f"key.{step_id}",
        required=required,
    )


def record(step_id: str, skipped: bool = False) -> OnboardingProgress:
    """Build a progress record for pure logic tests."""
    return OnboardingProgress(
        user_id="tester",
        step_id=step_id,
        completed_at=utcnow(),
        skipped=skipped,
    )


# ----------------------------------------------------------------------
# Pure domain logic
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("completed", "total", "expected"),
    [
        (0, 0, 0),
        (3, 0, 0),
        (0, 4, 0),
        (1, 4, 25),
        (2, 3, 66),
        (3, 3, 100),
        (9, 4, 100),
        (-1, 4, 0),
    ],
)
def test_completion_percent_is_clamped(completed: int, total: int, expected: int) -> None:
    """Percentages clamp to 0-100 and an empty total reports zero."""
    assert completion_percent(completed, total) == expected


@pytest.mark.parametrize(
    ("target", "kind"),
    [
        ("#onboarding-welcome", "anchor"),
        ("/settings", "route"),
        ("/api/onboarding/steps", "route"),
        ('[data-tour="challenge-board"]', "selector"),
        ("tour:submit-flag", "token"),
    ],
)
def test_validate_target_accepts_safe_forms(target: str, kind: str) -> None:
    """Only the four supported selector grammars are accepted."""
    result = validate_target(target)
    assert result.valid is True
    assert result.kind == kind
    assert result.label == kind


@pytest.mark.parametrize(
    "target",
    ["", "   ", "javascript:alert(1)", "<script>", "#Bad Target", "https://example.com"],
)
def test_validate_target_rejects_unsafe_forms(target: str) -> None:
    """Arbitrary selectors and URLs are rejected with a reason."""
    result = validate_target(target)
    assert result.valid is False
    assert result.reason


def test_step_helpers_expose_derived_values() -> None:
    """Steps expose ordinals, target kinds and flexible reference matching."""
    item = step("step-two", 2)
    assert item.ordinal == "2nd"
    assert item.with_order(3).ordinal == "3rd"
    assert item.target_kind == "anchor"
    assert item.duration_label == "1 min"
    assert item.matches("step-two") is True
    assert item.matches("key.step-two") is True
    assert item.matches("missing") is False
    assert step("step-one", 1).ordinal == "1st"
    assert step("step-eleven", 11).ordinal == "11th"


def test_ordered_and_unique_steps_normalise_the_catalogue() -> None:
    """Ordering is stable and duplicate slugs keep their first occurrence."""
    first = step("a", 2)
    duplicate = step("other", 1, slug="a")
    last = step("c", 9)
    ordered = ordered_steps([last, first, duplicate])
    assert [item.id for item in ordered] == ["other", "a", "c"]
    unique = unique_steps([last, first, duplicate])
    assert [item.id for item in unique] == ["other", "c"]


def test_derive_next_step_honours_completion_and_skip() -> None:
    """Skipped steps advance the journey without becoming the next step."""
    steps = [step("a", 1), step("b", 2), step("c", 3)]
    assert derive_next_step(steps, []) == steps[0]
    assert derive_next_step(steps, [record("a")]) == steps[1]
    assert derive_next_step(steps, [record("a"), record("b", skipped=True)]) == steps[2]
    assert derive_next_step(steps, [record(s.id) for s in steps]) is None


def test_derive_step_states_respects_required_prerequisites() -> None:
    """Optional steps never lock later steps; unresolved required steps do."""
    optional = step("a", 1, required=False)
    required = step("b", 2)
    third = step("c", 3)
    states = {item.id: state for item, state in derive_step_states([optional, required, third], [])}
    assert states["a"] is StepState.ACTIVE
    assert states["b"] is StepState.AVAILABLE
    assert states["c"] is StepState.LOCKED

    resolved = {
        item.id: state
        for item, state in derive_step_states([optional, required, third], [record("a")])
    }
    assert resolved["a"] is StepState.COMPLETE
    assert resolved["b"] is StepState.ACTIVE
    assert resolved["c"] is StepState.LOCKED

    completed = {
        item.id: state
        for item, state in derive_step_states(
            [optional, required, third], [record("a"), record("b")]
        )
    }
    assert completed["c"] is StepState.ACTIVE


def test_validate_catalogue_reports_every_problem() -> None:
    """Catalogue validation records duplicated and malformed steps."""
    assert validate_catalogue([]) == ("The onboarding catalogue is empty",)
    broken = [
        step("a", 1),
        step("b", 1, slug="a", completion_key="key.a"),
        step("c", 0, slug="c"),
    ]
    problems = validate_catalogue(broken)
    assert any("Duplicate step slug" in problem for problem in problems)
    assert any("Duplicate completion key" in problem for problem in problems)
    assert any("Duplicate step order" in problem for problem in problems)
    assert any("non-positive order" in problem for problem in problems)
    assert validate_catalogue(DEFAULT_STEPS) == ()


def test_checklist_serialisation_and_marking() -> None:
    """Checklists survive a JSON round trip and marking is immutable."""
    items = (ChecklistItem("a", "Alpha"), ChecklistItem("b", "Beta"))
    raw = dump_checklist_items(items)
    parsed = parse_checklist_items(raw)
    assert [item.id for item in parsed] == ["a", "b"]
    checklist = SetupChecklist("tester", raw)
    assert checklist.total == 2
    assert checklist.completed == 0
    assert checklist.percent == 0
    updated = checklist.mark("a", True)
    assert updated.completed == 1
    assert updated.percent == 50
    assert updated.get("a").done is True
    assert checklist.completed == 0
    assert updated.mark("a", False).completed == 0
    assert parse_checklist_items('{"not": "a list"}') == ()
    assert parse_checklist_items("[1, null]") == ()
    assert parse_checklist_items("{broken") == ()
    assert parse_checklist_items(None) == ()


def test_progress_record_and_note_helpers() -> None:
    """Progress age and welcome note metrics are derived correctly."""
    now = utcnow()
    old = OnboardingProgress("tester", "a", now - timedelta(seconds=30))
    assert old.is_complete is True
    assert old.state is StepState.COMPLETE
    assert old.status_label == "Completed"
    assert 29 < old.elapsed_seconds(now) < 31
    skipped = OnboardingProgress("tester", "a", now, skipped=True)
    assert skipped.state is StepState.SKIPPED
    assert skipped.status_label == "Skipped"

    summary = summarise_progress("tester", [step("a", 1)], [old])
    note = build_welcome_note(summary)
    assert note.tone is WelcomeTone.SUCCESS
    assert note.word_count > 5
    assert note.reading_seconds >= 1
    assert len(note.preview) <= 120
    fresh = build_welcome_note(summarise_progress("tester", [step("a", 1)], []))
    assert fresh.tone is WelcomeTone.INFO
    partial = build_welcome_note(
        summarise_progress(
            "tester",
            [step("a", 1), step("b", 2)],
            [record("a")],
            SetupChecklist("tester", dump_checklist_items(DEFAULT_CHECKLIST_ITEMS)),
        )
    )
    assert partial.tone is WelcomeTone.TIP
    assert "50%" in partial.body


def test_resume_state_reflects_progress() -> None:
    """Resume state distinguishes fresh, partially done and finished tours."""
    steps = [step("a", 1), step("b", 2)]
    fresh = build_resume_state(steps, [], 0)
    assert isinstance(fresh, ResumeState)
    assert fresh.can_resume is False
    assert fresh.next_step_slug == "a"
    assert fresh.last_activity_at is None

    partial = build_resume_state(steps, [record("a")], 50)
    assert partial.can_resume is True
    assert partial.next_step_slug == "b"
    assert partial.last_activity_at is not None

    finished = build_resume_state(steps, [record("a"), record("b")], 100)
    assert finished.can_resume is False
    assert finished.next_step_slug is None


# ----------------------------------------------------------------------
# Store layer
# ----------------------------------------------------------------------
def test_schema_creates_feature_tables(database: object) -> None:
    """The exported schema script creates all three feature tables."""
    assert "v3_onboarding_steps" in SCHEMA_SQL
    assert "v3_onboarding_progress" in SCHEMA_SQL
    assert "v3_checklists" in SCHEMA_SQL
    names = database.table_names()
    assert {"v3_onboarding_steps", "v3_onboarding_progress", "v3_checklists"} <= names


def test_step_repository_seed_is_idempotent(database: object) -> None:
    """Seeding the catalogue twice never duplicates rows."""
    repository = OnboardingStepRepository()
    assert repository.count() == 0
    assert repository.seed(DEFAULT_STEPS) == len(DEFAULT_STEPS)
    assert repository.seed(DEFAULT_STEPS) == 0
    assert repository.count() == len(DEFAULT_STEPS)
    assert repository.get("step-welcome") is not None
    assert repository.get_by_slug("welcome").id == "step-welcome"
    assert repository.get_by_key("tour.welcome").id == "step-welcome"
    assert repository.find("step-welcome").slug == "welcome"
    assert repository.find("tour.welcome").slug == "welcome"
    assert repository.find("missing") is None
    assert [item.order for item in repository.all_ordered()] == list(range(1, 8))


def test_progress_repository_crud(database: object) -> None:
    """Progress records can be upserted, listed, counted and removed."""
    repository = OnboardingProgressRepository()
    initial = record("step-welcome")
    repository.upsert(initial)
    repository.upsert(record("step-team", skipped=True))
    assert repository.count_for_user("tester") == 2
    assert repository.count_for_user("tester", skipped=True) == 1
    assert repository.count_for_user("tester", skipped=False) == 1
    assert repository.get("tester", "step-welcome").is_complete is True
    assert len(repository.list_for_user("tester")) == 2
    assert repository.latest_for_user("tester") is not None
    repository.upsert(OnboardingProgress("tester", "step-welcome", utcnow(), skipped=True))
    assert repository.get("tester", "step-welcome").skipped is True
    assert repository.delete("tester", "step-welcome") is True
    assert repository.delete("tester", "step-welcome") is False
    assert repository.delete_for_user("tester") == 1
    assert repository.list_for_user("tester") == []


def test_checklist_repository_crud(database: object) -> None:
    """Checklists persist as JSON and expose their item identifiers."""
    repository = ChecklistRepository()
    assert repository.get("tester") is None
    checklist = SetupChecklist("tester", dump_checklist_items(DEFAULT_CHECKLIST_ITEMS))
    repository.save(checklist)
    assert repository.get("tester").total == len(DEFAULT_CHECKLIST_ITEMS)
    assert len(repository.item_ids("tester")) == len(DEFAULT_CHECKLIST_ITEMS)
    repository.save(checklist.mark("tour.welcome", True))
    assert repository.get("tester").completed == 1
    assert repository.delete("tester") is True
    assert repository.delete("tester") is False


# ----------------------------------------------------------------------
# Service layer
# ----------------------------------------------------------------------
def test_service_seeds_catalogue_and_default_checklist(database: object) -> None:
    """First use seeds both the step catalogue and the default checklist."""
    service = OnboardingService()
    views = service.list_steps("alice")
    assert len(views) == len(DEFAULT_STEPS)
    assert views[0].step.slug == "welcome"
    assert views[0].state is StepState.ACTIVE
    assert views[0].is_current is True
    assert views[-1].state is StepState.LOCKED
    assert service.checklist("alice").total == len(DEFAULT_CHECKLIST_ITEMS)
    assert service.ensure_catalogue() == 0


def test_service_complete_advances_and_syncs_checklist(database: object) -> None:
    """Completing a step advances the tour and ticks its linked item."""
    service = OnboardingService()
    result = service.complete_step("welcome", "alice")
    assert result.finished is False
    assert result.summary.percent > 0
    assert result.summary.completed_count == 1
    assert result.summary.next_step.slug == "profile"
    assert service.checklist("alice").get("tour.welcome").done is True
    assert service.next_step("alice").slug == "profile"


def test_service_skip_advances_without_credit(database: object) -> None:
    """A skipped step unlocks the next one but earns no completion credit."""
    service = OnboardingService()
    result = service.skip_step("welcome", "alice")
    assert result.summary.percent == 0
    assert result.summary.skipped_count == 1
    assert result.summary.next_step.slug == "profile"
    assert service.checklist("alice").get("tour.welcome").done is False


def test_service_complete_overrides_a_previous_skip(database: object) -> None:
    """Changing your mind about a skipped step awards credit on completion."""
    service = OnboardingService()
    service.skip_step("welcome", "alice")
    result = service.complete_step("welcome", "alice")
    assert result.summary.skipped_count == 0
    assert result.summary.completed_count == 1
    assert result.summary.next_step.slug == "profile"


def test_service_complete_raises_on_conflicts_and_missing_steps(database: object) -> None:
    """Duplicate completions and unknown steps raise typed domain errors."""
    service = OnboardingService()
    service.complete_step("welcome", "alice")
    with pytest.raises(ConflictError, match="already complete"):
        service.complete_step("welcome", "alice")
    with pytest.raises(NotFoundError, match="does not exist"):
        service.complete_step("not-a-step", "alice")


def test_service_skip_raises_on_conflicts(database: object) -> None:
    """A resolved step cannot be skipped a second time."""
    service = OnboardingService()
    service.skip_step("welcome", "alice")
    with pytest.raises(ConflictError, match="already been resolved"):
        service.skip_step("welcome", "alice")
    service.complete_step("workspace", "alice")
    with pytest.raises(ConflictError, match="already been resolved"):
        service.skip_step("step-workspace", "alice")


def test_service_replace_checklist_validates_input(database: object) -> None:
    """Checklist replacement rejects duplicates, blanks and oversized lists."""
    service = OnboardingService()
    items = [ChecklistItem("one", "First"), ChecklistItem("two", "Second")]
    saved = service.replace_checklist(items, "alice")
    assert saved.total == 2
    assert [item.id for item in service.checklist("alice").items()] == ["one", "two"]
    with pytest.raises(ValidationError, match="Duplicate checklist item"):
        service.replace_checklist(
            [ChecklistItem("one", "First"), ChecklistItem("one", "Again")], "alice"
        )
    with pytest.raises(ValidationError, match="need an id and a label"):
        service.replace_checklist([ChecklistItem("one", "  ")], "alice")
    with pytest.raises(ValidationError, match="more than 50 items"):
        service.replace_checklist(
            [ChecklistItem(f"item-{index}", "Label") for index in range(51)], "alice"
        )


def test_service_toggles_checklist_items(database: object) -> None:
    """Single items can be ticked and unticked, unknown ones are rejected."""
    service = OnboardingService()
    updated = service.set_checklist_item("tour.welcome", True, "alice")
    assert updated.get("tour.welcome").done is True
    assert service.set_checklist_item("tour.welcome", False, "alice").completed == 0
    with pytest.raises(NotFoundError, match="Checklist item"):
        service.set_checklist_item("unknown", True, "alice")


def test_service_reset_clears_progress_and_restores_checklist(database: object) -> None:
    """Reset removes progress and recreates the default checklist."""
    service = OnboardingService()
    service.complete_step("welcome", "alice")
    service.set_checklist_item("tour.welcome", True, "alice")
    result = service.reset("alice")
    assert result.removed_progress == 1
    assert result.removed_checklist is True
    assert result.summary.percent == 0
    assert result.summary.next_step.slug == "welcome"
    assert result.checklist.completed == 0
    assert result.checklist.total == len(DEFAULT_CHECKLIST_ITEMS)


def test_service_resume_and_target_validation(database: object) -> None:
    """Resume state and target validation are available through the service."""
    service = OnboardingService()
    assert service.resume_state("alice").can_resume is False
    service.complete_step("welcome", "alice")
    assert service.resume_state("alice").can_resume is True
    assert service.welcome_note("alice").tone is WelcomeTone.TIP
    assert service.check_target("tour:submit-flag").kind == "token"
    with pytest.raises(ValidationError, match="Targets must be"):
        service.check_target("javascript:alert(1)")


def test_progress_is_isolated_per_user(database: object) -> None:
    """Completing a step for one user leaves another user untouched."""
    service = OnboardingService()
    service.complete_step("welcome", "alice")
    assert service.get_summary("alice").completed_count == 1
    assert service.get_summary("bob").completed_count == 0
    assert service.next_step("bob").slug == "welcome"


# ----------------------------------------------------------------------
# HTTP API
# ----------------------------------------------------------------------
def test_api_lists_steps_with_derived_states(client: TestClient) -> None:
    """GET /steps returns the ordered catalogue with state annotations."""
    response = client.get("/api/onboarding/steps", params={"user_id": "alice"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 7
    assert payload[0]["slug"] == "welcome"
    assert payload[0]["state"] == "active"
    assert payload[0]["is_current"] is True
    assert payload[0]["target_kind"] == "anchor"
    assert payload[0]["duration_label"] == "45s"
    assert payload[-1]["state"] == "locked"


def test_api_progress_lifecycle(client: TestClient) -> None:
    """Progress can be read, advanced through completion and read again."""
    initial = client.get("/api/onboarding/progress", params={"user_id": "alice"})
    assert initial.status_code == 200
    assert initial.json()["status"] == "not-started"
    assert initial.json()["percent"] == 0

    action = client.post("/api/onboarding/steps/welcome/complete", params={"user_id": "alice"})
    assert action.status_code == 200
    body = action.json()
    assert body["step"]["slug"] == "welcome"
    assert body["finished"] is False
    assert body["progress"]["completed"] == 1
    assert body["progress"]["next_step"]["slug"] == "profile"

    updated = client.get("/api/onboarding/progress", params={"user_id": "alice"})
    assert updated.json()["status"] == "in-progress"
    assert updated.json()["checklist"]["completed"] == 1
    assert updated.json()["resume"]["can_resume"] is True
    assert updated.json()["welcome_note"]["tone"] == "tip"


def test_api_skips_a_step(client: TestClient) -> None:
    """POST /skip advances the tour without incrementing completion."""
    response = client.post("/api/onboarding/steps/welcome/skip", params={"user_id": "alice"})
    assert response.status_code == 200
    progress = response.json()["progress"]
    assert progress["skipped"] == 1
    assert progress["completed"] == 0
    assert progress["next_step"]["slug"] == "profile"


def test_api_step_error_paths(client: TestClient) -> None:
    """Unknown steps return 404 and duplicate actions return 409."""
    missing = client.post("/api/onboarding/steps/missing/complete")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"

    client.post("/api/onboarding/steps/welcome/complete")
    duplicate = client.post("/api/onboarding/steps/welcome/complete")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict"


def test_api_checklist_read_replace_and_toggle(client: TestClient) -> None:
    """The checklist supports reading, full replacement and single toggles."""
    initial = client.get("/api/onboarding/checklist", params={"user_id": "alice"})
    assert initial.status_code == 200
    assert initial.json()["total"] == len(DEFAULT_CHECKLIST_ITEMS)

    replaced = client.put(
        "/api/onboarding/checklist",
        params={"user_id": "alice"},
        json={"items": [{"id": "custom", "label": "Custom task", "done": False}]},
    )
    assert replaced.status_code == 200
    assert replaced.json()["items"][0]["id"] == "custom"
    assert replaced.json()["percent"] == 0

    toggled = client.put(
        "/api/onboarding/checklist/custom",
        params={"user_id": "alice"},
        json={"done": True},
    )
    assert toggled.status_code == 200
    assert toggled.json()["percent"] == 100
    assert toggled.json()["items"][0]["status"] == "Done"


def test_api_checklist_rejects_invalid_payloads(client: TestClient) -> None:
    """Malformed checklist updates surface as 422 or 409 responses."""
    duplicate = client.put(
        "/api/onboarding/checklist",
        json={
            "items": [
                {"id": "same", "label": "One"},
                {"id": "same", "label": "Two"},
            ]
        },
    )
    assert duplicate.status_code == 422

    invalid = client.put("/api/onboarding/checklist", json={"items": [{"id": "x", "label": ""}]})
    assert invalid.status_code == 422

    missing = client.put("/api/onboarding/checklist/missing", json={"done": True})
    assert missing.status_code == 404


def test_api_next_and_target_validation(client: TestClient) -> None:
    """The next-step and target-validation helpers are exposed over HTTP."""
    nxt = client.get("/api/onboarding/next", params={"user_id": "alice"})
    assert nxt.status_code == 200
    assert nxt.json()["slug"] == "welcome"

    valid = client.post("/api/onboarding/targets/check", json={"target": "#hero"})
    assert valid.status_code == 200
    assert valid.json() == {
        "target": "#hero",
        "valid": True,
        "kind": "anchor",
        "reason": "element id",
        "label": "anchor",
    }

    invalid = client.post("/api/onboarding/targets/check", json={"target": "javascript:alert(1)"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"


def test_api_reset_restores_initial_state(client: TestClient) -> None:
    """POST /reset clears progress for the requested user only."""
    client.post("/api/onboarding/steps/welcome/complete", params={"user_id": "alice"})
    response = client.post("/api/onboarding/reset", params={"user_id": "alice"})
    assert response.status_code == 200
    body = response.json()
    assert body["removed_progress"] == 1
    assert body["progress"]["percent"] == 0
    assert body["progress"]["status"] == "not-started"
    assert body["checklist"]["completed"] == 0
    assert body["progress"]["next_step"]["slug"] == "welcome"


def test_api_serves_users_independently(client: TestClient) -> None:
    """Two users never share progress when queried through the API."""
    client.post("/api/onboarding/steps/welcome/complete", params={"user_id": "alice"})
    alice = client.get("/api/onboarding/progress", params={"user_id": "alice"}).json()
    bob = client.get("/api/onboarding/progress", params={"user_id": "bob"}).json()
    assert alice["completed"] == 1
    assert bob["completed"] == 0
    assert bob["next_step"]["slug"] == "welcome"
