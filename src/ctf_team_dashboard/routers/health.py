"""Health check endpoints for the CTF Team Dashboard."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, status

from ctf_team_dashboard import __version__
from ctf_team_dashboard.db.engine import get_database

router = APIRouter(tags=["health"])


@router.get("/api/health", status_code=status.HTTP_200_OK)
def health() -> dict[str, str]:
    """Return service health."""
    return {"status": "ok", "version": __version__}


@router.get("/api/health/ready", status_code=status.HTTP_200_OK)
def readiness() -> dict[str, object]:
    """Return a readiness probe including the database connectivity check."""
    database = get_database()
    healthy = False
    try:
        healthy = "teams" in database.table_names()
    except Exception:
        healthy = False
    return {
        "status": "ready" if healthy else "degraded",
        "database": healthy,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
