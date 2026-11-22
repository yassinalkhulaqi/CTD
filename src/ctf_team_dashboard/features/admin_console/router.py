"""HTTP API for the administration console feature."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ctf_team_dashboard.dependencies import require_role
from ctf_team_dashboard.features.admin_console.models import (
    ActionFilter,
    AdminActionKind,
    CaseFilter,
    CasePriority,
    CaseSort,
    CaseStatus,
    ReportType,
    TargetType,
)
from ctf_team_dashboard.features.admin_console.schemas import (
    AccountControlListResponse,
    AccountControlRead,
    AccountStatusRequest,
    ActionListResponse,
    AdminActionRead,
    AdminStatsRead,
    AssignRequest,
    CaseCreateRequest,
    CaseListResponse,
    CaseRead,
    DismissRequest,
    HealthCreateRequest,
    HealthListResponse,
    HealthRead,
    ResolutionRequest,
)
from ctf_team_dashboard.features.admin_console.service import AdminService
from ctf_team_dashboard.services.auth import Principal

router = APIRouter(prefix="/api/admin", tags=["admin"])


def get_admin_service() -> AdminService:
    """Dependency returning the administration service."""
    return AdminService()


AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]
AdminPrincipalDep = Annotated[Principal, Depends(require_role("admin"))]


@router.get("/cases", response_model=CaseListResponse)
def list_cases(
    service: AdminServiceDep,
    _principal: AdminPrincipalDep,
    status: CaseStatus | None = None,
    priority: CasePriority | None = None,
    report_type: ReportType | None = None,
    assignee_id: str | None = None,
    unassigned: bool = False,
    search: str = "",
    overdue: bool = False,
    sort: CaseSort = CaseSort.CREATED_DESC,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> CaseListResponse:
    """Return a filtered page of the moderation queue."""
    spec = CaseFilter(
        statuses=(status,) if status is not None else (),
        priorities=(priority,) if priority is not None else (),
        report_types=(report_type,) if report_type is not None else (),
        assignee_id=assignee_id,
        unassigned_only=unassigned,
        search=search,
        overdue_only=overdue,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    cases, total = service.list_cases(spec)
    return CaseListResponse(
        items=[CaseRead.from_domain(case) for case in cases],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/cases", response_model=CaseRead, status_code=201)
def create_case(
    payload: CaseCreateRequest,
    service: AdminServiceDep,
    principal: AdminPrincipalDep,
) -> CaseRead:
    """Open a new moderation case."""
    case = service.open_case(
        actor_id=principal.user_id,
        report_type=payload.report_type,
        target_id=payload.target_id,
        reporter_id=payload.reporter_id,
        priority=payload.priority,
    )
    return CaseRead.from_domain(case)


@router.post("/cases/{case_id}/assign", response_model=CaseRead)
def assign_case(
    case_id: str,
    payload: AssignRequest,
    service: AdminServiceDep,
    principal: AdminPrincipalDep,
) -> CaseRead:
    """Assign a case and move it into review."""
    case = service.assign_case(
        case_id,
        actor_id=principal.user_id,
        assignee_id=payload.assignee_id,
    )
    return CaseRead.from_domain(case)


@router.post("/cases/{case_id}/resolve", response_model=CaseRead)
def resolve_case(
    case_id: str,
    payload: ResolutionRequest,
    service: AdminServiceDep,
    principal: AdminPrincipalDep,
) -> CaseRead:
    """Resolve a case with a written resolution."""
    case = service.resolve_case(
        case_id,
        actor_id=principal.user_id,
        resolution=payload.resolution,
    )
    return CaseRead.from_domain(case)


@router.post("/cases/{case_id}/dismiss", response_model=CaseRead)
def dismiss_case(
    case_id: str,
    payload: DismissRequest,
    service: AdminServiceDep,
    principal: AdminPrincipalDep,
) -> CaseRead:
    """Dismiss a case with a written reason."""
    case = service.dismiss_case(
        case_id,
        actor_id=principal.user_id,
        reason=payload.reason,
    )
    return CaseRead.from_domain(case)


@router.get("/account-controls", response_model=AccountControlListResponse)
def list_account_controls(
    service: AdminServiceDep,
    _principal: AdminPrincipalDep,
) -> AccountControlListResponse:
    """Return the account control table."""
    views = service.list_account_controls()
    return AccountControlListResponse(
        items=[AccountControlRead.from_domain(view) for view in views],
        suspended=sum(1 for view in views if view.is_suspended),
    )


@router.post("/account-controls", response_model=AccountControlRead)
def set_account_status(
    payload: AccountStatusRequest,
    service: AdminServiceDep,
    principal: AdminPrincipalDep,
) -> AccountControlRead:
    """Suspend or activate an account."""
    view = service.set_account_status(
        payload.user_id,
        actor_id=principal.user_id,
        status=payload.status,
        reason=payload.reason,
        flags=tuple(payload.flags),
    )
    return AccountControlRead.from_domain(view)


@router.get("/actions", response_model=ActionListResponse)
def list_actions(
    service: AdminServiceDep,
    _principal: AdminPrincipalDep,
    actor_id: str | None = None,
    target_type: TargetType | None = None,
    target_id: str | None = None,
    action: AdminActionKind | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    search: str = "",
    limit: int = Query(default=100, ge=1, le=300),
    offset: int = Query(default=0, ge=0),
) -> ActionListResponse:
    """Return a filtered page of the immutable audit trail."""
    spec = ActionFilter(
        actor_id=actor_id,
        target_types=(target_type,) if target_type is not None else (),
        target_id=target_id,
        actions=(action,) if action is not None else (),
        since=since,
        until=until,
        search=search,
        limit=limit,
        offset=offset,
    )
    entries, total = service.query_actions(spec)
    return ActionListResponse(
        items=[AdminActionRead.from_domain(entry) for entry in entries],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/health", response_model=HealthListResponse)
def list_health(
    service: AdminServiceDep,
    _principal: AdminPrincipalDep,
    limit: int = Query(default=20, ge=1, le=200),
) -> HealthListResponse:
    """Return the latest recorded health snapshots."""
    checks = service.list_health(limit)
    return HealthListResponse(
        items=[HealthRead.from_domain(check) for check in checks],
        latest=HealthRead.from_domain(checks[0]) if checks else None,
    )


@router.post("/health", response_model=HealthRead, status_code=201)
def record_health(
    payload: HealthCreateRequest,
    service: AdminServiceDep,
    principal: AdminPrincipalDep,
) -> HealthRead:
    """Record a new infrastructure health snapshot."""
    check = service.record_health_check(
        actor_id=principal.user_id,
        database_ok=payload.database_ok,
        api_latency_ms=payload.api_latency_ms,
        cache_hit_ratio=payload.cache_hit_ratio,
        queue_depth=payload.queue_depth,
    )
    return HealthRead.from_domain(check)


@router.get("/stats", response_model=AdminStatsRead)
def get_stats(
    service: AdminServiceDep,
    _principal: AdminPrincipalDep,
) -> AdminStatsRead:
    """Return the aggregated administration overview."""
    return AdminStatsRead.from_domain(service.stats())
