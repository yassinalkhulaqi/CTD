"""Domain model of the tiered hint engine.

The module keeps the hint economy pure: cost curves, content masking,
eligibility and budget accounting are plain functions of immutable records.
The service layer wires those rules to persistence and the HTTP API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum, IntEnum

from ctf_team_dashboard.domain.models import utcnow

MIN_TIER = 1
MAX_TIER = 3
DEFAULT_VISIBLE_CHARS = 28
MASK_CHARACTER = "*"


class HintTier(IntEnum):
    """The three progressive disclosure levels of a challenge."""

    ONE = 1
    TWO = 2
    THREE = 3

    @classmethod
    def parse(cls, value: int) -> HintTier:
        """Return the tier matching ``value`` or raise :class:`ValueError`."""
        try:
            return cls(int(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Hint tier must be between 1 and 3, got {value!r}") from exc

    @property
    def previous(self) -> HintTier | None:
        """Return the tier immediately below this one, if any."""
        return HintTier(self.value - 1) if self.value > MIN_TIER else None


class HintState(str, Enum):
    """The state of one hint in a team's challenge view."""

    LOCKED = "locked"
    ELIGIBLE = "eligible"
    UNLOCKED = "unlocked"
    EXHAUSTED = "exhausted"


@dataclass(frozen=True, slots=True)
class CostPoint:
    """One point on the geometric cost curve of a hint ladder."""

    tier: int
    cost: int
    cumulative: int = 0

    @property
    def label(self) -> str:
        """Return a compact human readable label."""
        return f"T{self.tier}: {self.cost}"


@dataclass(frozen=True, slots=True)
class Hint:
    """A single tiered hint attached to a challenge."""

    id: str
    challenge_id: str
    tier: int
    title: str
    content: str
    cost: int
    base_cost: int = 25
    multiplier: float = 2.0
    reveal_after_seconds: int = 0
    is_active: bool = True
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    @property
    def tier_enum(self) -> HintTier:
        """Return the validated tier enumeration value."""
        return HintTier.parse(self.tier)

    @property
    def previous_tier(self) -> int | None:
        """Return the tier that must be unlocked before this one."""
        previous = self.tier_enum.previous
        return previous.value if previous is not None else None

    def masked_content(self, visible: int = DEFAULT_VISIBLE_CHARS) -> str:
        """Return the teaser shown to teams that have not unlocked the hint."""
        return mask_content(self.content, visible)


@dataclass(frozen=True, slots=True)
class HintUnlock:
    """An immutable ledger record created when a team spends budget."""

    id: str
    hint_id: str
    member_id: str
    team_id: str
    cost_paid: int
    unlocked_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True, slots=True)
class HintBudget:
    """A team's finite hint allowance for the current competition window."""

    team_id: str
    total: int
    spent: int = 0
    reset_at: datetime = field(default_factory=utcnow)
    created_at: datetime = field(default_factory=utcnow)

    @property
    def remaining(self) -> int:
        """Return the unspent allowance, clamped at zero."""
        return max(0, self.total - self.spent)

    @property
    def utilization(self) -> float:
        """Return the fraction of the allowance already spent."""
        if self.total <= 0:
            return 0.0
        return min(1.0, max(0.0, self.spent / self.total))

    @property
    def is_exhausted(self) -> bool:
        """Return whether the team has no budget left."""
        return self.remaining <= 0

    def can_afford(self, cost: int) -> bool:
        """Return whether a purchase of ``cost`` fits in the allowance."""
        return cost >= 0 and cost <= self.remaining


@dataclass(frozen=True, slots=True)
class Eligibility:
    """The outcome of evaluating the hint rules for one team and hint."""

    state: HintState
    reason: str
    remaining_seconds: int = 0
    required_tier: int | None = None

    @property
    def eligible(self) -> bool:
        """Return whether the hint can be unlocked immediately."""
        return self.state is HintState.ELIGIBLE

    @property
    def unlocked(self) -> bool:
        """Return whether the hint is already revealed."""
        return self.state is HintState.UNLOCKED


@dataclass(frozen=True, slots=True)
class TierSpend:
    """Aggregated unlock spending for a single hint tier."""

    tier: int
    unlocks: int
    spent: int

    @property
    def average_cost(self) -> float:
        """Return the mean price paid at this tier."""
        if self.unlocks == 0:
            return 0.0
        return self.spent / self.unlocks


@dataclass(frozen=True, slots=True)
class TeamSpendSummary:
    """A team's budget usage broken down by hint tier."""

    team_id: str
    total: int
    spent: int
    unlock_count: int
    by_tier: tuple[TierSpend, ...] = ()

    @property
    def remaining(self) -> int:
        """Return the allowance still available to the team."""
        return max(0, self.total - self.spent)

    @property
    def utilization(self) -> float:
        """Return the fraction of the allowance already consumed."""
        if self.total <= 0:
            return 0.0
        return min(1.0, self.spent / self.total)

    @property
    def average_cost(self) -> float:
        """Return the mean price paid per unlocked hint."""
        if self.unlock_count == 0:
            return 0.0
        return self.spent / self.unlock_count


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    """A joined ledger row ready for display in the reveal history."""

    id: str
    hint_id: str
    hint_title: str
    tier: int
    member_id: str
    member_handle: str
    team_id: str
    cost_paid: int
    unlocked_at: datetime

    @property
    def description(self) -> str:
        """Return a one line description of the reveal."""
        return f"{self.member_handle} unlocked tier {self.tier} · {self.hint_title}"


