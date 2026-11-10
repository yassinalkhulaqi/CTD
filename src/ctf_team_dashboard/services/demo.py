"""Demo dataset for the CTF Team Dashboard."""

from __future__ import annotations

from ctf_team_dashboard.models import Challenge, Member, Solve, Team

DEMO_TEAMS: list[Team] = [
    Team(id="team-1", name="RedScribe"),
]

DEMO_MEMBERS: list[Member] = [
    Member(id="member-1", team_id="team-1", handle="analyst", display_name="Analyst One"),
]

DEMO_CHALLENGES: list[Challenge] = [
    Challenge(
        id="challenge-1",
        team_id="team-1",
        title="Web Fundamentals",
        category="web",
        difficulty="easy",
    ),
]

DEMO_SOLVES: list[Solve] = [
    Solve(id="solve-1", challenge_id="challenge-1", member_id="member-1", flag="flag{ctf_demo}"),
]


def load_demo_data() -> tuple[list[Team], list[Member], list[Challenge], list[Solve]]:
    """Return the demo dataset used until persistence is wired up."""
    return (
        list(DEMO_TEAMS),
        list(DEMO_MEMBERS),
        list(DEMO_CHALLENGES),
        list(DEMO_SOLVES),
    )
