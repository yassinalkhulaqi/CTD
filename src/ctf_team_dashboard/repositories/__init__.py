"""Repository layer for the CTF Team Dashboard."""

from ctf_team_dashboard.repositories.base import BaseRepository
from ctf_team_dashboard.repositories.challenges import ChallengeRepository
from ctf_team_dashboard.repositories.events import EventRepository
from ctf_team_dashboard.repositories.members import MemberRepository
from ctf_team_dashboard.repositories.solves import SolveRepository
from ctf_team_dashboard.repositories.teams import TeamRepository


class Repositories:
    """Container bundling every repository used by the service layer."""

    def __init__(
        self,
        teams: TeamRepository | None = None,
        members: MemberRepository | None = None,
        challenges: ChallengeRepository | None = None,
        solves: SolveRepository | None = None,
        events: EventRepository | None = None,
    ) -> None:
        self.teams = teams or TeamRepository()
        self.members = members or MemberRepository()
        self.challenges = challenges or ChallengeRepository()
        self.solves = solves or SolveRepository()
        self.events = events or EventRepository()

    def execute(self, sql: str, params: tuple[object, ...] = ()) -> int:
        """Execute a raw mutating statement against the shared database."""
        return self.events.execute(sql, params)


__all__ = [
    "BaseRepository",
    "ChallengeRepository",
    "EventRepository",
    "MemberRepository",
    "Repositories",
    "SolveRepository",
    "TeamRepository",
]
