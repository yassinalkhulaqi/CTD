"""Team endpoints for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import APIRouter

from ctf_team_dashboard.services import demo

router = APIRouter()


@router.get("/api/teams")
def list_teams() -> list[dict[str, str]]:
    """Return all tracked teams."""
    teams, _, _, _ = demo.load_demo_data()
    return [{"id": team.id, "name": team.name} for team in teams]
