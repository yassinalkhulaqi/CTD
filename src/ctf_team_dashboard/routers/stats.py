"""Statistics endpoints for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import APIRouter

from ctf_team_dashboard.services import demo, stats

router = APIRouter()


@router.get("/api/stats/overview")
def get_overview() -> dict[str, int]:
    """Return headline counters for the dashboard."""
    teams, members, challenges, solves = demo.load_demo_data()
    overview = stats.compute_overview(
        team_count=len(teams),
        member_count=len(members),
        challenge_count=len(challenges),
        solve_count=len(solves),
    )
    return {
        "teams": overview.teams,
        "members": overview.members,
        "challenges": overview.challenges,
        "solves": overview.solves,
    }


@router.get("/api/stats/categories")
def get_categories() -> list[dict[str, int | str]]:
    """Return solve statistics grouped by challenge category."""
    _, _, challenges, solves = demo.load_demo_data()
    categories = stats.compute_category_stats(challenges, solves)
    return [
        {
            "category": category.category,
            "challenges": category.challenges,
            "solves": category.solves,
        }
        for category in categories
    ]
