"""Router package for the CTF Team Dashboard."""

from ctf_team_dashboard.routers import (
    analytics,
    audit,
    auth,
    challenge_details,
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
    "analytics",
    "audit",
    "auth",
    "challenge_details",
    "challenges",
    "dashboard",
    "health",
    "members",
    "realtime",
    "solves",
    "stats",
    "teams",
]
