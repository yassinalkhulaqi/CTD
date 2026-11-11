"""Audit trail endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ctf_team_dashboard.dependencies import require_permission
from ctf_team_dashboard.security.audit import AuditAction, get_audit_log
from ctf_team_dashboard.security.permissions import Permission

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/entries")
def list_entries(
    limit: int = Query(default=100, ge=1, le=500),
    action: str | None = Query(default=None),
    _principal: object = Depends(require_permission(Permission.AUDIT_VIEW)),
) -> dict[str, object]:
    """Return the most recent entries of the audit trail."""
    parsed: AuditAction | None = None
    if action:
        try:
            parsed = AuditAction(action)
        except ValueError:
            parsed = None

    entries = get_audit_log().recent(limit=limit, action=parsed)
    return {
        "entries": [entry.to_dict() for entry in entries],
        "total": get_audit_log().size,
    }


@router.get("/actions")
def list_actions() -> dict[str, object]:
    """Return the catalogue of audited actions."""
    return {
        "actions": [
            {"value": action.value, "label": action.value.replace(".", " ")}
            for action in AuditAction
        ]
    }


@router.get("/summary")
def summary(
    _principal: object = Depends(require_permission(Permission.AUDIT_VIEW)),
) -> dict[str, object]:
    """Return the number of audited events grouped by action."""
    log = get_audit_log()
    counts: dict[str, int] = {}
    for entry in log.recent(limit=log.size):
        counts[entry.action.value] = counts.get(entry.action.value, 0) + 1
    return {"counts": counts, "total": log.size}
