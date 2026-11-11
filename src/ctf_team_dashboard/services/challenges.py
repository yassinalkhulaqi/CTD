"""Challenge oriented application services."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from ctf_team_dashboard.domain.enums import (
    ChallengeCategory,
    ChallengeStatus,
    Difficulty,
    EventKind,
)
from ctf_team_dashboard.domain.models import Challenge
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.repositories import Repositories


class ChallengeService:
    """Business rules for the challenge board."""

    def __init__(self, repositories: Repositories | None = None) -> None:
        self.repositories = repositories or Repositories()

    def list_challenges(
        self,
        team_id: str | None = None,
        *,
        category: ChallengeCategory | None = None,
        status: ChallengeStatus | None = None,
    ) -> list[Challenge]:
        """Return challenges filtered by team, category and status."""
        return self.repositories.challenges.list_all(
            team_id, category=category, status=status
        )

    def get_challenge(self, challenge_id: str) -> Challenge:
        """Return a challenge or raise :class:`NotFoundError`."""
        challenge = self.repositories.challenges.get(challenge_id)
        if challenge is None:
            raise NotFoundError(f"Challenge {challenge_id!r} does not exist")
        return challenge

    def create_challenge(
        self,
        *,
        team_id: str,
        title: str,
        category: ChallengeCategory,
        difficulty: Difficulty,
        points: int = 100,
        description: str = "",
        status: ChallengeStatus = ChallengeStatus.PENDING,
        tags: Sequence[str] = (),
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
        challenge_id: str | None = None,
    ) -> Challenge:
        """Create a challenge after validating the window and points."""
        if self.repositories.teams.get(team_id) is None:
            raise NotFoundError(f"Team {team_id!r} does not exist")
        cleaned_title = title.strip()
        if not cleaned_title:
            raise ValidationError("Challenge title must not be empty")
        if points < 0:
            raise ValidationError("Challenge points must not be negative")
        if starts_at is not None and ends_at is not None and ends_at <= starts_at:
            raise ValidationError("Challenge end time must be after its start time")
        normalised_tags = tuple(
            dict.fromkeys(tag.strip().lower() for tag in tags if tag.strip())
        )
        challenge = Challenge(
            id=challenge_id or f"challenge-{uuid.uuid4().hex[:12]}",
            team_id=team_id,
            title=cleaned_title,
            category=category,
            difficulty=difficulty,
            points=points,
            description=description.strip(),
            status=status,
            tags=normalised_tags,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        self.repositories.challenges.create(challenge)
        self.repositories.events.append(
            EventKind.CHALLENGE_CREATED,
            team_id=team_id,
            payload={"id": challenge.id, "title": challenge.title},
        )
        return challenge

    def update_challenge(
        self,
        challenge_id: str,
        *,
        title: str | None = None,
        category: ChallengeCategory | None = None,
        difficulty: Difficulty | None = None,
        points: int | None = None,
        description: str | None = None,
        status: ChallengeStatus | None = None,
        tags: Sequence[str] | None = None,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
    ) -> Challenge:
        """Apply partial updates to a challenge.

        Args:
            challenge_id: Identifier of the challenge to update.
            title: New title.
            category: New category.
            difficulty: New difficulty tier.
            points: New base point value.
            description: New description.
            status: New lifecycle status.
            tags: New tag list.
            starts_at: New start of the availability window.
            ends_at: New end of the availability window.

        Returns:
            The updated challenge.
        """
        challenge = self.get_challenge(challenge_id)
        resolved_title = (title if title is not None else challenge.title).strip()
        if not resolved_title:
            raise ValidationError("Challenge title must not be empty")
        resolved_points = points if points is not None else challenge.points
        if resolved_points < 0:
            raise ValidationError("Challenge points must not be negative")
        resolved_category = category if category is not None else challenge.category
        resolved_difficulty = difficulty if difficulty is not None else challenge.difficulty
        resolved_status = status if status is not None else challenge.status
        resolved_description = (
            description if description is not None else challenge.description
        )
        resolved_tags = tuple(tags) if tags is not None else challenge.tags
        updated = Challenge(
            id=challenge.id,
            team_id=challenge.team_id,
            title=resolved_title,
            category=resolved_category,
            difficulty=resolved_difficulty,
            points=resolved_points,
            description=resolved_description,
            status=resolved_status,
            tags=resolved_tags,
            starts_at=starts_at if starts_at is not None else challenge.starts_at,
            ends_at=ends_at if ends_at is not None else challenge.ends_at,
            created_at=challenge.created_at,
        )
        self.repositories.challenges.update(updated)
        self.repositories.events.append(
            EventKind.CHALLENGE_UPDATED,
            team_id=challenge.team_id,
            payload={"id": challenge.id, "status": updated.status.value},
        )
        return updated

    def set_status(self, challenge_id: str, status: ChallengeStatus) -> Challenge:
        """Move a challenge to a new lifecycle status."""
        challenge = self.get_challenge(challenge_id)
        self.repositories.challenges.set_status(challenge_id, status)
        updated = Challenge(
            id=challenge.id,
            team_id=challenge.team_id,
            title=challenge.title,
            category=challenge.category,
            difficulty=challenge.difficulty,
            points=challenge.points,
            description=challenge.description,
            status=status,
            tags=challenge.tags,
            starts_at=challenge.starts_at,
            ends_at=challenge.ends_at,
            created_at=challenge.created_at,
        )
        self.repositories.events.append(
            EventKind.CHALLENGE_UPDATED,
            team_id=challenge.team_id,
            payload={"id": challenge.id, "status": status.value},
        )
        return updated

    def delete_challenge(self, challenge_id: str) -> None:
        """Remove a challenge together with its solves."""
        challenge = self.get_challenge(challenge_id)
        self.repositories.challenges.delete(challenge_id)
        self.repositories.events.append(
            EventKind.CHALLENGE_DELETED,
            team_id=challenge.team_id,
            payload={"id": challenge.id, "title": challenge.title},
        )

    def board(self, team_id: str) -> dict[str, list[Challenge]]:
        """Group the challenges of a team by lifecycle status."""
        grouped: dict[str, list[Challenge]] = {status.value: [] for status in ChallengeStatus}
        for challenge in self.list_challenges(team_id):
            grouped[challenge.status.value].append(challenge)
        return grouped

    def ensure_unique_title(self, team_id: str, title: str) -> None:
        """Raise when two challenges of a team share the same title."""
        normalised = title.strip().lower()
        for challenge in self.list_challenges(team_id):
            if challenge.title.strip().lower() == normalised:
                raise ConflictError(f"Challenge {title!r} already exists for this team")
