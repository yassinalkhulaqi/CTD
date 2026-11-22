"""HTTP routes for the accessibility toolkit."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from ctf_team_dashboard.features.accessibility.models import (
    A11yIssue,
    AccessibilityStats,
    ContrastAudit,
    ContrastPair,
    FocusOrderEntry,
    FocusTrap,
    KeyboardShortcut,
    Severity,
    ShortcutConflict,
)
from ctf_team_dashboard.features.accessibility.schemas import (
    AccessibilityStatsRead,
    AriaSuggestionRead,
    AriaSuggestionRequest,
    ContrastAuditRead,
    ContrastPairRead,
    ContrastPairRequest,
    FocusOrderCreateRequest,
    FocusOrderEntryRead,
    FocusOrderReorderRequest,
    FocusTrapRead,
    IssueCreateRequest,
    IssueRead,
    ShortcutConflictRead,
    ShortcutCreateRequest,
    ShortcutRead,
)
from ctf_team_dashboard.features.accessibility.service import AccessibilityService

router = APIRouter(prefix="/api/accessibility", tags=["accessibility"])


def get_accessibility_service() -> AccessibilityService:
    """Dependency returning a service bound to the active database."""
    return AccessibilityService()


AccessibilityServiceDep = Annotated[AccessibilityService, Depends(get_accessibility_service)]


def _issue_read(issue: A11yIssue) -> IssueRead:
    """Map an issue domain object onto its API representation."""
    return IssueRead(
        id=issue.id,
        path=issue.path,
        rule_id=issue.rule_id,
        severity=issue.severity,
        description=issue.description,
        suggestion=issue.suggestion,
        detected_at=issue.detected_at,
        resolved_at=issue.resolved_at,
        is_resolved=issue.is_resolved,
        severity_weight=issue.severity_weight,
    )


def _shortcut_read(shortcut: KeyboardShortcut) -> ShortcutRead:
    """Map a shortcut domain object onto its API representation."""
    return ShortcutRead(
        id=shortcut.id,
        keys=shortcut.canonical_keys,
        canonical_keys=shortcut.canonical_keys,
        display_keys=shortcut.display_keys,
        action=shortcut.action,
        scope=shortcut.scope,
        is_global=shortcut.is_global,
        is_chord=shortcut.is_chord,
    )


def _contrast_read(pair: ContrastPair) -> ContrastPairRead:
    """Map a contrast pair onto its API representation."""
    return ContrastPairRead(
        foreground=pair.foreground_hex,
        background=pair.background_hex,
        path=pair.path,
        label=pair.label,
        large_text=pair.large_text,
        ratio=pair.ratio,
        passes_aa=pair.passes_aa,
        passes_aaa=pair.passes_aaa,
        level=pair.level,
        suggestion=pair.suggestion,
    )


def _audit_read(audit: ContrastAudit) -> ContrastAuditRead:
    """Map a contrast audit onto its API representation."""
    return ContrastAuditRead(
        pairs=[_contrast_read(pair) for pair in audit.pairs],
        issues=[_issue_read(issue) for issue in audit.issues],
        failures=len(audit.failures),
        pass_rate=round(audit.pass_rate, 4),
        average_ratio=audit.average_ratio,
    )


def _focus_read(entry: FocusOrderEntry) -> FocusOrderEntryRead:
    """Map a focus stop onto its API representation."""
    return FocusOrderEntryRead(
        id=entry.id,
        label=entry.label,
        order=entry.order,
        aria_label=entry.aria_label,
    )


def _trap_read(trap: FocusTrap) -> FocusTrapRead:
    """Map a focus trap snapshot onto its API representation."""
    return FocusTrapRead(
        entries=[_focus_read(entry) for entry in trap.entries],
        index=trap.index,
        size=trap.size,
        current_id=trap.current.id if trap.current else None,
        next_id=trap.next_entry.id if trap.next_entry else None,
        previous_id=trap.previous_entry.id if trap.previous_entry else None,
    )


def _conflict_read(conflict: ShortcutConflict) -> ShortcutConflictRead:
    """Map a shortcut collision onto its API representation."""
    return ShortcutConflictRead(
        description=conflict.description,
        left_id=conflict.left.id,
        right_id=conflict.right.id,
        keys=conflict.left.canonical_keys,
    )


def _stats_read(stats: AccessibilityStats) -> AccessibilityStatsRead:
    """Map accessibility statistics onto their API representation."""
    return AccessibilityStatsRead(
        total_issues=stats.total_issues,
        open_issues=stats.open_issues,
        resolved_issues=stats.resolved_issues,
        critical_open=stats.critical_open,
        warning_open=stats.warning_open,
        info_open=stats.info_open,
        shortcut_count=stats.shortcut_count,
        focus_entry_count=stats.focus_entry_count,
        scopes=list(stats.scopes),
        severity_counts=stats.severity_counts,
        resolution_rate=stats.resolution_rate,
        risk_score=stats.risk_score,
    )


@router.get("/issues", response_model=list[IssueRead])
def list_issues(
    service: AccessibilityServiceDep,
    path: str | None = None,
    severity: Severity | None = None,
    resolved: bool | None = None,
    limit: int = 200,
) -> list[IssueRead]:
    """Return issues filtered by route, severity and resolution state."""
    return [
        _issue_read(issue)
        for issue in service.list_issues(
            path=path, severity=severity, resolved=resolved, limit=limit
        )
    ]


@router.post("/issues", response_model=IssueRead, status_code=status.HTTP_201_CREATED)
def create_issue(payload: IssueCreateRequest, service: AccessibilityServiceDep) -> IssueRead:
    """Record a new accessibility issue."""
    issue = service.record_issue(
        path=payload.path,
        rule_id=payload.rule_id,
        severity=payload.severity,
        description=payload.description,
        suggestion=payload.suggestion,
        detected_at=payload.detected_at,
    )
    return _issue_read(issue)


@router.post("/issues/{issue_id}/resolve", response_model=IssueRead)
def resolve_issue(issue_id: str, service: AccessibilityServiceDep) -> IssueRead:
    """Mark an accessibility issue as resolved."""
    return _issue_read(service.resolve_issue(issue_id))


@router.get("/shortcuts", response_model=list[ShortcutRead])
def list_shortcuts(
    service: AccessibilityServiceDep, scope: str | None = None
) -> list[ShortcutRead]:
    """Return registered shortcuts for a scope, including global bindings."""
    return [_shortcut_read(shortcut) for shortcut in service.list_shortcuts(scope=scope)]


@router.post("/shortcuts", response_model=ShortcutRead, status_code=status.HTTP_201_CREATED)
def register_shortcut(
    payload: ShortcutCreateRequest, service: AccessibilityServiceDep
) -> ShortcutRead:
    """Register a shortcut after conflict detection."""
    return _shortcut_read(
        service.register_shortcut(keys=payload.keys, action=payload.action, scope=payload.scope)
    )


@router.get("/shortcuts/conflicts", response_model=list[ShortcutConflictRead])
def shortcut_conflicts(service: AccessibilityServiceDep) -> list[ShortcutConflictRead]:
    """Return all conflicting shortcut pairs currently registered."""
    return [_conflict_read(conflict) for conflict in service.shortcut_conflicts()]


@router.delete("/shortcuts/{shortcut_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shortcut(shortcut_id: str, service: AccessibilityServiceDep) -> Response:
    """Remove a registered shortcut."""
    service.delete_shortcut(shortcut_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/contrast", response_model=ContrastAuditRead)
def audit_contrast(
    payload: ContrastPairRequest, service: AccessibilityServiceDep
) -> ContrastAuditRead:
    """Evaluate a colour pair against WCAG contrast thresholds."""
    audit = service.audit_color_pair(
        foreground=payload.foreground,
        background=payload.background,
        path=payload.path,
        label=payload.label,
        large_text=payload.large_text,
        record_issue=payload.record_issue,
    )
    return _audit_read(audit)


@router.get("/focus-orders", response_model=list[FocusOrderEntryRead])
def list_focus_orders(service: AccessibilityServiceDep) -> list[FocusOrderEntryRead]:
    """Return the configured tab order."""
    return [_focus_read(entry) for entry in service.list_focus_entries()]


@router.post(
    "/focus-orders", response_model=FocusOrderEntryRead, status_code=status.HTTP_201_CREATED
)
def create_focus_order(
    payload: FocusOrderCreateRequest, service: AccessibilityServiceDep
) -> FocusOrderEntryRead:
    """Add a stop to the configured tab order."""
    return _focus_read(service.record_focus_entry(payload.label, order=payload.order))


@router.post("/focus-orders/reorder", response_model=list[FocusOrderEntryRead])
def reorder_focus_orders(
    payload: FocusOrderReorderRequest, service: AccessibilityServiceDep
) -> list[FocusOrderEntryRead]:
    """Replace the tab order with the supplied sequence."""
    return [_focus_read(entry) for entry in service.reorder_focus_entries(payload.ids)]


@router.get("/focus-trap", response_model=FocusTrapRead)
def get_focus_trap(service: AccessibilityServiceDep, index: int = 0) -> FocusTrapRead:
    """Return a snapshot of the focus trap state machine."""
    return _trap_read(service.build_focus_trap(index=max(0, index)))


@router.post("/aria-suggestions", response_model=AriaSuggestionRead)
def aria_suggestion(
    payload: AriaSuggestionRequest, service: AccessibilityServiceDep
) -> AriaSuggestionRead:
    """Generate a descriptive ARIA label for a control."""
    return AriaSuggestionRead(
        suggestion=service.suggest_aria_label(
            payload.text, context=payload.context, action=payload.action
        )
    )


@router.get("/stats", response_model=AccessibilityStatsRead)
def get_stats(service: AccessibilityServiceDep) -> AccessibilityStatsRead:
    """Return aggregated accessibility counters."""
    return _stats_read(service.stats())
