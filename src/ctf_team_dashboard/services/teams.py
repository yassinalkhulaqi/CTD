"""Team oriented application services."""

from __future__ import annotations

import re
import uuid
from collections.abc import Sequence

from ctf_team_dashboard.domain.enums import EventKind
from ctf_team_dashboard.domain.models import Team, TeamScore
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.repositories import Repositories

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


def slugify(value: str) -> str:
    """Return a URL safe slug derived from ``value``."""
    slug = _SLUG_PATTERN.sub("-", value.strip().lower()).strip("-")
    return slug or "team"


class TeamService:
    """Business rules for managing teams and their scoreboard rows."""

    def __init__(self, repositories: Repositories | None = None) -> None:
        self.repositories = repositories or Repositories()

    def list_teams(self) -> list[Team]:
        """Return every known team."""
        return self.repositories.teams.list_all()

    def get_team(self, team_id: str) -> Team:
        """Return a team or raise :class:`NotFoundError`."""
        team = self.repositories.teams.get(team_id)
        if team is None:
            raise NotFoundError(f"Team {team_id!r} does not exist")
        return team

    def create_team(
        self,
        *,
        name: str,
        slug: str | None = None,
        color: str = "#6366f1",
        description: str = "",
        team_id: str | None = None,
    ) -> Team:
        """Create a team, validating the slug and colour."""
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValidationError("Team name must not be empty")
        resolved_slug = slugify(slug or cleaned_name)
        if self.repositories.teams.get_by_slug(resolved_slug) is not None:
            raise ConflictError(f"Team slug {resolved_slug!r} is already taken")
        if not _COLOR_PATTERN.match(color):
            raise ValidationError("Team colour must be a hex value such as '#6366f1'")
        team = Team(
            id=team_id or f"team-{uuid.uuid4().hex[:12]}",
            name=cleaned_name,
            slug=resolved_slug,
            color=color,
            description=description.strip(),
        )
        self.repositories.teams.create(team)
        self.repositories.events.append(
            EventKind.TEAM_UPDATED,
            team_id=team.id,
            payload={"action": "created", "name": team.name},
        )
        return team

    def update_team(
        self,
        team_id: str,
        *,
        name: str | None = None,
        color: str | None = None,
        description: str | None = None,
    ) -> Team:
        """Apply partial updates to a team.

        Args:
            team_id: Identifier of the team to update.
            name: New display name.
            color: New hex accent colour.
            description: New description.

        Returns:
            The updated team.
        """
        team = self.get_team(team_id)
        resolved_name = (name if name is not None else team.name).strip()
        if not resolved_name:
            raise ValidationError("Team name must not be empty")
        resolved_color = color if color is not None else team.color
        if not _COLOR_PATTERN.match(resolved_color):
            raise ValidationError("Team colour must be a hex value such as '#6366f1'")
        resolved_description = description if description is not None else team.description
        updated = Team(
            id=team.id,
            name=resolved_name,
            slug=team.slug,
            color=resolved_color,
            description=resolved_description,
            created_at=team.created_at,
        )
        self.repositories.teams.update(updated)
        self.repositories.events.append(
            EventKind.TEAM_UPDATED,
            team_id=team.id,
            payload={"action": "updated", "name": updated.name},
        )
        return updated

    def delete_team(self, team_id: str) -> None:
        """Delete a team and all of its dependent records."""
        team = self.get_team(team_id)
        self.repositories.teams.delete(team_id)
        self.repositories.events.append(
            EventKind.TEAM_UPDATED,
            payload={"action": "deleted", "name": team.name},
        )

    def scoreboard(self) -> list[TeamScore]:
        """Return the aggregated scoreboard ordered by points then solves."""
        scores = self._build_scoreboard()
        return sorted(scores, key=lambda score: (-score.points, -score.solves, score.team_name))

    def _build_scoreboard(self) -> list[TeamScore]:
        """Compute a scoreboard row for every team."""
        teams = self.repositories.teams.list_all()
        members = self.repositories.members.list_all()
        challenges = self.repositories.challenges.list_all()
        solves = self.repositories.solves.list_all()

        member_count: dict[str, int] = {}
        for member in members:
            member_count[member.team_id] = member_count.get(member.team_id, 0) + 1

        challenge_count: dict[str, int] = {}
        challenge_team: dict[str, str] = {}
        for challenge in challenges:
            challenge_count[challenge.team_id] = challenge_count.get(challenge.team_id, 0) + 1
            challenge_team[challenge.id] = challenge.team_id

        solve_count: dict[str, int] = {}
        point_count: dict[str, int] = {}
        for solve in solves:
            team_id = challenge_team.get(solve.challenge_id)
            if team_id is None:
                continue
            solve_count[team_id] = solve_count.get(team_id, 0) + 1
            point_count[team_id] = point_count.get(team_id, 0) + solve.points_awarded

        return [
            TeamScore(
                team_id=team.id,
                team_name=team.name,
                solves=solve_count.get(team.id, 0),
                points=point_count.get(team.id, 0),
                challenges=challenge_count.get(team.id, 0),
                members=member_count.get(team.id, 0),
            )
            for team in teams
        ]

    def teams_with_members(self) -> list[tuple[Team, Sequence[str]]]:
        """Return each team paired with the handles of its members."""
        members = self.repositories.members.list_all()
        grouped: dict[str, list[str]] = {}
        for member in members:
            grouped.setdefault(member.team_id, []).append(member.handle)
        return [(team, grouped.get(team.id, [])) for team in self.repositories.teams.list_all()]
