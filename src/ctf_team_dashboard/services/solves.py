"""Solve oriented application services."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from ctf_team_dashboard.domain.enums import ChallengeStatus, EventKind
from ctf_team_dashboard.domain.models import Solve, utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.repositories import Repositories


class SolveService:
    """Business rules for recording flag solves."""

    def __init__(self, repositories: Repositories | None = None) -> None:
        self.repositories = repositories or Repositories()

    def list_solves(
        self,
        *,
        member_id: str | None = None,
        challenge_id: str | None = None,
        team_id: str | None = None,
    ) -> list[Solve]:
        """Return solves filtered by member, challenge and team."""
        return self.repositories.solves.list_all(
            member_id=member_id, challenge_id=challenge_id, team_id=team_id
        )

    def get_solve(self, solve_id: str) -> Solve:
        """Return a solve or raise :class:`NotFoundError`."""
        solve = self.repositories.solves.get(solve_id)
        if solve is None:
            raise NotFoundError(f"Solve {solve_id!r} does not exist")
        return solve

    def record_solve(
        self,
        *,
        challenge_id: str,
        member_id: str,
        flag: str = "",
        points_awarded: int | None = None,
        solved_at: datetime | None = None,
        solve_id: str | None = None,
    ) -> Solve:
        """Record a solve and flip the challenge to the solved state."""
        challenge = self.repositories.challenges.get(challenge_id)
        if challenge is None:
            raise NotFoundError(f"Challenge {challenge_id!r} does not exist")
        member = self.repositories.members.get(member_id)
        if member is None:
            raise NotFoundError(f"Member {member_id!r} does not exist")
        if member.team_id != challenge.team_id:
            raise ValidationError("Members may only solve challenges of their own team")
        existing = self.repositories.solves.get_for_pair(challenge_id, member_id)
        if existing is not None:
            raise ConflictError("This member already solved the challenge")
        awarded = challenge.difficulty_points if points_awarded is None else points_awarded
        if awarded < 0:
            raise ValidationError("Awarded points must not be negative")
        solve = Solve(
            id=solve_id or f"solve-{uuid.uuid4().hex[:12]}",
            challenge_id=challenge_id,
            member_id=member_id,
            flag=flag.strip(),
            points_awarded=awarded,
            solved_at=solved_at or utcnow(),
        )
        self.repositories.solves.create(solve)
        self.repositories.challenges.set_status(challenge_id, ChallengeStatus.SOLVED)
        self.repositories.events.append(
            EventKind.SOLVE_CREATED,
            team_id=challenge.team_id,
            payload={
                "id": solve.id,
                "challenge_id": challenge_id,
                "member_id": member_id,
                "points": awarded,
            },
        )
        return solve

    def delete_solve(self, solve_id: str) -> None:
        """Remove a solve and reopen the challenge when it was the last one."""
        solve = self.get_solve(solve_id)
        self.repositories.solves.delete(solve_id)
        remaining = self.repositories.solves.list_all(challenge_id=solve.challenge_id)
        if not remaining:
            self.repositories.challenges.set_status(solve.challenge_id, ChallengeStatus.ACTIVE)
        self.repositories.events.append(
            EventKind.SOLVE_REMOVED,
            payload={"id": solve.id, "challenge_id": solve.challenge_id},
        )

    def solve_velocity(self, team_id: str | None = None) -> list[int]:
        """Return the number of solves per hour over the last 24 hours."""
        now = utcnow()
        buckets = [0] * 24
        solves = self.repositories.solves.solved_at_between(
            now - timedelta(hours=24), now, team_id
        )
        for solve in solves:
            offset = int((now - solve.solved_at).total_seconds() // 3600)
            index = max(0, min(23, 23 - offset))
            buckets[index] += 1
        return buckets