@dataclass(frozen=True, slots=True)
class HintView:
    """A hint as rendered for one team, with content masking applied."""

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
    unlocked_at: datetime | None = None
    unlocked_by: str | None = None

    @property
    def unlocked(self) -> bool:
        """Return whether the full content has been revealed."""
        return self.state is HintState.UNLOCKED

    @property
    def eligible(self) -> bool:
        """Return whether the unlock action should be enabled."""
        return self.state is HintState.ELIGIBLE

    @property
    def badge_label(self) -> str:
        """Return the label shown on the tier card."""
        return {
            HintState.UNLOCKED: "Revealed",
            HintState.ELIGIBLE: "Available",
            HintState.EXHAUSTED: "No budget",
            HintState.LOCKED: "Locked",
        }[self.state]


@dataclass(frozen=True, slots=True)
class ChallengeHintView:
    """The complete hint ladder for one challenge and team."""

    challenge_id: str
    team_id: str
    hints: tuple[HintView, ...]
    budget: HintBudget
    curve: tuple[CostPoint, ...] = ()

    @property
    def unlocked_count(self) -> int:
        """Return the number of hints already revealed."""
        return sum(1 for hint in self.hints if hint.unlocked)

    @property
    def next_hint(self) -> HintView | None:
        """Return the first hint that is currently unlockable."""
        return next((hint for hint in self.hints if hint.eligible), None)


def cost_for_tier(base_cost: int, multiplier: float, tier: int) -> int:
    """Return the rounded price of one tier on a geometric cost curve.

    Args:
        base_cost: Positive price of tier one.
        multiplier: Growth factor applied for every additional tier.
        tier: Ladder position in the inclusive range one to three.

    Returns:
        The price rounded half up to the nearest whole budget unit.

    Raises:
        ValueError: When any of the inputs is outside its supported range.
    """
    if base_cost <= 0:
        raise ValueError("base_cost must be positive")
    if multiplier < 1:
        raise ValueError("multiplier must be at least 1")
    parsed = HintTier.parse(tier)
    raw = Decimal(str(base_cost)) * Decimal(str(multiplier)) ** (parsed.value - 1)
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def cost_curve(base_cost: int, multiplier: float, tiers: int = MAX_TIER) -> tuple[CostPoint, ...]:
    """Return the cumulative price curve for the whole hint ladder.

    Args:
        base_cost: Price of the first tier.
        multiplier: Growth factor between tiers.
        tiers: Number of tiers to include, at most three.

    Returns:
        One :class:`CostPoint` per tier with running totals.
    """
    count = max(MIN_TIER, min(MAX_TIER, tiers))
    points: list[CostPoint] = []
    cumulative = 0
    for tier in range(MIN_TIER, count + 1):
        price = cost_for_tier(base_cost, multiplier, tier)
        cumulative += price
        points.append(CostPoint(tier=tier, cost=price, cumulative=cumulative))
    return tuple(points)


def mask_content(content: str, visible: int = DEFAULT_VISIBLE_CHARS) -> str:
    """Return the public teaser for locked hint content.

    Args:
        content: The full hint text.
        visible: Number of leading characters left in the clear.

    Returns:
        The original text when short enough, otherwise the prefix followed by
        one asterisk for every hidden character.
    """
    if visible < 0:
        raise ValueError("visible must not be negative")
    if len(content) <= visible:
        return content
    return f"{content[:visible]}{MASK_CHARACTER * (len(content) - visible)}"


def evaluate_eligibility(
    hint: Hint,
    *,
    unlocked_tiers: frozenset[int],
    elapsed_seconds: float,
    budget_remaining: int,
) -> Eligibility:
    """Apply the tier, timing and budget rules to one hint.

    Args:
        hint: The hint being evaluated.
        unlocked_tiers: Tiers already revealed by the same team.
        elapsed_seconds: Seconds since the challenge started.
        budget_remaining: The team's remaining hint allowance.

    Returns:
        An :class:`Eligibility` describing the resulting state.
    """
    if not hint.is_active:
        return Eligibility(HintState.LOCKED, "This hint is not active")
    if hint.tier in unlocked_tiers:
        return Eligibility(HintState.UNLOCKED, "Already revealed by your team")
    previous = hint.previous_tier
    if previous is not None and previous not in unlocked_tiers:
        return Eligibility(
            HintState.LOCKED,
            f"Unlock tier {previous} first",
            required_tier=previous,
        )
    remaining = max(0, int(hint.reveal_after_seconds - elapsed_seconds))
    if remaining > 0:
        return Eligibility(
            HintState.LOCKED,
            f"Available in {remaining}s",
            remaining_seconds=remaining,
        )
    if budget_remaining < hint.cost:
        return Eligibility(
            HintState.EXHAUSTED,
            f"Needs {hint.cost} credits, {max(0, budget_remaining)} left",
        )
    return Eligibility(HintState.ELIGIBLE, "Ready to unlock")
