"""Repository layer for the CTF Team Dashboard."""

from ctf_team_dashboard.repositories.base import BaseRepository
from ctf_team_dashboard.repositories.challenges import ChallengeRepository
from ctf_team_dashboard.repositories.credentials import ApiKeyRepository, SessionRepository
from ctf_team_dashboard.repositories.events import EventRepository
from ctf_team_dashboard.repositories.members import MemberRepository
from ctf_team_dashboard.repositories.notes import NoteRepository
from ctf_team_dashboard.repositories.solves import SolveRepository
from ctf_team_dashboard.repositories.teams import TeamRepository
from ctf_team_dashboard.repositories.users import UserRepository


class Repositories:
    """Container bundling every repository used by the service layer."""

    def __init__(
        self,
        teams: TeamRepository | None = None,
        members: MemberRepository | None = None,
        challenges: ChallengeRepository | None = None,
        solves: SolveRepository | None = None,
        events: EventRepository | None = None,
        users: UserRepository | None = None,
        api_keys: ApiKeyRepository | None = None,
        sessions: SessionRepository | None = None,
        notes: NoteRepository | None = None,
    ) -> None:
        self.teams = teams or TeamRepository()
        self.members = members or MemberRepository()
        self.challenges = challenges or ChallengeRepository()
        self.solves = solves or SolveRepository()
        self.events = events or EventRepository()
        self.users = users or UserRepository()
        self.api_keys = api_keys or ApiKeyRepository()
        self.sessions = sessions or SessionRepository()
        self.notes = notes or NoteRepository()

    def execute(self, sql: str, params: tuple[object, ...] = ()) -> int:
        """Execute a raw mutating statement against the shared database."""
        return self.events.execute(sql, params)


__all__ = [
    "ApiKeyRepository",
    "BaseRepository",
    "ChallengeRepository",
    "EventRepository",
    "MemberRepository",
    "NoteRepository",
    "Repositories",
    "SessionRepository",
    "SolveRepository",
    "TeamRepository",
    "UserRepository",
]
