"""Router package for the CTF Team Dashboard."""

from ctf_team_dashboard.routers import (
    auth,
    challenges,
    health,
    members,
    solves,
    stats,
    teams,
)

__all__ = ["auth", "challenges", "health", "members", "solves", "stats", "teams"]
