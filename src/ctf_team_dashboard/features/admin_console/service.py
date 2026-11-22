"""Business rules and orchestration for the administration console."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from ctf_team_dashboard.domain.enums import MemberRole
from ctf_team_dashboard.domain.models import User, ensure_utc, utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.admin_console.models import (
    AccountControl,
    AccountControlView,
    AccountStatus,
    ActionFilter,
    AdminAction,
    AdminActionKind,
    AdminStats,
    CaseFilter,
    CasePriority,
    CaseStatus,
    ModerationCase,
    ReportType,
    SystemHealth,
    TargetType,
    can_transition,
)
from ctf_team_dashboard.features.admin_console.store import (
    AccountControlRepository,
    AdminActionRepository,
    HealthCheckRepository,
    ModerationCaseRepository,
    repository_priority_counts,
)
from ctf_team_dashboard.repositories.users import UserRepository


@dataclass(frozen=True, slots=True)
class AdminRepositories:
    """Repositories used by the administration service."""

    cases: ModerationCaseRepository = field(default_factory=ModerationCaseRepository)
    actions: AdminActionRepository = field(default_factory=AdminActionRepository)
    controls: AccountControlRepository = field(default_factory=AccountControlRepository)
    health: HealthCheckRepository = field(default_factory=HealthCheckRepository)
    users: UserRepository = field(default_factory=UserRepository)


def clean_text(value: str, field_name: str, *, max_length: int = 500) -> str:
    """Normalise and validate a required text field."""
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"{field_name} must not be empty")
    if len(cleaned) > max_length:
        raise ValidationError(f"{field_name} must not exceed {max_length} characters")
    return cleaned


def clean_flags(values: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    """Normalise a list of account flags into unique trimmed values."""
    if not values:
        return ()
    cleaned: list[str] = []
    for value in values:
        flag = value.strip().lower().replace(" ", "_")
        if flag and flag not in cleaned:
            cleaned.append(flag)
    return tuple(cleaned)


def validate_health_metrics(
    *,
    api_latency_ms: float,
    cache_hit_ratio: float,
    queue_depth: int,
) -> None:
    """Validate the numeric ranges of health metrics."""
    if api_latency_ms < 0 or api_latency_ms > 1_000_000:
        raise ValidationError("api_latency_ms must be between 0 and 1000000")
    if not 0.0 <= cache_hit_ratio <= 1.0:
        raise ValidationError("cache_hit_ratio must be between 0 and 1")
    if queue_depth < 0 or queue_depth > 1_000_000:
        raise ValidationError("queue_depth must be between 0 and 1000000")


class AdminService:
    """Implement moderation, account control, audit and health rules."""

    def __init__(self, repositories: AdminRepositories | None = None) -> None:
        self._repos = repositories or AdminRepositories()

    @property
    def repositories(self) -> AdminRepositories:
        """Return the repositories used by the service."""
        return self._repos

    def _record_action(
        self,
        *,
        actor_id: str,
        target_type: TargetType,
        target_id: str,
        action: AdminActionKind,
        reason: str = "",
    ) -> AdminAction:
        """Append an audit entry for a successful administrative operation."""
        entry = AdminAction(
            id=f"adm-{uuid.uuid4().hex[:12]}",
            actor_id=clean_text(actor_id, "actor_id", max_length=120),
            target_type=target_type,
            target_id=target_id,
            action=action,
            reason=reason.strip(),
            created_at=utcnow(),
        )
        return self._repos.actions.create(entry)

    def get_case(self, case_id: str) -> ModerationCase:
        """Return a case or raise a not found error."""
        case = self._repos.cases.get(case_id)
        if case is None:
            raise NotFoundError(f"Moderation case {case_id!r} does not exist")
        return case

    def list_cases(self, spec: CaseFilter | None = None) -> tuple[list[ModerationCase], int]:
        """Return a page of cases and the total number of matches."""
        query = spec or CaseFilter()
        return self._repos.cases.filtered(query), self._repos.cases.count_matching(query)

    def open_case(
        self,
        *,
        actor_id: str,
        report_type: ReportType,
        target_id: str,
        reporter_id: str,
        priority: CasePriority = CasePriority.NORMAL,
        created_at: datetime | None = None,
    ) -> ModerationCase:
        """Open a new moderation case and record its creation."""
        case = ModerationCase(
            id=f"case-{uuid.uuid4().hex[:12]}",
            report_type=report_type,
            target_id=clean_text(target_id, "target_id", max_length=200),
            reporter_id=clean_text(reporter_id, "reporter_id", max_length=200),
            status=CaseStatus.OPEN,
            priority=priority,
            created_at=ensure_utc(created_at) if created_at else utcnow(),
        )
        self._repos.cases.create(case)
        self._record_action(
            actor_id=actor_id,
            target_type=TargetType.CASE,
            target_id=case.id,
            action=AdminActionKind.CASE_OPENED,
            reason=f"{report_type.value} report against {case.target_id}",
        )
        return case

    def assign_case(
        self,
        case_id: str,
        *,
        actor_id: str,
        assignee_id: str,
    ) -> ModerationCase:
        """Assign an open case to an administrator, moving it into review."""
        case = self.get_case(case_id)
        if case.is_terminal:
            raise ConflictError(f"Case {case_id!r} is already closed")
        assignee = clean_text(assignee_id, "assignee_id", max_length=120)
        if case.status is CaseStatus.OPEN:
            updated = case.to_in_review(assignee)
        else:
            updated = replace(case, assignee_id=assignee)
        self._repos.cases.save(updated)
        self._record_action(
            actor_id=actor_id,
            target_type=TargetType.CASE,
            target_id=case.id,
            action=AdminActionKind.CASE_ASSIGNED,
            reason=f"assigned to {assignee}",
        )
        return updated

    def _ensure_openable(self, case: ModerationCase, target: CaseStatus) -> None:
        """Validate a requested status transition."""
        if not can_transition(case.status, target):
            raise ConflictError(
                f"Cannot move case {case.id!r} from {case.status.value} to {target.value}"
            )

    def resolve_case(
        self,
        case_id: str,
        *,
        actor_id: str,
        resolution: str,
    ) -> ModerationCase:
        """Resolve a case and store its resolution text."""
        case = self.get_case(case_id)
        self._ensure_openable(case, CaseStatus.RESOLVED)
        details = clean_text(resolution, "resolution")
        updated = case.close(CaseStatus.RESOLVED, details)
        self._repos.cases.save(updated)
        self._record_action(
            actor_id=actor_id,
            target_type=TargetType.CASE,
            target_id=case.id,
            action=AdminActionKind.CASE_RESOLVED,
            reason=details,
        )
        return updated

    def dismiss_case(
        self,
        case_id: str,
        *,
        actor_id: str,
        reason: str,
    ) -> ModerationCase:
        """Dismiss a case with an auditable explanation."""
        case = self.get_case(case_id)
        self._ensure_openable(case, CaseStatus.DISMISSED)
        details = clean_text(reason, "reason")
        updated = case.close(CaseStatus.DISMISSED, details)
        self._repos.cases.save(updated)
        self._record_action(
            actor_id=actor_id,
            target_type=TargetType.CASE,
            target_id=case.id,
            action=AdminActionKind.CASE_DISMISSED,
            reason=details,
        )
        return updated

    def _account_view(
        self,
        control: AccountControl,
        user: User | None = None,
    ) -> AccountControlView:
        """Join an account control with its identity record for the UI."""
        resolved = user or self._repos.users.get(control.user_id)
        if resolved is None:
            raise NotFoundError(f"Account {control.user_id!r} does not exist")
        return AccountControlView(
            control=control,
            username=resolved.username,
            role=resolved.role.value,
            auth_active=resolved.is_active,
        )

    def get_account_control(self, user_id: str) -> AccountControlView:
        """Return the control for one user, defaulting to an active record."""
        user = self._repos.users.get(user_id)
        if user is None:
            raise NotFoundError(f"Account {user_id!r} does not exist")
        control = self._repos.controls.get(user_id) or AccountControl(user_id=user_id)
        return self._account_view(control, user)

    def list_account_controls(self) -> list[AccountControlView]:
        """Return a view of every account and its control state."""
        views: list[AccountControlView] = []
        for user in self._repos.users.list_all():
            control = self._repos.controls.get(user.id) or AccountControl(user_id=user.id)
            views.append(self._account_view(control, user))
        return views

    def set_account_status(
        self,
        user_id: str,
        *,
        actor_id: str,
        status: AccountStatus,
        reason: str = "",
        flags: tuple[str, ...] | list[str] | None = None,
        updated_at: datetime | None = None,
    ) -> AccountControlView:
        """Suspend or activate an account while enforcing the safety guards."""
        actor = clean_text(actor_id, "actor_id", max_length=120)
        target_id = clean_text(user_id, "user_id", max_length=120)
        user = self._repos.users.get(target_id)
        if user is None:
            raise NotFoundError(f"Account {target_id!r} does not exist")

        existing = self._repos.controls.get(target_id)
        if status is AccountStatus.SUSPENDED:
            if actor == target_id:
                raise ValidationError("An administrator cannot suspend their own account")
            if user.is_admin:
                raise ConflictError("An administrator account cannot be suspended")
            details = clean_text(reason, "reason", max_length=300)
        else:
            details = reason.strip()

        current_status = existing.status if existing else AccountStatus.ACTIVE
        if current_status is status:
            raise ConflictError(f"Account {target_id!r} is already {status.value}")

        base_flags = existing.flags if existing else ()
        final_flags = clean_flags(flags) if flags is not None else base_flags
        if status is AccountStatus.SUSPENDED:
            final_flags = tuple(dict.fromkeys((*final_flags, "suspended")))
        else:
            final_flags = tuple(flag for flag in final_flags if flag != "suspended")

        control = AccountControl(
            user_id=target_id,
            status=status,
            flags=final_flags,
            updated_at=ensure_utc(updated_at) if updated_at else utcnow(),
        )
        self._repos.controls.upsert(control)
        updated_user = replace(user, is_active=status is AccountStatus.ACTIVE)
        self._repos.users.update(updated_user)
        self._record_action(
            actor_id=actor,
            target_type=TargetType.ACCOUNT,
            target_id=target_id,
            action=(
                AdminActionKind.ACCOUNT_SUSPENDED
                if status is AccountStatus.SUSPENDED
                else AdminActionKind.ACCOUNT_ACTIVATED
            ),
            reason=details,
        )
        return self._account_view(control, updated_user)

    def query_actions(self, spec: ActionFilter | None = None) -> tuple[list[AdminAction], int]:
        """Return a page of audit entries and the total number of matches."""
        query = spec or ActionFilter()
        return self._repos.actions.filtered(query), self._repos.actions.count_matching(query)

    def actions_for_case(self, case_id: str) -> list[AdminAction]:
        """Return the complete audit history of one case."""
        return self._repos.actions.for_target(TargetType.CASE, case_id)

    def record_health_check(
        self,
        *,
        actor_id: str,
        database_ok: bool,
        api_latency_ms: float,
        cache_hit_ratio: float,
        queue_depth: int,
        checked_at: datetime | None = None,
    ) -> SystemHealth:
        """Record an infrastructure snapshot and audit the operation."""
        actor = clean_text(actor_id, "actor_id", max_length=120)
        validate_health_metrics(
            api_latency_ms=api_latency_ms,
            cache_hit_ratio=cache_hit_ratio,
            queue_depth=queue_depth,
        )
        check = SystemHealth(
            id=f"health-{uuid.uuid4().hex[:12]}",
            checked_at=ensure_utc(checked_at) if checked_at else utcnow(),
            database_ok=bool(database_ok),
            api_latency_ms=float(api_latency_ms),
            cache_hit_ratio=float(cache_hit_ratio),
            queue_depth=int(queue_depth),
        )
        self._repos.health.create(check)
        self._record_action(
            actor_id=actor,
            target_type=TargetType.SYSTEM,
            target_id=check.id,
            action=AdminActionKind.HEALTH_RECORDED,
            reason=f"score {check.score:.1f} ({check.state.value})",
        )
        return check

    def list_health(self, limit: int = 50) -> list[SystemHealth]:
        """Return the most recent health snapshots."""
        safe_limit = max(1, min(limit, 200))
        return self._repos.health.list_recent(safe_limit)

    def get_health(self, check_id: str) -> SystemHealth:
        """Return a health snapshot by identifier."""
        check = self._repos.health.get(check_id)
        if check is None:
            raise NotFoundError(f"Health check {check_id!r} does not exist")
        return check

    def prune_health(self, *, max_items: int = 200) -> int:
        """Remove health snapshots beyond the retention limit."""
        if max_items < 1:
            raise ValidationError("max_items must be positive")
        snapshots = self._repos.health.list_recent(max_items)
        if len(snapshots) < max_items:
            return 0
        cutoff = snapshots[-1].checked_at
        return self._repos.health.remove_before(cutoff)

    def stats(self) -> AdminStats:
        """Aggregate the numbers displayed on the admin overview."""
        cases = self._repos.cases.list_all()
        now = utcnow()
        checks = self._repos.health.list_recent(100)
        latest = checks[0] if checks else None
        report_counts = {
            report.value: sum(1 for case in cases if case.report_type is report)
            for report in ReportType
        }
        return AdminStats(
            total_cases=len(cases),
            open_cases=self._repos.cases.count_status(CaseStatus.OPEN),
            in_review_cases=self._repos.cases.count_status(CaseStatus.IN_REVIEW),
            resolved_cases=self._repos.cases.count_status(CaseStatus.RESOLVED),
            dismissed_cases=self._repos.cases.count_status(CaseStatus.DISMISSED),
            overdue_cases=sum(1 for case in cases if case.is_overdue(now)),
            critical_cases=sum(1 for case in cases if case.priority is CasePriority.CRITICAL),
            suspended_accounts=self._repos.controls.count_suspended(),
            actions_24h=self._repos.actions.count_since(now - timedelta(hours=24)),
            health_checks=len(checks),
            latest_score=latest.score if latest else 0.0,
            database_ok=latest.database_ok if latest else True,
            priority_counts=repository_priority_counts(self._repos.cases),
            report_counts=report_counts,
        )

    def actor_is_admin(self, user_id: str) -> bool:
        """Return whether a known account has administrative clearance."""
        user: User | None = self._repos.users.get(user_id)
        if user is None:
            return False
        return user.role is MemberRole.ADMIN
