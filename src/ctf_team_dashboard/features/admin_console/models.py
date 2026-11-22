"""Domain model of the administration console feature."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from ctf_team_dashboard.domain.enums import StrEnum
from ctf_team_dashboard.domain.models import ensure_utc, utcnow


class ReportType(StrEnum):
    """Reason a moderation case was opened."""

    HARASSMENT = "harassment"
    CHEATING = "cheating"
    SPAM = "spam"
    INAPPROPRIATE = "inappropriate_content"
    SECURITY = "security_issue"
    OTHER = "other"

    @property
    def label(self) -> str:
        """Return a display label for the report type."""
        labels = {
            ReportType.HARASSMENT: "Harassment",
            ReportType.CHEATING: "Cheating",
            ReportType.SPAM: "Spam",
            ReportType.INAPPROPRIATE: "Inappropriate content",
            ReportType.SECURITY: "Security issue",
            ReportType.OTHER: "Other",
        }
        return labels[self]


class CaseStatus(StrEnum):
    """Lifecycle status of a moderation case."""

    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"

    @property
    def is_terminal(self) -> bool:
        """Return whether the status ends the case lifecycle."""
        return self in (CaseStatus.RESOLVED, CaseStatus.DISMISSED)

    @property
    def label(self) -> str:
        """Return a display label for the status."""
        labels = {
            CaseStatus.OPEN: "Open",
            CaseStatus.IN_REVIEW: "In review",
            CaseStatus.RESOLVED: "Resolved",
            CaseStatus.DISMISSED: "Dismissed",
        }
        return labels[self]


class CasePriority(StrEnum):
    """Handling priority and its service level target."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def sla_hours(self) -> int:
        """Return the number of hours allowed before the case breaches SLA."""
        hours = {
            CasePriority.LOW: 72,
            CasePriority.NORMAL: 24,
            CasePriority.HIGH: 8,
            CasePriority.CRITICAL: 2,
        }
        return hours[self]

    @property
    def rank(self) -> int:
        """Return a numeric rank used for ordering."""
        return list(CasePriority).index(self) + 1

    @property
    def label(self) -> str:
        """Return a display label for the priority."""
        return self.value.capitalize()


class CaseSort(StrEnum):
    """Supported orderings of the moderation queue."""

    CREATED_DESC = "created_desc"
    CREATED_ASC = "created_asc"
    PRIORITY_DESC = "priority_desc"
    DUE_ASC = "due_asc"


class TargetType(StrEnum):
    """Kind of object referenced by an administrative action."""

    CASE = "case"
    ACCOUNT = "account"
    SYSTEM = "system"


class AdminActionKind(StrEnum):
    """Auditable action performed from the administration console."""

    CASE_OPENED = "case_opened"
    CASE_ASSIGNED = "case_assigned"
    CASE_RESOLVED = "case_resolved"
    CASE_DISMISSED = "case_dismissed"
    ACCOUNT_SUSPENDED = "account_suspended"
    ACCOUNT_ACTIVATED = "account_activated"
    HEALTH_RECORDED = "health_recorded"

    @property
    def label(self) -> str:
        """Return a display label for the action."""
        return self.value.replace("_", " ").capitalize()


class AccountStatus(StrEnum):
    """Operational state of a dashboard account."""

    ACTIVE = "active"
    SUSPENDED = "suspended"

    @property
    def is_suspended(self) -> bool:
        """Return whether the status blocks access."""
        return self is AccountStatus.SUSPENDED


