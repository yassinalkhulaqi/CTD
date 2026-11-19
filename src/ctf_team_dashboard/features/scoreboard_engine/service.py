"""Business rules and orchestration for the configurable scoreboard."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ctf_team_dashboard.domain.models import Team, utcnow
from ctf_team_dashboard.errors import NotFoundError, ValidationError
from ctf_team_dashboard.repositories import Repositories

from .models import (
    MAX_DECAY,
    MAX_MULTIPLIER,
    MAX_RULE_NAME_LENGTH,
    MAX_SCORE,
    MIN_DECAY,
    MIN_MULTIPLIER,
    RankingEntry,
    ScoreBreakdown,
    ScoreRule,
    ScoreSnapshot,
    build_ranking,
    categorize_scores,
    rank_for_team,
    score_solves,
)
from .store import ScoreStore

MAX_FIELD_VALUE = 100_000


def _as_int(values: Mapping[str, object], key: str, default: int) -> int:
    """Read an integer field from a decoded request payload."""
    value = values.get(key, default)
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float, str)):
        return int(value)
    return default


def _as_float(values: Mapping[str, object], key: str, default: float) -> float:
    """Read a floating point field from a decoded request payload."""
    value = values.get(key, default)
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float, str)):
        return float(value)
    return default


@dataclass(frozen=True, slots=True)
class RuleDraft:
    """User supplied values for a scoring rule."""

    name: str
    base_points: int
    difficulty_multiplier: float
    first_blood_bonus: int
    hint_penalty: int
    decay_factor: float
    decay_enabled: bool

    @classmethod
    def from_values(cls, values: Mapping[str, object]) -> RuleDraft:
        """Build a draft from a decoded request payload."""
        return cls(
            name=str(values.get("name", "")),
            base_points=_as_int(values, "base_points", 0),
            difficulty_multiplier=_as_float(values, "difficulty_multiplier", 1.0),
            first_blood_bonus=_as_int(values, "first_blood_bonus", 0),
            hint_penalty=_as_int(values, "hint_penalty", 0),
            decay_factor=_as_float(values, "decay_factor", 1.0),
            decay_enabled=bool(values.get("decay_enabled", False)),
        )


def validate_rule(draft: RuleDraft) -> dict[str, str]:
    """Return a mapping of field names to validation messages.

    An empty mapping means the draft is valid. Keeping validation pure makes
    the same rules available to the API and to the configuration editor UI.
    """
    errors: dict[str, str] = {}
    name = draft.name.strip()
    if not name:
        errors["name"] = "A rule name is required."
    elif len(name) > MAX_RULE_NAME_LENGTH:
        errors["name"] = f"Name must be at most {MAX_RULE_NAME_LENGTH} characters."

    if draft.base_points < 0:
        errors["base_points"] = "Base points cannot be negative."
    elif draft.base_points > MAX_FIELD_VALUE:
        errors["base_points"] = f"Base points cannot exceed {MAX_FIELD_VALUE}."

    if draft.difficulty_multiplier < MIN_MULTIPLIER:
        errors["difficulty_multiplier"] = (
            f"Difficulty multiplier must be at least {MIN_MULTIPLIER}."
        )
    elif draft.difficulty_multiplier > MAX_MULTIPLIER:
        errors["difficulty_multiplier"] = f"Difficulty multiplier cannot exceed {MAX_MULTIPLIER}."

    if draft.first_blood_bonus < 0:
        errors["first_blood_bonus"] = "First blood bonus cannot be negative."
    elif draft.first_blood_bonus > MAX_FIELD_VALUE:
        errors["first_blood_bonus"] = f"Bonus cannot exceed {MAX_FIELD_VALUE}."

    if draft.hint_penalty < 0:
        errors["hint_penalty"] = "Hint penalty cannot be negative."
    elif draft.hint_penalty > MAX_FIELD_VALUE:
        errors["hint_penalty"] = f"Penalty cannot exceed {MAX_FIELD_VALUE}."

    if draft.decay_factor < MIN_DECAY:
        errors["decay_factor"] = f"Decay factor must be at least {MIN_DECAY}."
    elif draft.decay_factor > MAX_DECAY:
        errors["decay_factor"] = f"Decay factor cannot exceed {MAX_DECAY}."

    if draft.base_points + draft.first_blood_bonus > MAX_SCORE:
        errors["base_points"] = "A single solve cannot exceed the maximum score."
    return errors


def raise_for_rule(draft: RuleDraft) -> None:
    """Raise a typed domain error when ``draft`` contains invalid values."""
    errors = validate_rule(draft)
    if errors:
        raise ValidationError("Invalid scoring rule", details={"fields": errors})


class ScoreboardService:
    """Compute live rankings and persist scoring configuration and history."""

    def __init__(
        self,
        store: ScoreStore | None = None,
        repositories: Repositories | None = None,
    ) -> None:
        self.store = store or ScoreStore()
        self.repositories = repositories or Repositories()

    def ensure_team(self, team_id: str) -> Team:
        """Return a team or raise a typed not-found error."""
        team = self.repositories.teams.get(team_id)
        if team is None:
            raise NotFoundError("Team not found", details={"team_id": team_id})
        return team

    def default_rule(self, team_id: str) -> ScoreRule:
        """Return the balanced default policy for a team."""
        return ScoreRule(
            id=f"rule-{team_id}",
            team_id=team_id,
            name="Balanced",
            base_points=100,
            difficulty_multiplier=1.0,
            first_blood_bonus=50,
            hint_penalty=10,
            decay_factor=0.9,
            decay_enabled=True,
            updated_at=utcnow(),
        )

    def get_rule(self, team_id: str) -> ScoreRule:
        """Return a team's stored rule, or the default when none was saved."""
        self.ensure_team(team_id)
        stored = self.store.get_rule(team_id)
        return stored if stored is not None else self.default_rule(team_id)

    def upsert_rule(self, team_id: str, draft: RuleDraft) -> ScoreRule:
        """Validate and persist a team's scoring policy."""
        self.ensure_team(team_id)
        raise_for_rule(draft)
        existing = self.store.get_rule(team_id)
        rule = ScoreRule(
            id=existing.id if existing is not None else f"rule-{team_id}",
            team_id=team_id,
            name=draft.name.strip(),
            base_points=draft.base_points,
            difficulty_multiplier=draft.difficulty_multiplier,
            first_blood_bonus=draft.first_blood_bonus,
            hint_penalty=draft.hint_penalty,
            decay_factor=draft.decay_factor,
            decay_enabled=draft.decay_enabled,
            updated_at=utcnow(),
        )
        return self.store.upsert_rule(rule)

    def breakdown_for(self, team_id: str) -> ScoreBreakdown:
        """Compute the full scored breakdown for one team."""
        team = self.ensure_team(team_id)
        rule = self.get_rule(team_id)
        challenges = self.repositories.challenges.list_all(team_id)
        solves = self.repositories.solves.list_all(team_id=team_id)
        scores = score_solves(rule, challenges, solves)
        return ScoreBreakdown(
            team_id=team.id,
            team_name=team.name,
            rule=rule,
            scores=tuple(scores),
            categories=tuple(categorize_scores(scores, challenges)),
            challenges=len(challenges),
        )

    def live_ranking(self) -> list[RankingEntry]:
        """Compute the ranking of every team from current solves."""
        teams = self.repositories.teams.list_all()
        scores_by_team = {team.id: self.breakdown_for(team.id).scores for team in teams}
        return list(build_ranking(teams, scores_by_team, self.store.latest_ranks()))

    def ranking(self) -> list[RankingEntry]:
        """Alias for the live ranking, exposed for service consumers."""
        return self.live_ranking()

    def create_snapshot(self, team_id: str) -> ScoreSnapshot:
        """Freeze the current score and rank of a team into a snapshot."""
        self.ensure_team(team_id)
        breakdown = self.breakdown_for(team_id)
        ranking = self.live_ranking()
        rank = rank_for_team(ranking, team_id)
        return self.store.insert_snapshot(
            team_id=team_id,
            points=breakdown.total_points,
            solves=breakdown.total_solves,
            rank=rank,
            details=breakdown.to_details(),
        )

    def list_snapshots(self, team_id: str, limit: int = 50) -> list[ScoreSnapshot]:
        """Return the snapshot history of a team, newest first."""
        self.ensure_team(team_id)
        return self.store.list_snapshots(team_id, limit)

    def latest_snapshot(self, team_id: str) -> ScoreSnapshot | None:
        """Return the most recent snapshot of a team."""
        return self.store.latest_snapshot(team_id)

    def snapshot_series(self, team_id: str, limit: int = 20) -> list[int]:
        """Return a team's points over time, oldest first."""
        snapshots = self.list_snapshots(team_id, limit)
        return [snapshot.points for snapshot in reversed(snapshots)]
