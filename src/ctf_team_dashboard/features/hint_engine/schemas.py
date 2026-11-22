"""Typed request and response schemas for the hint engine API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ctf_team_dashboard.features.hint_engine.models import HintState


class HintApiModel(BaseModel):
    """Shared serialisation configuration for hint schemas."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CostPointRead(HintApiModel):
    """One tier of the geometric cost curve."""

    tier: int
    cost: int
    cumulative: int
    label: str


class HintCreate(HintApiModel):
    """Payload used to author a new hint."""

    challenge_id: str = Field(min_length=1)
    tier: int = Field(ge=1, le=3)
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=4_000)
    base_cost: int = Field(gt=0, le=10_000)
    multiplier: float = Field(default=2.0, ge=1, le=10)
    reveal_after_seconds: int = Field(default=0, ge=0, le=86_400)
    is_active: bool = True


class HintUpdate(HintApiModel):
    """Partial update of an existing hint."""

    tier: int | None = Field(default=None, ge=1, le=3)
    title: str | None = Field(default=None, min_length=1, max_length=120)
    content: str | None = Field(default=None, min_length=1, max_length=4_000)
    base_cost: int | None = Field(default=None, gt=0, le=10_000)
    multiplier: float | None = Field(default=None, ge=1, le=10)
    reveal_after_seconds: int | None = Field(default=None, ge=0, le=86_400)
    is_active: bool | None = None


class HintRead(HintApiModel):
    """The full hint record returned to authors."""

    id: str
    challenge_id: str
    tier: int
    title: str
    content: str
    cost: int
    base_cost: int
    multiplier: float
    reveal_after_seconds: int
    is_active: bool
    teaser: str
    curve: list[CostPointRead]
    created_at: datetime
    updated_at: datetime


class HintUnlockRequest(HintApiModel):
    """Payload used to spend budget on a hint."""

    member_id: str = Field(min_length=1)
    team_id: str = Field(min_length=1)


class HintUnlockRead(HintApiModel):
    """A ledger row returned after a successful reveal."""

    id: str
    hint_id: str
    member_id: str
    team_id: str
    cost_paid: int
    unlocked_at: datetime


class HintBudgetRead(HintApiModel):
    """A team's hint allowance at a point in time."""

    team_id: str
    total: int
    spent: int
    remaining: int
    reset_at: datetime
    created_at: datetime
    utilization: float
    is_exhausted: bool


class BudgetResetRequest(HintApiModel):
    """Optional settings applied when a budget is reset."""

    total: int | None = Field(default=None, gt=0, le=1_000_000)
    reset_after_seconds: int = Field(default=604_800, ge=1, le=31_536_000)


class HintViewRead(HintApiModel):
    """A hint as displayed to one team, with masking applied."""

    hint_id: str
    challenge_id: str
    tier: int
    title: str
    content: str
    cost: int
    reveal_after_seconds: int
    is_active: bool
    state: HintState
    reason: str
    remaining_seconds: int
    required_tier: int | None
    unlocked: bool
    eligible: bool
    badge_label: str
    unlocked_at: datetime | None = None
    unlocked_by: str | None = None


class ChallengeHintViewRead(HintApiModel):
    """The complete hint ladder for a challenge and team."""

    challenge_id: str
    team_id: str
    hints: list[HintViewRead]
    budget: HintBudgetRead
    curve: list[CostPointRead]
    unlocked_count: int


class LedgerEntryRead(HintApiModel):
    """A single row of the reveal history."""

    id: str
    hint_id: str
    hint_title: str
    tier: int
    member_id: str
    member_handle: str
    team_id: str
    cost_paid: int
    unlocked_at: datetime
    description: str


class TierSpendRead(HintApiModel):
    """Spend aggregated at one tier."""

    tier: int
    unlocks: int
    spent: int
    average_cost: float


class TeamSpendSummaryRead(HintApiModel):
    """A team's budget usage, broken down by tier."""

    team_id: str
    total: int
    spent: int
    remaining: int
    unlock_count: int
    utilization: float
    average_cost: float
    by_tier: list[TierSpendRead]


class HintLedgerRead(HintApiModel):
    """Ledger response combining history with the spend summary."""

    team_id: str
    entries: list[LedgerEntryRead]
    summary: TeamSpendSummaryRead
