"""Typed API schemas for the configurable scoreboard engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from ctf_team_dashboard.schemas import ApiModel

from .models import RankMovement


class ScoreRuleWrite(BaseModel):
    """Payload accepted when configuring a team's scoring policy."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    base_points: int
    difficulty_multiplier: float
    first_blood_bonus: int
    hint_penalty: int
    decay_factor: float
    decay_enabled: bool


class ScoreRuleRead(ApiModel):
    """The stored scoring policy of a team."""

    id: str
    team_id: str
    name: str
    base_points: int
    difficulty_multiplier: float
    first_blood_bonus: int
    hint_penalty: int
    decay_factor: float
    decay_enabled: bool
    updated_at: datetime
    summary: str


class ScoreSnapshotRead(ApiModel):
    """A persisted scoring snapshot."""

    id: str
    team_id: str
    recorded_at: datetime
    points: int
    solves: int
    rank: int
    details_json: str
    details: dict[str, Any]
    label: str
    rule_name: str


class RankingEntryRead(ApiModel):
    """One row of the live ranking table."""

    team_id: str
    team_name: str
    points: int
    solves: int
    rank: int
    previous_rank: int | None
    movement: RankMovement
    movement_label: str
    last_solve_at: datetime | None


class RankingResponse(ApiModel):
    """The complete live ranking with its generation timestamp."""

    entries: list[RankingEntryRead]
    team_count: int
    generated_at: datetime
    leader_points: int
    total_points: int


class SolveScoreRead(ApiModel):
    """An itemised solve score used by the breakdown chart."""

    solve_id: str
    challenge_id: str
    title: str
    category: str
    category_label: str
    difficulty: str
    solve_index: int
    solved_at: datetime
    base_points: float
    difficulty_weight: float
    difficulty_multiplier: float
    decay: float
    first_blood: bool
    bonus_points: int
    hint_count: int
    penalty_points: int
    points: int
    formula: str


class CategoryScoreRead(ApiModel):
    """Points and solves aggregated for one challenge category."""

    category: str
    label: str
    accent: str
    points: int
    solves: int
    challenges: int
    solve_rate: float
    share: float


class ScoreBreakdownRead(ApiModel):
    """Everything needed to explain one team's total."""

    team_id: str
    team_name: str
    rule: ScoreRuleRead
    total_points: int
    total_solves: int
    first_bloods: int
    hint_penalties: int
    decay_loss: float
    average_points: float
    challenges: int
    generated_at: datetime
    categories: list[CategoryScoreRead]
    solves: list[SolveScoreRead]
