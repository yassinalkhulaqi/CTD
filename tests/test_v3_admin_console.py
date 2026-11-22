"""Tests for the administration console feature."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.db.engine import Database
from ctf_team_dashboard.domain.enums import MemberRole
from ctf_team_dashboard.domain.models import User, utcnow
from ctf_team_dashboard.errors import ConflictError, ValidationError
from ctf_team_dashboard.features.admin_console.models import (
    AccountStatus,
    ActionFilter,
    AdminAction,
    AdminActionKind,
    CaseFilter,
    CasePriority,
    CaseSort,
    CaseStatus,
    HealthState,
    ModerationCase,
    ReportType,
    TargetType,
    can_transition,
    health_bottleneck,
    health_score,
    health_state,
)
from ctf_team_dashboard.features.admin_console.service import (
    AdminService,
    validate_health_metrics,
)
from ctf_team_dashboard.features.admin_console.store import (
    AccountControlRepository,
    ModerationCaseRepository,
)
from ctf_team_dashboard.repositories.users import UserRepository


@pytest.fixture
def service(database: Database) -> AdminService:
    """Return an administration service bound to the test database."""
    return AdminService()


def make_user(
    database: Database,
    user_id: str,
    role: MemberRole = MemberRole.VIEWER,
    *,
    username: str | None = None,
) -> User:
    """Persist a user used by account-control tests."""
    user = User(
        id=user_id,
        username=username or user_id,
        email=f"{user_id}@example.test",
        password_hash="test-hash",
        role=role,
        is_active=True,
    )
    return UserRepository(database).create(user)


def test_health_score_and_state_calculation() -> None:
    score = health_score(
        database_ok=True,
        api_latency_ms=100,
        cache_hit_ratio=0.95,
        queue_depth=10,
    )
    assert score > 95.0
    assert health_state(score, database_ok=True) is HealthState.HEALTHY

    degraded = health_score(
        database_ok=True,
        api_latency_ms=1200,
        cache_hit_ratio=0.4,
        queue_depth=300,
    )
    assert 40.0 < degraded < 85.0
    assert health_state(degraded, database_ok=True) is HealthState.DEGRADED

    down = health_score(
        database_ok=False,
        api_latency_ms=50,
        cache_hit_ratio=1.0,
        queue_depth=0,
    )
    assert health_state(down, database_ok=False) is HealthState.CRITICAL
    assert (
        health_bottleneck(
            database_ok=False,
            api_latency_ms=50,
            cache_hit_ratio=1.0,
            queue_depth=0,
        )
        == "database"
    )


def test_case_sla_and_transition_rules() -> None:
    created = utcnow() - timedelta(hours=10)
    case = ModerationCase(
        id="case-sla",
        report_type=ReportType.CHEATING,
        target_id="challenge-1",
        reporter_id="member-1",
        priority=CasePriority.HIGH,
        created_at=created,
    )
    assert case.due_at == created + timedelta(hours=8)
    assert case.is_overdue()
    assert case.age_hours() >= 10.0
    assert case.urgency_score() > 30.0

    closed = case.close(CaseStatus.RESOLVED, "confirmed")
    assert closed.is_terminal
    assert not closed.is_overdue()
    assert can_transition(CaseStatus.OPEN, CaseStatus.IN_REVIEW)
    assert not can_transition(CaseStatus.RESOLVED, CaseStatus.OPEN)


def test_case_filter_matches_sorts_and_paginates() -> None:
    now = utcnow()
    urgent = ModerationCase(
        id="case-urgent",
        report_type=ReportType.SECURITY,
        target_id="target-1",
        reporter_id="reporter-1",
        priority=CasePriority.CRITICAL,
        created_at=now - timedelta(hours=3),
    )
    calm = ModerationCase(
        id="case-calm",
        report_type=ReportType.SPAM,
        target_id="target-2",
        reporter_id="reporter-1",
        priority=CasePriority.LOW,
        created_at=now - timedelta(hours=5),
    )
    assigned = urgent.to_in_review("mod-1")
    cases = [calm, assigned]

    spec = CaseFilter(priorities=(CasePriority.CRITICAL,), sort=CaseSort.DUE_ASC)
    assert [case.id for case in spec.apply(cases)] == ["case-urgent"]

    unassigned = CaseFilter(unassigned_only=True)
    assert [case.id for case in unassigned.apply(cases)] == ["case-calm"]

    overdue = CaseFilter(overdue_only=True)
    assert [case.id for case in overdue.apply(cases, now)] == ["case-urgent"]

    searched = CaseFilter(search="target-2")
    assert [case.id for case in searched.apply(cases)] == ["case-calm"]

    page = CaseFilter(limit=1, offset=1, sort=CaseSort.CREATED_ASC)
    assert [case.id for case in page.apply(cases)] == ["case-urgent"]


def test_action_filter_matches_entries() -> None:
    now = utcnow()
    entry = AdminAction(
        id="action-1",
        actor_id="admin",
        target_type=TargetType.CASE,
        target_id="case-1",
        action=AdminActionKind.CASE_OPENED,
        reason="spam report",
        created_at=now,
    )
    assert ActionFilter(actor_id="admin", search="spam").matches(entry)
    assert not ActionFilter(actor_id="other").matches(entry)
    assert not ActionFilter(since=now + timedelta(minutes=1)).matches(entry)


def test_store_case_round_trip_and_counts(service: AdminService, database: Database) -> None:
    case = service.open_case(
        actor_id="admin",
        report_type=ReportType.SPAM,
        target_id="message-42",
        reporter_id="member-7",
        priority=CasePriority.HIGH,
    )
    repository = ModerationCaseRepository(database)
    stored = repository.get(case.id)
    assert stored is not None
    assert stored.report_type is ReportType.SPAM
    assert stored.priority is CasePriority.HIGH
    assert stored.status is CaseStatus.OPEN
    assert repository.count_status(CaseStatus.OPEN) == 1
    assert repository.count_priority(CasePriority.HIGH) == 1

    updated = stored.to_in_review("mod-1")
    repository.save(updated)
    assert repository.get(case.id) is not None
    assert repository.get(case.id).status is CaseStatus.IN_REVIEW


def test_service_case_lifecycle_writes_audit_trail(service: AdminService) -> None:
    case = service.open_case(
        actor_id="admin",
        report_type=ReportType.HARASSMENT,
        target_id="member-9",
        reporter_id="member-3",
    )
    assert case.status is CaseStatus.OPEN

    assigned = service.assign_case(case.id, actor_id="admin", assignee_id="mod-2")
    assert assigned.status is CaseStatus.IN_REVIEW
    assert assigned.assignee_id == "mod-2"

    resolved = service.resolve_case(case.id, actor_id="admin", resolution="warning sent")
    assert resolved.status is CaseStatus.RESOLVED
    assert resolved.resolution == "warning sent"

    actions = service.actions_for_case(case.id)
    assert [entry.action for entry in actions] == [
        AdminActionKind.CASE_RESOLVED,
        AdminActionKind.CASE_ASSIGNED,
        AdminActionKind.CASE_OPENED,
    ]
    assert all(entry.actor_id == "admin" for entry in actions)


def test_service_dismiss_case_blocks_later_transitions(service: AdminService) -> None:
    case = service.open_case(
        actor_id="admin",
        report_type=ReportType.OTHER,
        target_id="target-1",
        reporter_id="reporter-1",
    )
    dismissed = service.dismiss_case(case.id, actor_id="admin", reason="duplicate")
    assert dismissed.status is CaseStatus.DISMISSED

    with pytest.raises(ConflictError):
        service.assign_case(case.id, actor_id="admin", assignee_id="mod-1")
    with pytest.raises(ConflictError):
        service.resolve_case(case.id, actor_id="admin", resolution="too late")


def test_suspension_guards_protect_self_and_admins(
    service: AdminService, database: Database
) -> None:
    viewer = make_user(database, "viewer-1")
    admin = make_user(database, "admin-1", MemberRole.ADMIN)

    with pytest.raises(ValidationError):
        service.set_account_status(
            viewer.id,
            actor_id=viewer.id,
            status=AccountStatus.SUSPENDED,
            reason="self",
        )
    with pytest.raises(ConflictError):
        service.set_account_status(
            admin.id,
            actor_id=viewer.id,
            status=AccountStatus.SUSPENDED,
            reason="admin",
        )


def test_suspend_and_activate_account_updates_auth_state(
    service: AdminService, database: Database
) -> None:
    viewer = make_user(database, "viewer-2")
    suspended = service.set_account_status(
        viewer.id,
        actor_id="admin",
        status=AccountStatus.SUSPENDED,
        reason="abusive messages",
        flags=("repeat_offender",),
    )
    assert suspended.is_suspended
    assert not suspended.auth_active
    assert suspended.is_consistent
    assert "suspended" in suspended.flags

    refreshed = UserRepository(database).get(viewer.id)
    assert refreshed is not None
    assert not refreshed.is_active

    control = AccountControlRepository(database).get(viewer.id)
    assert control is not None
    assert control.has_flag("repeat_offender")

    activated = service.set_account_status(
        viewer.id,
        actor_id="admin",
        status=AccountStatus.ACTIVE,
        reason="appeal accepted",
    )
    assert not activated.is_suspended
    assert activated.auth_active
    assert "suspended" not in activated.flags

    with pytest.raises(ConflictError):
        service.set_account_status(viewer.id, actor_id="admin", status=AccountStatus.ACTIVE)


def test_health_recording_validation_and_stats(service: AdminService) -> None:
    check = service.record_health_check(
        actor_id="admin",
        database_ok=True,
        api_latency_ms=120,
        cache_hit_ratio=0.92,
        queue_depth=4,
    )
    assert check.is_healthy
    assert check.score > 85.0
    assert len(service.list_health()) == 1
    assert service.get_health(check.id).id == check.id

    stats = service.stats()
    assert stats.health_checks == 1
    assert stats.latest_score == check.score
    assert stats.health_state is HealthState.HEALTHY

    with pytest.raises(ValidationError):
        validate_health_metrics(api_latency_ms=50, cache_hit_ratio=1.2, queue_depth=0)
    with pytest.raises(ValidationError):
        service.record_health_check(
            actor_id="admin",
            database_ok=True,
            api_latency_ms=-1,
            cache_hit_ratio=0.5,
            queue_depth=0,
        )


def test_required_tables_are_created(database: Database) -> None:
    names = database.table_names()
    assert {
        "v3_moderation_cases",
        "v3_admin_actions",
        "v3_account_controls",
        "v3_health_checks",
    } <= names


def test_router_opens_and_lists_cases(client: TestClient) -> None:
    response = client.post(
        "/api/admin/cases",
        json={
            "report_type": "cheating",
            "target_id": "challenge-7",
            "reporter_id": "member-1",
            "priority": "high",
        },
    )
    assert response.status_code == 201
    created = response.json()
    assert created["status"] == "open"
    assert created["priority"] == "high"
    assert created["sla_hours"] == 8

    listing = client.get("/api/admin/cases")
    assert listing.status_code == 200
    payload = listing.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == created["id"]


def test_router_assign_resolve_and_dismiss(client: TestClient) -> None:
    def open_case(target_id: str) -> str:
        response = client.post(
            "/api/admin/cases",
            json={
                "report_type": "spam",
                "target_id": target_id,
                "reporter_id": "reporter-1",
            },
        )
        assert response.status_code == 201
        return str(response.json()["id"])

    first = open_case("target-1")
    assigned = client.post(f"/api/admin/cases/{first}/assign", json={"assignee_id": "mod-1"})
    assert assigned.status_code == 200
    assert assigned.json()["status"] == "in_review"
    resolved = client.post(f"/api/admin/cases/{first}/resolve", json={"resolution": "removed spam"})
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    second = open_case("target-2")
    dismissed = client.post(
        f"/api/admin/cases/{second}/dismiss", json={"reason": "not a violation"}
    )
    assert dismissed.status_code == 200
    assert dismissed.json()["status"] == "dismissed"

    conflict = client.post(f"/api/admin/cases/{second}/assign", json={"assignee_id": "mod-1"})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "conflict"


def test_router_case_filters_and_pagination(client: TestClient) -> None:
    for index, priority in enumerate(("low", "high", "critical")):
        response = client.post(
            "/api/admin/cases",
            json={
                "report_type": "security_issue",
                "target_id": f"target-{index}",
                "reporter_id": "reporter-1",
                "priority": priority,
            },
        )
        assert response.status_code == 201

    filtered = client.get(
        "/api/admin/cases",
        params={"priority": "high", "report_type": "security_issue"},
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["priority"] == "high"

    paged = client.get("/api/admin/cases", params={"limit": 2, "offset": 1})
    assert paged.status_code == 200
    assert paged.json()["total"] == 3
    assert len(paged.json()["items"]) == 2

    unassigned = client.get("/api/admin/cases", params={"unassigned": True})
    assert unassigned.json()["total"] == 3


def test_router_account_controls_and_guards(client: TestClient, database: Database) -> None:
    make_user(database, "viewer-3", MemberRole.VIEWER, username="viewer3")
    make_user(database, "root-admin", MemberRole.ADMIN, username="root")

    listing = client.get("/api/admin/account-controls")
    assert listing.status_code == 200
    assert listing.json()["suspended"] == 0
    assert len(listing.json()["items"]) == 2

    suspended = client.post(
        "/api/admin/account-controls",
        json={
            "user_id": "viewer-3",
            "status": "suspended",
            "reason": "spam",
            "flags": ["manual"],
        },
    )
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "suspended"
    assert suspended.json()["auth_active"] is False

    admin_guard = client.post(
        "/api/admin/account-controls",
        json={"user_id": "root-admin", "status": "suspended", "reason": "nope"},
    )
    assert admin_guard.status_code == 409

    missing = client.post(
        "/api/admin/account-controls",
        json={"user_id": "missing-user", "status": "suspended", "reason": "nope"},
    )
    assert missing.status_code == 404


def test_router_audit_query(client: TestClient) -> None:
    response = client.post(
        "/api/admin/cases",
        json={
            "report_type": "harassment",
            "target_id": "member-1",
            "reporter_id": "member-2",
        },
    )
    assert response.status_code == 201
    case_id = response.json()["id"]

    actions = client.get(
        "/api/admin/actions",
        params={"target_type": "case", "action": "case_opened", "search": "member-1"},
    )
    assert actions.status_code == 200
    payload = actions.json()
    assert payload["total"] == 1
    assert payload["items"][0]["target_id"] == case_id
    assert "harassment" in payload["items"][0]["reason"]


def test_router_health_and_error_envelope(client: TestClient) -> None:
    recorded = client.post(
        "/api/admin/health",
        json={
            "database_ok": True,
            "api_latency_ms": 150,
            "cache_hit_ratio": 0.88,
            "queue_depth": 12,
        },
    )
    assert recorded.status_code == 201
    assert recorded.json()["state"] == "healthy"
    assert recorded.json()["score"] > 85

    listing = client.get("/api/admin/health")
    assert listing.status_code == 200
    assert listing.json()["latest"]["id"] == recorded.json()["id"]

    invalid = client.post(
        "/api/admin/health",
        json={
            "database_ok": True,
            "api_latency_ms": 150,
            "cache_hit_ratio": 2.0,
            "queue_depth": 12,
        },
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"


def test_router_stats_endpoint(client: TestClient, database: Database) -> None:
    make_user(database, "viewer-4")
    client.post(
        "/api/admin/cases",
        json={
            "report_type": "cheating",
            "target_id": "target-5",
            "reporter_id": "reporter-5",
            "priority": "critical",
        },
    )
    client.post(
        "/api/admin/health",
        json={
            "database_ok": True,
            "api_latency_ms": 90,
            "cache_hit_ratio": 0.98,
            "queue_depth": 2,
        },
    )
    response = client.get("/api/admin/stats")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_cases"] == 1
    assert payload["critical_cases"] == 1
    assert payload["actions_24h"] >= 2
    assert payload["health_state"] == "healthy"


def test_openapi_exposes_admin_console(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/api/admin/cases" in paths
    assert "/api/admin/account-controls" in paths
    assert "/api/admin/health" in paths
    assert "/api/admin/stats" in paths
