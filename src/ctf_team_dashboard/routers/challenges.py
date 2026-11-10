"""Challenge endpoints for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import APIRouter

from ctf_team_dashboard.services import demo

router = APIRouter()


@router.get("/api/challenges")
def list_challenges() -> list[dict[str, str]]:
    """Return all tracked challenges."""
    _, _, challenges, _ = demo.load_demo_data()
    return [
        {
            "id": challenge.id,
            "team_id": challenge.team_id,
            "title": challenge.title,
            "category": challenge.category,
            "difficulty": challenge.difficulty,
        }
        for challenge in challenges
    ]
