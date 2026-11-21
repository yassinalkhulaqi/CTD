"""Typed HTTP schemas for the achievement API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ctf_team_dashboard.features.achievements.models import BadgeTier, CriteriaKind


class AchievementModel(BaseModel):
    """Base model with attribute-based construction enabled."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class BadgeCreate(AchievementModel):
    """Payload used to create a custom badge."""

    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    tier: BadgeTier = BadgeTier.BRONZE
    criteria_kind: CriteriaKind = CriteriaKind.SOLVES
    criteria_value: int = Field(default=1, ge=1, le=1_000_000)
    icon: str = Field(default="trophy", max_length=48)
    points: int = Field(default=100, ge=0, le=100_000)
    secret: bool = False
    id: str | None = Field(default=None, max_length=120)

    @field_validator("name", "icon")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        """Trim surrounding whitespace from textual fields."""
        return value.strip()

    @field_validator("id")
    @classmethod
    def _strip_identifier(cls, value: str | None) -> str | None:
        """Normalise an optional explicit identifier."""
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class BadgeRead(AchievementModel):
    """Public representation of a badge definition."""

    id: str
    name: str
    description: str
    tier: BadgeTier
    criteria_kind: CriteriaKind
    criteria_value: int
    icon: str
    points: int
    secret: bool
    score: int
    target: int
    tier_rank: int
    criteria_label: str
    metric_key: str


class ProgressRead(AchievementModel):
    """A member's progress towards a badge."""

    member_id: str
    badge_id: str
    current: int
    target: int
    percent: float
    remaining: int
    is_complete: bool


class AwardRead(AchievementModel):
    """A badge award granted to a member."""

    id: str
    badge_id: str
    member_id: str
    awarded_at: datetime
    evidence: dict[str, Any] = Field(default_factory=dict)
    observed_value: int = 0
    is_fresh: bool = False


class BadgeWithProgress(AchievementModel):
    """A badge plus the viewer-specific progress and masking information."""

    badge: BadgeRead
    awarded: bool
    revealed: bool
    rarity: float
    holders: int
    current: int
    target: int
    percent: float
    rarity_band: str
    status: str
    display_name: str
    display_description: str
    display_icon: str


class BadgeListResponse(AchievementModel):
    """A filtered badge catalogue response."""

    badges: list[BadgeWithProgress]
    total: int
    tier: BadgeTier | None = None
    criteria_kind: CriteriaKind | None = None


class BadgeDetailResponse(AchievementModel):
    """A single badge detail response."""

    badge: BadgeWithProgress
    awarded_to: int


class EvaluationRequest(AchievementModel):
    """Metrics used to evaluate one member."""

    member_id: str = Field(min_length=1, max_length=120)
    metrics: dict[str, float] = Field(default_factory=dict)


class MemberMetricsInput(AchievementModel):
    """A single member's metrics inside a batch evaluation."""

    member_id: str = Field(min_length=1, max_length=120)
    metrics: dict[str, float] = Field(default_factory=dict)


class BatchEvaluationRequest(AchievementModel):
    """Metrics for several members submitted together."""

    submissions: list[MemberMetricsInput] = Field(default_factory=list, max_length=100)


class EvaluationOutcomeRead(AchievementModel):
    """The result of evaluating one badge."""

    badge_id: str
    member_id: str
    current: int
    target: int
    percent: float
    qualifies: bool
    remaining: int
    status: str
    criteria_kind: CriteriaKind
    tier: BadgeTier
    awarded: bool
    newly_awarded: bool
    reason: str


class EvaluationResultRead(AchievementModel):
    """The result of one member evaluation."""

    member_id: str
    metrics: dict[str, float]
    evaluated: int
    eligible: int
    unlocked: int
    outcomes: list[EvaluationOutcomeRead]


class BatchEvaluationResultRead(AchievementModel):
    """The aggregate response for a batch evaluation."""

    results: list[EvaluationResultRead]
    evaluated_members: int
    total_unlocked: int


class AwardRequest(AchievementModel):
    """Payload for manually granting a badge."""

    evidence: dict[str, Any] = Field(default_factory=dict)


class AwardResult(AchievementModel):
    """Response returned after granting a badge."""

    badge: BadgeRead
    award: AwardRead
    awarded: bool
    progress: float | None = None


class LeaderboardEntry(AchievementModel):
    """One member row of the achievement leaderboard."""

    member_id: str
    handle: str
    display_name: str
    label: str
    awards: int
    points: int
    rank: int
    rarity: float


class LeaderboardResponse(AchievementModel):
    """Leaderboard payload with an explicit member count."""

    entries: list[LeaderboardEntry]
    total: int


class AchievementStatsRead(AchievementModel):
    """Aggregate achievement counters."""

    badges: int
    awards: int
    members_with_awards: int
    members: int
    points: int
    secret_badges: int
    gold_badges: int
    recent_awards: int
    average_rarity: float
    participation_rate: float
    completion_rate: float
    points_per_member: float


class MemberAchievementResponse(AchievementModel):
    """The complete achievement profile of a member."""

    member_id: str
    points: int
    unlocked: int
    completion: float
    next_badge: BadgeWithProgress | None = None
    awards: list[AwardRead]
    progress: list[ProgressRead]
    badges: list[BadgeWithProgress]


class SeedResultRead(AchievementModel):
    """Result of seeding the built-in badge catalogue."""

    created: int
    total: int
