"""Typed request and response schemas for the administration API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ctf_team_dashboard.features.admin_console.models import (
    AccountControlView,
    AccountStatus,
    AdminAction,
    AdminActionKind,
    AdminStats,
    CasePriority,
    CaseStatus,
    HealthState,
    ModerationCase,
    ReportType,
    SystemHealth,
    TargetType,
)


class CaseCreateRequest(BaseModel):
    """Payload used to open a moderation case."""

    report_type: ReportType
    target_id: str
    reporter_id: str
    priority: CasePriority = CasePriority.NORMAL


class CaseRead(BaseModel):
    """A moderation case enriched with derived SLA fields."""

    id: str
    report_type: ReportType
    target_id: str
    reporter_id: str
    status: CaseStatus
    priority: CasePriority
    assignee_id: str | None = None
    resolution: str | None = None
    created_at: datetime
    due_at: datetime
    is_overdue: bool
    is_terminal: bool
    sla_hours: int

    @classmethod
    def from_domain(cls, case: ModerationCase) -> CaseRead:
        """Build a schema from a domain case."""
        return cls(
            id=case.id,
            report_type=case.report_type,
            target_id=case.target_id,
            reporter_id=case.reporter_id,
            status=case.status,
            priority=case.priority,
            assignee_id=case.assignee_id,
            resolution=case.resolution,
            created_at=case.created_at,
            due_at=case.due_at,
            is_overdue=case.is_overdue(),
            is_terminal=case.is_terminal,
            sla_hours=case.priority.sla_hours,
        )


class CaseListResponse(BaseModel):
    """A page of moderation cases."""

    items: list[CaseRead]
    total: int
    limit: int
    offset: int


class AssignRequest(BaseModel):
    """Payload used to assign a case."""

    assignee_id: str


class ResolutionRequest(BaseModel):
    """Payload used to resolve a case."""

    resolution: str


class DismissRequest(BaseModel):
    """Payload used to dismiss a case."""

    reason: str


class AccountStatusRequest(BaseModel):
    """Payload used to suspend or activate an account."""

    user_id: str
    status: AccountStatus
    reason: str = ""
    flags: list[str] = Field(default_factory=list)


class AccountControlRead(BaseModel):
    """Administrative control joined with account identity."""

    user_id: str
    username: str
    role: str
    status: AccountStatus
    flags: list[str]
    updated_at: datetime
    is_suspended: bool
    auth_active: bool
    is_consistent: bool

    @classmethod
    def from_domain(cls, view: AccountControlView) -> AccountControlRead:
        """Build a schema from an account control view."""
        return cls(
            user_id=view.user_id,
            username=view.username,
            role=view.role,
            status=view.status,
            flags=list(view.flags),
            updated_at=view.control.updated_at,
            is_suspended=view.is_suspended,
            auth_active=view.auth_active,
            is_consistent=view.is_consistent,
        )


class AccountControlListResponse(BaseModel):
    """Every account control visible to an administrator."""

    items: list[AccountControlRead]
    suspended: int


class AdminActionRead(BaseModel):
    """One entry in the audit trail."""

    id: str
    actor_id: str
    target_type: TargetType
    target_id: str
    action: AdminActionKind
    reason: str
    created_at: datetime
    summary: str

    @classmethod
    def from_domain(cls, entry: AdminAction) -> AdminActionRead:
        """Build a schema from an audit entry."""
        return cls(
            id=entry.id,
            actor_id=entry.actor_id,
            target_type=entry.target_type,
            target_id=entry.target_id,
            action=entry.action,
            reason=entry.reason,
            created_at=entry.created_at,
            summary=entry.summary,
        )


class ActionListResponse(BaseModel):
    """A page of audit trail entries."""

    items: list[AdminActionRead]
    total: int
    limit: int
    offset: int


class HealthCreateRequest(BaseModel):
    """Payload used to record a health snapshot."""

    database_ok: bool
    api_latency_ms: float
    cache_hit_ratio: float
    queue_depth: int


class HealthRead(BaseModel):
    """A health snapshot with derived score and state."""

    id: str
    checked_at: datetime
    database_ok: bool
    api_latency_ms: float
    cache_hit_ratio: float
    queue_depth: int
    score: float
    state: HealthState
    bottleneck: str
    is_healthy: bool

    @classmethod
    def from_domain(cls, check: SystemHealth) -> HealthRead:
        """Build a schema from a domain health snapshot."""
        return cls(
            id=check.id,
            checked_at=check.checked_at,
            database_ok=check.database_ok,
            api_latency_ms=check.api_latency_ms,
            cache_hit_ratio=check.cache_hit_ratio,
            queue_depth=check.queue_depth,
            score=check.score,
            state=check.state,
            bottleneck=check.bottleneck,
            is_healthy=check.is_healthy,
        )


class HealthListResponse(BaseModel):
    """Recent health snapshots and the latest one."""

    items: list[HealthRead]
    latest: HealthRead | None = None


class AdminStatsRead(BaseModel):
    """Aggregated administration statistics."""

    total_cases: int
    open_cases: int
    in_review_cases: int
    resolved_cases: int
    dismissed_cases: int
    active_cases: int
    overdue_cases: int
    critical_cases: int
    suspended_accounts: int
    actions_24h: int
    health_checks: int
    latest_score: float
    database_ok: bool
    resolution_rate: float
    attention_score: int
    health_state: HealthState
    priority_counts: dict[str, int]
    report_counts: dict[str, int]

    @classmethod
    def from_domain(cls, stats: AdminStats) -> AdminStatsRead:
        """Build a schema from a domain statistics object."""
        return cls(
            total_cases=stats.total_cases,
            open_cases=stats.open_cases,
            in_review_cases=stats.in_review_cases,
            resolved_cases=stats.resolved_cases,
            dismissed_cases=stats.dismissed_cases,
            active_cases=stats.active_cases,
            overdue_cases=stats.overdue_cases,
            critical_cases=stats.critical_cases,
            suspended_accounts=stats.suspended_accounts,
            actions_24h=stats.actions_24h,
            health_checks=stats.health_checks,
            latest_score=stats.latest_score,
            database_ok=stats.database_ok,
            resolution_rate=stats.resolution_rate,
            attention_score=stats.attention_score,
            health_state=stats.health_state,
            priority_counts=stats.priority_counts,
            report_counts=stats.report_counts,
        )