class HealthState(StrEnum):
    """Overall state derived from a health check."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"

    @property
    def label(self) -> str:
        """Return a display label for the health state."""
        return self.value.capitalize()


_ALLOWED_TRANSITIONS: dict[CaseStatus, frozenset[CaseStatus]] = {
    CaseStatus.OPEN: frozenset({CaseStatus.IN_REVIEW, CaseStatus.RESOLVED, CaseStatus.DISMISSED}),
    CaseStatus.IN_REVIEW: frozenset({CaseStatus.RESOLVED, CaseStatus.DISMISSED}),
    CaseStatus.RESOLVED: frozenset(),
    CaseStatus.DISMISSED: frozenset(),
}


def can_transition(source: CaseStatus, target: CaseStatus) -> bool:
    """Return whether a case may move from one status to another."""
    return target in _ALLOWED_TRANSITIONS.get(source, frozenset())


def clamp(value: float, low: float, high: float) -> float:
    """Clamp a number into the inclusive interval."""
    return min(max(value, low), high)


def health_score(
    *,
    database_ok: bool,
    api_latency_ms: float,
    cache_hit_ratio: float,
    queue_depth: int,
) -> float:
    """Compute a 0-100 health score from the collected infrastructure metrics.

    Database availability contributes 40 percent, API latency 25 percent,
    cache efficiency 20 percent and queue pressure 15 percent. Latency is
    considered healthy below 200 ms and saturated at 2000 ms; the queue is
    saturated at 500 pending jobs.
    """
    database_component = 1.0 if database_ok else 0.0
    latency_component = clamp(1.0 - max(0.0, api_latency_ms) / 2000.0, 0.0, 1.0)
    cache_component = clamp(cache_hit_ratio, 0.0, 1.0)
    queue_component = clamp(1.0 - max(0, queue_depth) / 500.0, 0.0, 1.0)
    weighted = (
        database_component * 0.40
        + latency_component * 0.25
        + cache_component * 0.20
        + queue_component * 0.15
    )
    return round(clamp(weighted, 0.0, 1.0) * 100.0, 1)


def health_state(score: float, *, database_ok: bool) -> HealthState:
    """Map a score to a health state, forcing critical when the database is down."""
    if not database_ok:
        return HealthState.CRITICAL
    if score >= 85.0:
        return HealthState.HEALTHY
    if score >= 60.0:
        return HealthState.DEGRADED
    return HealthState.CRITICAL


def health_bottleneck(
    *,
    database_ok: bool,
    api_latency_ms: float,
    cache_hit_ratio: float,
    queue_depth: int,
) -> str:
    """Return the name of the weakest health component."""
    components: tuple[tuple[str, float], ...] = (
        ("database", 1.0 if database_ok else 0.0),
        ("api_latency", clamp(1.0 - max(0.0, api_latency_ms) / 2000.0, 0.0, 1.0)),
        ("cache_hit_ratio", clamp(cache_hit_ratio, 0.0, 1.0)),
        ("queue_depth", clamp(1.0 - max(0, queue_depth) / 500.0, 0.0, 1.0)),
    )
    weakest = min(components, key=lambda item: item[1])
    return weakest[0]


@dataclass(frozen=True, slots=True)
class ModerationCase:
    """A report awaiting action by an administrator."""

    id: str
    report_type: ReportType
    target_id: str
    reporter_id: str
    status: CaseStatus = CaseStatus.OPEN
    priority: CasePriority = CasePriority.NORMAL
    assignee_id: str | None = None
    resolution: str | None = None
    created_at: datetime = field(default_factory=utcnow)

    @property
    def is_terminal(self) -> bool:
        """Return whether the case has been closed."""
        return self.status.is_terminal

    @property
    def is_assigned(self) -> bool:
        """Return whether an administrator owns the case."""
        return bool(self.assignee_id)

    @property
    def due_at(self) -> datetime:
        """Return the SLA deadline derived from creation time and priority."""
        return ensure_utc(self.created_at) + timedelta(hours=self.priority.sla_hours)

    def hours_until_due(self, now: datetime | None = None) -> float:
        """Return the signed number of hours left before the SLA deadline."""
        current = ensure_utc(now if now is not None else utcnow())
        return (self.due_at - current).total_seconds() / 3600.0

    def is_overdue(self, now: datetime | None = None) -> bool:
        """Return whether an open case has breached its SLA."""
        if self.is_terminal:
            return False
        return self.hours_until_due(now) < 0

    def age_hours(self, now: datetime | None = None) -> float:
        """Return the number of hours since the case was opened."""
        current = ensure_utc(now if now is not None else utcnow())
        return max(0.0, (current - ensure_utc(self.created_at)).total_seconds() / 3600.0)

    def urgency_score(self, now: datetime | None = None) -> float:
        """Return a ranking score combining priority and SLA breach."""
        overdue_hours = max(0.0, -self.hours_until_due(now))
        return self.priority.rank * 10.0 + overdue_hours * 2.0

    def to_in_review(self, assignee_id: str) -> ModerationCase:
        """Return the case owned by an administrator."""
        return replace(self, status=CaseStatus.IN_REVIEW, assignee_id=assignee_id)

    def close(self, status: CaseStatus, resolution: str) -> ModerationCase:
        """Return the case in a terminal state with its resolution recorded."""
        return replace(self, status=status, resolution=resolution)


@dataclass(frozen=True, slots=True)
class AdminAction:
    """An append-only entry in the administration audit trail."""

    id: str
    actor_id: str
    target_type: TargetType
    target_id: str
    action: AdminActionKind
    reason: str = ""
    created_at: datetime = field(default_factory=utcnow)

    @property
    def has_reason(self) -> bool:
        """Return whether the action carries an explanatory reason."""
        return bool(self.reason.strip())

    @property
    def summary(self) -> str:
        """Return a compact human readable description of the action."""
        target = f"{self.target_type.value}:{self.target_id}"
        if self.has_reason:
            return f"{self.action.label} on {target} — {self.reason}"
        return f"{self.action.label} on {target}"


@dataclass(frozen=True, slots=True)
class AccountControl:
    """Administrative controls attached to a dashboard account."""

    user_id: str
    status: AccountStatus = AccountStatus.ACTIVE
    flags: tuple[str, ...] = field(default_factory=tuple)
    updated_at: datetime = field(default_factory=utcnow)

    @property
    def is_suspended(self) -> bool:
        """Return whether the account is suspended."""
        return self.status.is_suspended

    def has_flag(self, flag: str) -> bool:
        """Return whether a named flag is present."""
        return flag in self.flags

    def with_status(
        self,
        status: AccountStatus,
        *,
        flags: tuple[str, ...] | None = None,
        updated_at: datetime | None = None,
    ) -> AccountControl:
        """Return a copy with a new account status."""
        return replace(
            self,
            status=status,
            flags=self.flags if flags is None else flags,
            updated_at=updated_at if updated_at is not None else utcnow(),
        )


@dataclass(frozen=True, slots=True)
class SystemHealth:
    """A recorded snapshot of infrastructure health metrics."""

    id: str
    checked_at: datetime
    database_ok: bool
    api_latency_ms: float
    cache_hit_ratio: float
    queue_depth: int

    @property
    def score(self) -> float:
        """Return the derived health score."""
        return health_score(
            database_ok=self.database_ok,
            api_latency_ms=self.api_latency_ms,
            cache_hit_ratio=self.cache_hit_ratio,
            queue_depth=self.queue_depth,
        )

    @property
    def state(self) -> HealthState:
        """Return the derived health state."""
        return health_state(self.score, database_ok=self.database_ok)

    @property
    def bottleneck(self) -> str:
        """Return the metric that most limits the health score."""
        return health_bottleneck(
            database_ok=self.database_ok,
            api_latency_ms=self.api_latency_ms,
            cache_hit_ratio=self.cache_hit_ratio,
            queue_depth=self.queue_depth,
        )

    @property
    def is_healthy(self) -> bool:
        """Return whether the snapshot is fully healthy."""
        return self.state is HealthState.HEALTHY


@dataclass(frozen=True, slots=True)
class CaseFilter:
    """Declarative filter and ordering applied to the moderation queue."""

    statuses: tuple[CaseStatus, ...] = field(default_factory=tuple)
    priorities: tuple[CasePriority, ...] = field(default_factory=tuple)
    report_types: tuple[ReportType, ...] = field(default_factory=tuple)
    assignee_id: str | None = None
    unassigned_only: bool = False
    search: str = ""
    overdue_only: bool = False
    sort: CaseSort = CaseSort.CREATED_DESC
    limit: int = 50
    offset: int = 0

    def matches(self, case: ModerationCase, now: datetime | None = None) -> bool:
        """Return whether a case satisfies every active filter."""
        if self.statuses and case.status not in self.statuses:
            return False
        if self.priorities and case.priority not in self.priorities:
            return False
        if self.report_types and case.report_type not in self.report_types:
            return False
        if self.assignee_id is not None and case.assignee_id != self.assignee_id:
            return False
        if self.unassigned_only and case.is_assigned:
            return False
        if self.overdue_only and not case.is_overdue(now):
            return False
        if self.search:
            needle = self.search.strip().lower()
            haystack = " ".join(
                part
                for part in (
                    case.id,
                    case.target_id,
                    case.reporter_id,
                    case.resolution or "",
                    case.report_type.value,
                )
                if part
            ).lower()
            if needle not in haystack:
                return False
        return True

    def matching(
        self, cases: list[ModerationCase], now: datetime | None = None
    ) -> list[ModerationCase]:
        """Return every matching case, ordered by the requested sort."""
        matched = [case for case in cases if self.matches(case, now)]
        if self.sort is CaseSort.CREATED_DESC:
            matched.sort(key=lambda case: ensure_utc(case.created_at), reverse=True)
        elif self.sort is CaseSort.CREATED_ASC:
            matched.sort(key=lambda case: ensure_utc(case.created_at))
        elif self.sort is CaseSort.PRIORITY_DESC:
            matched.sort(
                key=lambda case: (case.priority.rank, ensure_utc(case.created_at)),
                reverse=True,
            )
        else:
            matched.sort(key=lambda case: (case.due_at, case.priority.rank))
        return matched

    def apply(
        self, cases: list[ModerationCase], now: datetime | None = None
    ) -> list[ModerationCase]:
        """Return the requested page of matching cases."""
        matched = self.matching(cases, now)
        return matched[self.offset : self.offset + self.limit]


@dataclass(frozen=True, slots=True)
class ActionFilter:
    """Filter applied to the administration audit trail."""

    actor_id: str | None = None
    target_types: tuple[TargetType, ...] = field(default_factory=tuple)
    target_id: str | None = None
    actions: tuple[AdminActionKind, ...] = field(default_factory=tuple)
    since: datetime | None = None
    until: datetime | None = None
    search: str = ""
    limit: int = 100
    offset: int = 0

    def matches(self, entry: AdminAction) -> bool:
        """Return whether an action satisfies every active filter."""
        if self.actor_id is not None and entry.actor_id != self.actor_id:
            return False
        if self.target_types and entry.target_type not in self.target_types:
            return False
        if self.target_id is not None and entry.target_id != self.target_id:
            return False
        if self.actions and entry.action not in self.actions:
            return False
        moment = ensure_utc(entry.created_at)
        if self.since is not None and moment < ensure_utc(self.since):
            return False
        if self.until is not None and moment > ensure_utc(self.until):
            return False
        if self.search:
            needle = self.search.strip().lower()
            haystack = " ".join(
                (entry.actor_id, entry.target_id, entry.action.value, entry.reason)
            ).lower()
            if needle not in haystack:
                return False
        return True

    def apply(self, entries: list[AdminAction]) -> list[AdminAction]:
        """Return the requested page of matching actions, newest first."""
        matched = [entry for entry in entries if self.matches(entry)]
        matched.sort(key=lambda entry: ensure_utc(entry.created_at), reverse=True)
        return matched[self.offset : self.offset + self.limit]


@dataclass(frozen=True, slots=True)
class AccountControlView:
    """Account control joined with the identity data needed by the UI."""

    control: AccountControl
    username: str
    role: str
    auth_active: bool

    @property
    def user_id(self) -> str:
        """Return the account identifier."""
        return self.control.user_id

    @property
    def status(self) -> AccountStatus:
        """Return the administrative status of the account."""
        return self.control.status

    @property
    def flags(self) -> tuple[str, ...]:
        """Return the flags attached to the account."""
        return self.control.flags

    @property
    def is_suspended(self) -> bool:
        """Return whether the account is suspended."""
        return self.control.is_suspended

    @property
    def is_consistent(self) -> bool:
        """Return whether the control status agrees with the auth account state."""
        return self.is_suspended != self.auth_active


@dataclass(frozen=True, slots=True)
class AdminStats:
    """Aggregated statistics displayed on the administration overview."""

    total_cases: int = 0
    open_cases: int = 0
    in_review_cases: int = 0
    resolved_cases: int = 0
    dismissed_cases: int = 0
    overdue_cases: int = 0
    critical_cases: int = 0
    suspended_accounts: int = 0
    actions_24h: int = 0
    health_checks: int = 0
    latest_score: float = 0.0
    database_ok: bool = True
    priority_counts: dict[str, int] = field(default_factory=dict)
    report_counts: dict[str, int] = field(default_factory=dict)

    @property
    def active_cases(self) -> int:
        """Return the number of cases that still need attention."""
        return self.open_cases + self.in_review_cases

    @property
    def resolution_rate(self) -> float:
        """Return the fraction of cases that reached a resolution."""
        if self.total_cases <= 0:
            return 0.0
        return self.resolved_cases / self.total_cases

    @property
    def attention_score(self) -> int:
        """Return a rough count of items requiring administrator attention."""
        return self.overdue_cases + self.critical_cases + self.suspended_accounts

    @property
    def health_state(self) -> HealthState:
        """Return the state implied by the latest health snapshot."""
        return health_state(self.latest_score, database_ok=self.database_ok)
