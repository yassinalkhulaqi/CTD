"""Tests for the V3 accessibility toolkit."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.db.engine import Database
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.accessibility.models import (
    A11yIssue,
    ContrastPair,
    FocusDirection,
    FocusOrderEntry,
    FocusTrap,
    KeyboardShortcut,
    Severity,
    canonical_shortcut,
    classify_contrast,
    contrast_ratio,
    find_shortcut_conflicts,
    normalise_color,
    parse_color,
    relative_luminance,
    sort_issues,
    suggest_aria_label,
    suggest_contrast_fix,
    validate_focus_entries,
)
from ctf_team_dashboard.features.accessibility.service import AccessibilityService
from ctf_team_dashboard.features.accessibility.store import (
    IssueRepository,
    ShortcutRepository,
)
from ctf_team_dashboard.repositories import Repositories

UTC = timezone.utc


def make_issue(
    identifier: str,
    severity: Severity = Severity.INFO,
    *,
    path: str = "/challenges",
    resolved: bool = False,
    detected: datetime | None = None,
) -> A11yIssue:
    """Build a deterministic issue for model-level tests."""
    return A11yIssue(
        id=identifier,
        path=path,
        rule_id="label",
        severity=severity,
        description=f"Issue {identifier}",
        suggestion=f"Fix {identifier}",
        detected_at=detected or datetime(2026, 1, 1, tzinfo=UTC),
        resolved_at=datetime(2026, 1, 2, tzinfo=UTC) if resolved else None,
    )


def test_parse_color_accepts_supported_literals() -> None:
    """Hex shorthand, long hex, rgb expressions and names should all parse."""
    assert parse_color("#fff") == (255, 255, 255)
    assert parse_color("#1a2b3c") == (26, 43, 60)
    assert parse_color("rgb(10, 20, 30)") == (10, 20, 30)
    assert parse_color("navy") == (0, 0, 128)
    assert normalise_color("#ABC") == "#aabbcc"


def test_parse_color_rejects_invalid_literals() -> None:
    """Unsupported colour literals should raise a value error."""
    with pytest.raises(ValueError):
        parse_color("not-a-colour")
    with pytest.raises(ValueError):
        parse_color("rgb(300, 0, 0)")


def test_contrast_ratio_and_luminance_follow_wcag() -> None:
    """Black on white should reach the theoretical maximum ratio."""
    assert contrast_ratio("#000000", "#ffffff") == 21.0
    assert contrast_ratio("#ffffff", "#ffffff") == 1.0
    assert relative_luminance("#000000") == 0.0
    assert relative_luminance("#ffffff") == 1.0


def test_contrast_ratio_is_symmetric() -> None:
    """Swapping the two colours must not change the ratio."""
    forward = contrast_ratio("#4f46e5", "#ffffff")
    reverse = contrast_ratio("#ffffff", "#4f46e5")
    assert forward == reverse


def test_classify_contrast_respects_large_text() -> None:
    """Large text uses the relaxed AA and AAA thresholds."""
    assert classify_contrast(4.6).value == "aa"
    assert classify_contrast(4.6, large_text=True).value == "aaa"
    assert classify_contrast(2.9).value == "fail"


def test_contrast_pair_properties_and_suggestions() -> None:
    """A contrast pair should expose computed WCAG properties."""
    pair = ContrastPair("#777777", "#ffffff", path="/settings", label="Helper text")
    assert pair.foreground_hex == "#777777"
    assert pair.background_hex == "#ffffff"
    assert pair.passes_aa is False
    assert pair.passes_aaa is False
    assert "lighten the foreground" in pair.suggestion
    assert pair.display_label == "Helper text"


def test_suggest_contrast_fix_for_passing_pair() -> None:
    """Passing pairs should receive a preservation hint."""
    suggestion = suggest_contrast_fix("#000000", "#ffffff", ratio=21.0)
    assert "meets WCAG AA" in suggestion


def test_issue_resolution_is_idempotent_and_typed() -> None:
    """Resolving an issue produces a new resolved record."""
    issue = make_issue("a11y-1", Severity.CRITICAL)
    resolved = issue.resolve(when=datetime(2026, 1, 3, tzinfo=UTC))
    assert issue.is_resolved is False
    assert resolved.is_resolved is True
    assert resolved.resolved_at == datetime(2026, 1, 3, tzinfo=UTC)
    with pytest.raises(ValueError):
        resolved.resolve()


def test_issue_age_uses_resolution_time() -> None:
    """Issue age should stop growing after resolution."""
    issue = make_issue("a11y-age", resolved=True)
    assert issue.age_seconds == 86400.0


def test_severity_sorting_prioritises_critical_unresolved() -> None:
    """Severity ordering should place critical open issues first."""
    issues = [
        make_issue("info", Severity.INFO),
        make_issue("critical-done", Severity.CRITICAL, resolved=True),
        make_issue("warning", Severity.WARNING),
        make_issue("critical-open", Severity.CRITICAL),
    ]
    ordered = sort_issues(issues)
    assert [issue.id for issue in ordered] == [
        "critical-open",
        "critical-done",
        "warning",
        "info",
    ]


def test_shortcut_canonicalisation_and_display() -> None:
    """Modifier aliases and ordering should be normalised."""
    assert canonical_shortcut("Shift+Control+K") == "ctrl+shift+k"
    assert canonical_shortcut("g g") == "g g"
    shortcut = KeyboardShortcut("s1", "control+shift+p", "Open palette", "global")
    assert shortcut.canonical_keys == "ctrl+shift+p"
    assert shortcut.display_keys == "Ctrl+Shift+P"
    assert shortcut.is_global is True
    assert shortcut.is_chord is False


def test_shortcut_matching_and_scoping() -> None:
    """Shortcuts should match canonical keys and respect scope."""
    shortcut = KeyboardShortcut("s1", "ctrl+k", "Search", "challenges")
    assert shortcut.matches("CONTROL+K", scope="challenges") is True
    assert shortcut.matches("ctrl+k", scope="settings") is False
    assert shortcut.applies_to("global") is False
    assert KeyboardShortcut("s2", "ctrl+k", "Search").applies_to("settings") is True


def test_shortcut_conflict_detection() -> None:
    """Global bindings should conflict with every scope."""
    first = KeyboardShortcut("s1", "ctrl+k", "Search", "global")
    second = KeyboardShortcut("s2", "CONTROL+K", "Palette", "challenges")
    third = KeyboardShortcut("s3", "ctrl+k", "Find", "challenges")
    conflicts = find_shortcut_conflicts([first, second, third])
    assert len(conflicts) == 3
    assert all(conflict.description for conflict in conflicts)


def test_shortcut_parsing_accepts_literal_plus() -> None:
    """The plus key should be representable inside a binding."""
    assert canonical_shortcut("ctrl+plus") == "ctrl++"


def test_focus_trap_wraps_in_both_directions() -> None:
    """Next and previous steps should wrap around the sequence."""
    entries = validate_focus_entries(
        [
            FocusOrderEntry("one", "First", 1),
            FocusOrderEntry("two", "Second", 2),
            FocusOrderEntry("three", "Third", 3),
        ]
    )
    trap = FocusTrap.from_entries(entries)
    assert trap.current is not None
    assert trap.current.id == "one"
    assert trap.next().current is not None
    assert trap.next().current.id == "two"
    assert trap.previous().current is not None
    assert trap.previous().current.id == "three"
    assert trap.move(FocusDirection.NEXT, wrap=False).current is not None
    first = trap.move_to("one")
    assert first.previous(wrap=False).current is not None
    assert first.previous(wrap=False).current.id == "one"


def test_focus_trap_rejects_invalid_state() -> None:
    """An out-of-range focus index should be rejected."""
    entries = validate_focus_entries([FocusOrderEntry("one", "First", 1)])
    with pytest.raises(ValueError):
        FocusTrap(entries, 5)
    with pytest.raises(ValueError):
        FocusTrap.from_entries(entries).move_to("missing")


def test_validate_focus_entries_rejects_duplicates() -> None:
    """Duplicate identifiers and positions should be rejected."""
    with pytest.raises(ValueError):
        validate_focus_entries([FocusOrderEntry("one", "A", 1), FocusOrderEntry("one", "B", 2)])
    with pytest.raises(ValueError):
        validate_focus_entries([FocusOrderEntry("one", "A", 1), FocusOrderEntry("two", "B", 1)])


def test_aria_label_suggestions() -> None:
    """Generic control text should be replaced with descriptive labels."""
    assert suggest_aria_label("Click here", context="scoreboard", action="open") == (
        "Open scoreboard"
    )
    assert suggest_aria_label("Submit flag", context="web challenge") == (
        "Submit flag for web challenge"
    )
    assert suggest_aria_label("   ", context="filters") == "Open filters"


def test_schema_creates_feature_tables(database: Database) -> None:
    """Migration should create every table owned by the feature."""
    names = database.table_names()
    assert "v3_a11y_issues" in names
    assert "v3_shortcuts" in names
    assert "v3_focus_orders" in names


def test_schema_coexists_with_seed_data(seeded: Repositories) -> None:
    """The accessibility schema should not disturb the seeded dataset."""
    assert seeded.teams.count() > 0
    database = seeded.teams.database
    assert "v3_a11y_issues" in database.table_names()


def test_issue_store_round_trip(database: Database) -> None:
    """The store should persist, filter and resolve issues."""
    repository = IssueRepository()
    issue = repository.create(make_issue("stored", Severity.WARNING))
    assert repository.get("stored") == issue
    assert len(repository.list_all(severity=Severity.WARNING)) == 1
    assert repository.list_all(resolved=True) == []
    assert repository.set_resolved("stored", datetime(2026, 2, 1, tzinfo=UTC)) is True
    assert repository.list_all(resolved=True)[0].is_resolved is True
    assert repository.delete("stored") is True


def test_service_record_filter_and_resolve(database: Database) -> None:
    """The service should validate, order and resolve recorded issues."""
    service = AccessibilityService()
    first = service.record_issue(
        path="/challenges",
        rule_id="button-name",
        severity="critical",
        description="Challenge button has no accessible name",
    )
    second = service.record_issue(
        path="/settings",
        rule_id="label",
        severity=Severity.INFO,
        description="Toggle needs a label",
    )
    assert first.suggestion
    assert [issue.id for issue in service.list_issues()] == [first.id, second.id]
    assert len(service.list_issues(path="/settings")) == 1
    resolved = service.resolve_issue(first.id, when=datetime(2026, 3, 1, tzinfo=UTC))
    assert resolved.resolved_at == datetime(2026, 3, 1, tzinfo=UTC)
    with pytest.raises(ConflictError):
        service.resolve_issue(first.id)
    with pytest.raises(NotFoundError):
        service.resolve_issue("missing")


def test_service_validates_issue_fields(database: Database) -> None:
    """Blank issue fields should raise a typed validation error."""
    service = AccessibilityService()
    with pytest.raises(ValidationError):
        service.record_issue(path=" ", rule_id="rule", severity=Severity.INFO, description="text")


def test_service_contrast_audit_records_failures(database: Database) -> None:
    """A failing contrast audit should create graded issues when requested."""
    service = AccessibilityService()
    audit = service.audit_contrast_pairs(
        [
            ContrastPair("#777777", "#ffffff", path="/a", label="Low"),
            ContrastPair("#000000", "#ffffff", path="/b", label="High"),
            ContrastPair("#aaaaaa", "#ffffff", path="/c", label="Mid"),
        ],
        record_issues=True,
    )
    assert len(audit.pairs) == 3
    assert len(audit.failures) == 2
    assert audit.pass_rate == pytest.approx(1 / 3)
    assert len(audit.issues) == 2
    assert audit.issues[0].severity in (Severity.CRITICAL, Severity.WARNING)
    assert audit.worst_pair is not None
    assert audit.average_ratio > 0


def test_service_rejects_invalid_contrast_colour(database: Database) -> None:
    """Invalid colours should fail with a validation error."""
    service = AccessibilityService()
    with pytest.raises(ValidationError):
        service.audit_color_pair(foreground="nope", background="#ffffff")


def test_service_shortcut_registration_and_conflicts(database: Database) -> None:
    """Shortcut registration should reject collisions but allow other scopes."""
    service = AccessibilityService()
    first = service.register_shortcut(keys="Ctrl+K", action="Search", scope="global")
    assert first.keys == "ctrl+k"
    with pytest.raises(ConflictError):
        service.register_shortcut(keys="CONTROL+K", action="Palette", scope="settings")
    scoped = service.register_shortcut(keys="ctrl+shift+k", action="Filter", scope="settings")
    assert scoped.scope == "settings"
    legacy = ShortcutRepository().create(
        KeyboardShortcut("legacy", "CONTROL+K", "Legacy filter", "settings")
    )
    with pytest.raises(ConflictError):
        service.register_shortcut(keys="ctrl+k", action="Duplicate", scope="settings")
    assert len(service.shortcut_conflicts()) == 1
    assert len(service.list_shortcuts(scope="settings")) == 3
    service.delete_shortcut(scoped.id)
    assert {item.id for item in service.list_shortcuts(scope="settings")} == {
        first.id,
        legacy.id,
    }


def test_service_validates_shortcut_expression(database: Database) -> None:
    """Malformed shortcut expressions should be rejected."""
    service = AccessibilityService()
    with pytest.raises(ValidationError):
        service.register_shortcut(keys="ctrl+ctrl+a", action="Broken")


def test_shortcut_store_scope_and_delete(database: Database) -> None:
    """The shortcut store should map and delete scoped records."""
    repository = ShortcutRepository()
    shortcut = repository.create(KeyboardShortcut("shortcut-1", "ALT+SHIFT+M", "Mute", "meetings"))
    assert repository.get("shortcut-1") == shortcut
    assert repository.find_matching("alt+shift+m")[0].id == shortcut.id
    assert "meetings" in repository.scopes()
    assert repository.delete("shortcut-1") is True


def test_service_focus_order_lifecycle(database: Database) -> None:
    """Focus entries can be inserted, reordered, traversed and removed."""
    service = AccessibilityService()
    service.record_focus_entry("Skip link", order=1)
    service.record_focus_entry("Search", order=2)
    middle = service.record_focus_entry("Actions", order=2)
    assert [entry.label for entry in service.list_focus_entries()] == [
        "Skip link",
        "Actions",
        "Search",
    ]
    reorder = [entry.id for entry in reversed(service.list_focus_entries())]
    ordered = service.reorder_focus_entries(reorder)
    assert ordered[0].label == "Search"
    trap = service.advance_focus(direction=FocusDirection.NEXT)
    assert trap.current is not None
    assert trap.current.label == "Actions"
    with pytest.raises(ValidationError):
        service.reorder_focus_entries([reorder[0], reorder[0], reorder[1]])
    service.delete_focus_entry(middle.id)
    assert len(service.list_focus_entries()) == 2
    with pytest.raises(NotFoundError):
        service.delete_focus_entry("missing")


def test_service_stats_aggregate(database: Database) -> None:
    """Statistics should combine issue, shortcut and focus counters."""
    service = AccessibilityService()
    service.record_issue(
        path="/a", rule_id="r1", severity=Severity.CRITICAL, description="Critical"
    )
    resolved = service.record_issue(
        path="/a", rule_id="r2", severity=Severity.INFO, description="Info"
    )
    service.resolve_issue(resolved.id)
    service.register_shortcut(keys="ctrl+j", action="Jump", scope="global")
    service.record_focus_entry("Jump target")
    stats = service.stats()
    assert stats.total_issues == 2
    assert stats.open_issues == 1
    assert stats.resolved_issues == 1
    assert stats.critical_open == 1
    assert stats.shortcut_count == 1
    assert stats.focus_entry_count == 1
    assert stats.resolution_rate == 0.5
    assert stats.risk_score == 5


def test_issue_api_create_filter_and_resolve(client: TestClient) -> None:
    """The issue API should support creation, filtering and resolution."""
    created = client.post(
        "/api/accessibility/issues",
        json={
            "path": "/challenges",
            "rule_id": "aria-role",
            "severity": "warning",
            "description": "Icon button lacks a label",
            "suggestion": "Add aria-label",
        },
    )
    assert created.status_code == 201
    issue = created.json()
    assert issue["severity"] == "warning"
    assert issue["is_resolved"] is False

    filtered = client.get(
        "/api/accessibility/issues", params={"severity": "warning", "resolved": False}
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == [issue["id"]]

    resolved = client.post(f"/api/accessibility/issues/{issue['id']}/resolve")
    assert resolved.status_code == 200
    assert resolved.json()["is_resolved"] is True
    assert resolved.json()["resolved_at"] is not None

    conflict = client.post(f"/api/accessibility/issues/{issue['id']}/resolve")
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "conflict"


def test_issue_api_rejects_invalid_payload(client: TestClient) -> None:
    """Typed schemas should reject blank and unknown values."""
    blank = client.post(
        "/api/accessibility/issues",
        json={
            "path": "",
            "rule_id": "r",
            "severity": "warning",
            "description": "text",
        },
    )
    assert blank.status_code == 422
    unknown = client.post(
        "/api/accessibility/issues",
        json={
            "path": "/a",
            "rule_id": "r",
            "severity": "urgent",
            "description": "text",
        },
    )
    assert unknown.status_code == 422


def test_shortcut_api_conflict_and_delete(client: TestClient) -> None:
    """The shortcut API should surface conflicts through the shared envelope."""
    created = client.post(
        "/api/accessibility/shortcuts",
        json={"keys": "Ctrl+K", "action": "Command palette", "scope": "global"},
    )
    assert created.status_code == 201
    assert created.json()["canonical_keys"] == "ctrl+k"
    assert created.json()["display_keys"] == "Ctrl+K"

    conflict = client.post(
        "/api/accessibility/shortcuts",
        json={"keys": "control+k", "action": "Search", "scope": "settings"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["details"]["keys"] == "ctrl+k"

    listed = client.get("/api/accessibility/shortcuts", params={"scope": "settings"})
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    conflicts = client.get("/api/accessibility/shortcuts/conflicts")
    assert conflicts.json() == []

    deleted = client.delete(f"/api/accessibility/shortcuts/{created.json()['id']}")
    assert deleted.status_code == 204
    assert client.delete(f"/api/accessibility/shortcuts/{created.json()['id']}").status_code == 404


def test_contrast_api_audits_and_can_record(client: TestClient) -> None:
    """The contrast endpoint should compute WCAG values and optionally record."""
    response = client.post(
        "/api/accessibility/contrast",
        json={"foreground": "#777", "background": "#ffffff", "label": "Caption"},
    )
    assert response.status_code == 200
    payload = response.json()
    pair = payload["pairs"][0]
    assert pair["foreground"] == "#777777"
    assert pair["passes_aa"] is False
    assert pair["level"] == "fail"
    assert payload["failures"] == 1
    assert payload["issues"] == []

    recorded = client.post(
        "/api/accessibility/contrast",
        json={
            "foreground": "#777777",
            "background": "white",
            "path": "/accessibility",
            "label": "Caption",
            "record_issue": True,
        },
    )
    assert recorded.status_code == 200
    assert len(recorded.json()["issues"]) == 1


def test_contrast_api_rejects_invalid_colour(client: TestClient) -> None:
    """Invalid colours should be rejected by the request schema."""
    response = client.post(
        "/api/accessibility/contrast",
        json={"foreground": "chartreuse", "background": "#ffffff"},
    )
    assert response.status_code == 422


def test_focus_order_api_and_trap(client: TestClient) -> None:
    """Focus order endpoints should manage the visualised tab sequence."""
    first = client.post("/api/accessibility/focus-orders", json={"label": "Skip link", "order": 1})
    second = client.post("/api/accessibility/focus-orders", json={"label": "Search", "order": 2})
    assert first.status_code == 201
    assert second.status_code == 201

    listed = client.get("/api/accessibility/focus-orders")
    assert [entry["label"] for entry in listed.json()] == ["Skip link", "Search"]
    assert "focus order" in listed.json()[0]["aria_label"]

    reorder = client.post(
        "/api/accessibility/focus-orders/reorder",
        json={"ids": [second.json()["id"], first.json()["id"]]},
    )
    assert reorder.status_code == 200
    assert reorder.json()[0]["label"] == "Search"

    trap = client.get("/api/accessibility/focus-trap", params={"index": 1})
    assert trap.status_code == 200
    assert trap.json()["current_id"] == first.json()["id"]
    assert trap.json()["next_id"] == second.json()["id"]


def test_focus_order_api_rejects_unknown_ids(client: TestClient) -> None:
    """A reorder request must contain every stored identifier exactly once."""
    client.post("/api/accessibility/focus-orders", json={"label": "Only stop"})
    response = client.post("/api/accessibility/focus-orders/reorder", json={"ids": ["missing"]})
    assert response.status_code == 422


def test_aria_suggestion_api(client: TestClient) -> None:
    """The ARIA endpoint should return a descriptive label suggestion."""
    response = client.post(
        "/api/accessibility/aria-suggestions",
        json={"text": "click here", "context": "leaderboard", "action": "open"},
    )
    assert response.status_code == 200
    assert response.json()["suggestion"] == "Open leaderboard"


def test_stats_api_reflects_activity(client: TestClient) -> None:
    """The stats endpoint should reflect mutations performed through the API."""
    client.post(
        "/api/accessibility/issues",
        json={
            "path": "/a",
            "rule_id": "r",
            "severity": "critical",
            "description": "Critical defect",
        },
    )
    client.post(
        "/api/accessibility/shortcuts",
        json={"keys": "ctrl+/", "action": "Show shortcuts"},
    )
    response = client.get("/api/accessibility/stats")
    assert response.status_code == 200
    payload = response.json()
    assert payload["open_issues"] == 1
    assert payload["critical_open"] == 1
    assert payload["shortcut_count"] == 1
    assert payload["severity_counts"]["critical"] == 1
    assert payload["risk_score"] == 5


def test_issue_store_counts_by_severity(database: Database) -> None:
    """Severity counters should track unresolved issues independently."""
    repository = IssueRepository()
    repository.create(make_issue("one", Severity.CRITICAL))
    repository.create(make_issue("two", Severity.WARNING, resolved=True))
    counts = repository.count_by_severity()
    open_counts = repository.count_open_by_severity()
    assert counts["critical"] == 1
    assert counts["warning"] == 1
    assert open_counts["critical"] == 1
    assert open_counts["warning"] == 0
    assert repository.paths() == ["/challenges"]


def test_issue_age_is_non_negative_for_future_detection() -> None:
    """A future detection timestamp should not produce a negative age."""
    issue = make_issue("future", detected=datetime.now(tz=UTC) + timedelta(days=1))
    assert issue.age_seconds == 0.0
