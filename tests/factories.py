"""Test data factories building deterministic domain records."""

from __future__ import annotations

import itertools
from datetime import datetime, timedelta, timezone

from ctf_team_dashboard.domain.enums import (
    ChallengeCategory,
    ChallengeStatus,
    Difficulty,
    MemberRole,
    Presence,
)
from ctf_team_dashboard.domain.models import Challenge, Member, Note, Solve, Team


class Factory:
    """A deterministic factory producing unique domain records."""

    def __init__(self, *, prefix: str = "f") -> None:
        self.prefix = prefix
        self._counter = itertools.count(1)

    def _next(self) -> str:
        """Return the next unique identifier."""
        return f"{self.prefix}-{next(self._counter):04d}"

    def team(
        self,
        *,
        name: str = "Test Team",
        slug: str | None = None,
        color: str = "#6366f1",
        description: str = "",
        created_at: datetime | None = None,
    ) -> Team:
        """Build a team."""
        identifier = self._next()
        return Team(
            id=identifier,
            name=name,
            slug=slug or identifier.replace("-", "-").lower(),
            color=color,
            description=description,
            created_at=created_at or datetime.now(timezone.utc),
        )

    def member(
        self,
        *,
        team_id: str = "team-0001",
        handle: str = "analyst",
        display_name: str = "Analyst",
        role: MemberRole = MemberRole.ANALYST,
        presence: Presence = Presence.OFFLINE,
        joined_at: datetime | None = None,
    ) -> Member:
        """Build a member."""
        return Member(
            id=self._next(),
            team_id=team_id,
            handle=handle,
            display_name=display_name,
            role=role,
            presence=presence,
            joined_at=joined_at or datetime.now(timezone.utc),
        )

    def challenge(
        self,
        *,
        team_id: str = "team-0001",
        title: str = "Test Challenge",
        category: ChallengeCategory = ChallengeCategory.WEB,
        difficulty: Difficulty = Difficulty.EASY,
        points: int = 100,
        description: str = "",
        status: ChallengeStatus = ChallengeStatus.PENDING,
        tags: tuple[str, ...] = (),
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> Challenge:
        """Build a challenge."""
        return Challenge(
            id=self._next(),
            team_id=team_id,
            title=title,
            category=category,
            difficulty=difficulty,
            points=points,
            description=description,
            status=status,
            tags=tags,
            starts_at=starts_at,
            ends_at=ends_at,
            created_at=created_at or datetime.now(timezone.utc),
        )

    def solve(
        self,
        *,
        challenge_id: str = "challenge-0001",
        member_id: str = "member-0001",
        flag: str = "flag{test}",
        points_awarded: int = 100,
        solved_at: datetime | None = None,
    ) -> Solve:
        """Build a solve."""
        return Solve(
            id=self._next(),
            challenge_id=challenge_id,
            member_id=member_id,
            flag=flag,
            points_awarded=points_awarded,
            solved_at=solved_at or datetime.now(timezone.utc),
        )

    def note(
        self,
        *,
        challenge_id: str = "challenge-0001",
        member_id: str = "member-0001",
        body: str = "A note about the challenge.",
        created_at: datetime | None = None,
    ) -> Note:
        """Build a note."""
        moment = created_at or datetime.now(timezone.utc)
        return Note(
            id=self._next(),
            challenge_id=challenge_id,
            member_id=member_id,
            body=body,
            created_at=moment,
            updated_at=moment,
        )


def build_scenario(
    *,
    teams: int = 2,
    members_per_team: int = 3,
    challenges_per_team: int = 4,
    solve_rate: float = 0.5,
    seed: int = 42,
) -> tuple[list[Team], list[Member], list[Challenge], list[Solve]]:
    """Build a complete competition scenario.

    Args:
        teams: The number of teams.
        members_per_team: The number of members of every team.
        challenges_per_team: The number of challenges of every team.
        solve_rate: The ratio of challenges that received a solve.
        seed: The seed of the deterministic generator.

    Returns:
        The teams, members, challenges and solves of the scenario.
    """
    import random

    rng = random.Random(seed)
    factory = Factory(prefix="s")
    now = datetime.now(timezone.utc)

    team_records: list[Team] = []
    member_records: list[Member] = []
    challenge_records: list[Challenge] = []
    solve_records: list[Solve] = []

    for team_index in range(teams):
        team = factory.team(
            name=f"Team {team_index}",
            slug=f"team-{team_index}",
            created_at=now - timedelta(hours=6),
        )
        team_records.append(team)

        for member_index in range(members_per_team):
            member_records.append(
                factory.member(
                    team_id=team.id,
                    handle=f"member{member_index}",
                    display_name=f"Member {member_index}",
                    joined_at=now - timedelta(hours=5),
                )
            )

        for challenge_index in range(challenges_per_team):
            challenge_records.append(
                factory.challenge(
                    team_id=team.id,
                    title=f"Challenge {team_index}-{challenge_index}",
                    category=list(ChallengeCategory)[challenge_index % len(ChallengeCategory)],
                    difficulty=list(Difficulty)[challenge_index % len(Difficulty)],
                    points=100 * (challenge_index + 1),
                    created_at=now - timedelta(hours=4),
                    ends_at=now + timedelta(hours=6),
                )
            )

    for challenge in challenge_records:
        if rng.random() > solve_rate:
            continue
        candidates = [member for member in member_records if member.team_id == challenge.team_id]
        if not candidates:
            continue
        solver = rng.choice(candidates)
        solve_records.append(
            factory.solve(
                challenge_id=challenge.id,
                member_id=solver.id,
                points_awarded=challenge.difficulty_points,
                solved_at=now - timedelta(minutes=rng.randint(1, 240)),
            )
        )

    return team_records, member_records, challenge_records, solve_records
