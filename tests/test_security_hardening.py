"""Tests for the security hardening layer."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.config import Settings
from ctf_team_dashboard.errors import RateLimitError
from ctf_team_dashboard.security.audit import (
    AuditAction,
    AuditLog,
    record,
    redact,
)
from ctf_team_dashboard.security.headers import DEFAULT_CSP, SECURITY_HEADERS
from ctf_team_dashboard.security.rate_limit import Bucket, RateLimiter


# ----------------------------------------------------------------------
# Rate limiting
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_bucket_consumes_the_budget() -> None:
    """A bucket should refuse the requests beyond its limit."""
    bucket = Bucket(limit=3, window_seconds=60)
    assert await bucket.consume(now=100.0) is True
    assert await bucket.consume(now=100.0) is True
    assert await bucket.consume(now=100.0) is True
    assert await bucket.consume(now=100.0) is False


@pytest.mark.asyncio
async def test_bucket_expires_the_oldest_entries() -> None:
    """The entries outside of the window should be released."""
    bucket = Bucket(limit=2, window_seconds=10)
    await bucket.consume(now=100.0)
    await bucket.consume(now=101.0)
    assert await bucket.consume(now=105.0) is False
    assert await bucket.consume(now=111.0) is True


@pytest.mark.asyncio
async def test_bucket_reports_the_retry_delay() -> None:
    """The retry delay should point at the end of the window."""
    bucket = Bucket(limit=1, window_seconds=30)
    await bucket.consume(now=100.0)
    assert await bucket.retry_after(now=100.0) == pytest.approx(30.0)
    assert await bucket.retry_after(now=130.0) == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_limiter_isolates_the_callers() -> None:
    """Two callers should not share the same budget."""
    limiter = RateLimiter(limit=1, window_seconds=60)
    await limiter.check("a")
    with pytest.raises(RateLimitError):
        await limiter.check("a")
    await limiter.check("b")


@pytest.mark.asyncio
async def test_limiter_reports_the_retry_after() -> None:
    """The error should carry the delay before the next attempt."""
    limiter = RateLimiter(limit=1, window_seconds=30)
    await limiter.check("a")
    with pytest.raises(RateLimitError) as excinfo:
        await limiter.check("a")
    assert excinfo.value.retry_after > 0
    assert excinfo.value.details["limit"] == 1


@pytest.mark.asyncio
async def test_limiter_reset_clears_the_buckets() -> None:
    """Resetting the limiter should release every budget."""
    limiter = RateLimiter(limit=1, window_seconds=60)
    await limiter.check("a")
    await limiter.reset()
    await limiter.check("a")


# ----------------------------------------------------------------------
# Audit trail
# ----------------------------------------------------------------------
def test_audit_log_records_the_entries() -> None:
    """The audit trail should keep the recorded entries."""
    log = AuditLog(max_entries=10)
    log.record(AuditAction.LOGIN_SUCCESS, actor="nyx")
    log.record(AuditAction.FLAG_SUBMITTED, actor="kestrel", target="challenge-1")
    assert log.size == 2
    assert log.recent(limit=1)[0].action is AuditAction.FLAG_SUBMITTED


def test_audit_log_filters_by_action() -> None:
    """The audit trail should filter the entries by action."""
    log = AuditLog()
    log.record(AuditAction.LOGIN_SUCCESS, actor="nyx")
    log.record(AuditAction.LOGIN_FAILURE, actor="nyx")
    assert len(log.recent(action=AuditAction.LOGIN_FAILURE)) == 1


def test_audit_log_is_bounded() -> None:
    """The audit trail should never grow beyond its maximum size."""
    log = AuditLog(max_entries=5)
    for index in range(20):
        log.record(AuditAction.LOGIN_SUCCESS, actor=f"user-{index}")
    assert log.size == 5


def test_audit_entry_serialises() -> None:
    """An audit entry should be serialisable to JSON."""
    log = AuditLog()
    entry = log.record(AuditAction.TEAM_CREATED, actor="nyx", team_id="team-1")
    assert "team.created" in entry.to_json()
    assert entry.to_dict()["team_id"] == "team-1"


def test_redact_hides_a_sensitive_value() -> None:
    """The redaction should hide the middle of a secret."""
    assert redact("supersecret").endswith("et")
    assert "supersecret" not in redact("supersecret")
    assert redact("") == ""


def test_global_audit_log_is_shared() -> None:
    """The process wide audit trail should be a singleton."""
    from ctf_team_dashboard.security.audit import get_audit_log

    assert get_audit_log() is get_audit_log()


# ----------------------------------------------------------------------
# Headers
# ----------------------------------------------------------------------
def test_security_headers_are_applied(client: TestClient) -> None:
    """Every response should carry the security headers."""
    response = client.get("/api/health")
    for header in SECURITY_HEADERS:
        assert header in response.headers
    assert response.headers["Content-Security-Policy"] == DEFAULT_CSP
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_version_header_is_applied(client: TestClient) -> None:
    """Every response should carry the dashboard version."""
    response = client.get("/api/health")
    assert response.headers["X-Dashboard-Version"]


def test_hsts_can_be_enabled(tmp_path: object) -> None:
    """The strict transport security header should be opt in."""
    from ctf_team_dashboard.app import create_app

    settings = Settings(
        database_path=str(tmp_path) + "/test.sqlite",  # type: ignore[operator]
        enable_hsts=True,
        seed_on_startup=False,
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/health")
        assert "max-age=31536000" in response.headers["Strict-Transport-Security"]


# ----------------------------------------------------------------------
# API
# ----------------------------------------------------------------------
def test_audit_actions_endpoint(client: TestClient) -> None:
    """The action catalogue should be exposed."""
    response = client.get("/api/audit/actions")
    assert response.status_code == 200
    assert len(response.json()["actions"]) > 5


def test_audit_entries_endpoint(client: TestClient) -> None:
    """The audit entries should be exposed."""
    response = client.get("/api/audit/entries")
    assert response.status_code == 200
    assert "entries" in response.json()


def test_audit_log_records_a_login(client: TestClient) -> None:
    """A successful login should be recorded in the audit trail."""
    from ctf_team_dashboard.security.audit import get_audit_log

    client.post(
        "/api/auth/register",
        json={
            "username": "audited",
            "email": "audited@example.com",
            "password": "password123",
        },
    )
    client.post("/api/auth/login", json={"username": "audited", "password": "password123"})
    actions = [entry.action for entry in get_audit_log().recent(limit=50)]
    assert AuditAction.LOGIN_SUCCESS in actions


def test_audit_log_records_a_failed_login(client: TestClient) -> None:
    """A failed login should be recorded in the audit trail."""
    from ctf_team_dashboard.security.audit import get_audit_log

    client.post("/api/auth/login", json={"username": "ghost", "password": "password123"})
    entries = get_audit_log().recent(limit=50)
    assert any(entry.action is AuditAction.LOGIN_FAILURE for entry in entries)


def test_record_helper_writes_to_the_global_log() -> None:
    """The module level helper should write to the shared trail."""
    from ctf_team_dashboard.security.audit import get_audit_log

    before = get_audit_log().size
    record(AuditAction.TEAM_UPDATED, actor="tester")
    assert get_audit_log().size == before + 1
