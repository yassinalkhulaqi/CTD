"""Health check endpoints for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import APIRouter, status

router = APIRouter()


@router.get("/api/health", status_code=status.HTTP_200_OK)
def health() -> dict[str, str]:
    """Return service health."""
    return {"status": "ok"}
