"""Router package for the CTF Team Dashboard."""

from ctf_team_dashboard.routers import (
    auth,
    challenges,
    dashboard,
    health,
    members,
    realtime,
    solves,
    stats,
    teams,
)

__all__ = [
    "auth",
    "challenges",
    "dashboard",
    "health",
    "members",
    "realtime",
    "solves",
    "stats",
    "teams",
]
