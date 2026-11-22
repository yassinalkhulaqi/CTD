"""Pure domain model for the achievement and badge engine.

The types in this module deliberately contain no persistence or transport
concerns. Every calculation is a pure function of its arguments so the criteria
engine can be exercised without a database and reused by both the API and the
frontend contract.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from ctf_team_dashboard.domain.enums import StrEnum
from ctf_team_dashboard.domain.models import utcnow

SECRET_NAME = "???"
SECRET_DESCRIPTION = "This badge is hidden until it is unlocked."
SECRET_ICON = "question-mark"

METRIC_ALIASES: dict[str, tuple[str, ...]] = {
    "solves": ("solves", "solved", "solve_count", "total_solves"),
    "categories": (
        "categories",
        "categories_solved",
        "unique_categories",
        "category_count",
    ),
    "streak": ("streak", "current_streak", "day_streak", "consecutive_days"),
    "hints": ("hints", "hints_used", "hint_count", "hints_taken"),
}

KNOWN_METRICS: tuple[str, ...] = tuple(METRIC_ALIASES)


class BadgeTier(StrEnum):
    """Prestige tier of a badge."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"

    @property
    def rank(self) -> int:
        """Return the 1-based rank of the tier, bronze being the lowest."""
        return {BadgeTier.BRONZE: 1, BadgeTier.SILVER: 2, BadgeTier.GOLD: 3}[self]

    @property
    def multiplier(self) -> float:
        """Return the score multiplier awarded by this tier."""
        return {BadgeTier.BRONZE: 1.0, BadgeTier.SILVER: 1.5, BadgeTier.GOLD: 2.25}[self]

    @property
    def color(self) -> str:
        """Return the CSS colour token used for this tier."""
        return {
            BadgeTier.BRONZE: "#d08b5b",
            BadgeTier.SILVER: "#b8c4d4",
            BadgeTier.GOLD: "#f5c451",
        }[self]

    @property
    def label(self) -> str:
        """Return the human readable tier label."""
        return self.value.capitalize()

    def next(self) -> BadgeTier | None:
        """Return the next prestige tier, or ``None`` for gold."""
        tiers = list(BadgeTier)
        if self.rank >= len(tiers):
            return None
        return tiers[self.rank]


class CriteriaKind(StrEnum):
    """Metric family used to decide whether a badge is earned."""

    SOLVES = "solves"
    CATEGORIES = "categories"
    STREAK = "streak"
    HINTS = "hints"

    @property
    def unit(self) -> str:
        """Return the short unit shown next to progress counters."""
        return {
            CriteriaKind.SOLVES: "solves",
            CriteriaKind.CATEGORIES: "categories",
            CriteriaKind.STREAK: "days",
            CriteriaKind.HINTS: "hints",
        }[self]

    @property
    def label(self) -> str:
        """Return the human readable criterion label."""
        return {
            CriteriaKind.SOLVES: "Solves",
            CriteriaKind.CATEGORIES: "Categories",
            CriteriaKind.STREAK: "Streak",
            CriteriaKind.HINTS: "Hints",
        }[self]

    @property
    def description(self) -> str:
        """Return the rule description shown on a detail sheet."""
        return {
            CriteriaKind.SOLVES: "Earn the required number of challenge solves.",
            CriteriaKind.CATEGORIES: "Solve challenges in the required number of categories.",
            CriteriaKind.STREAK: "Keep a solve streak for the required number of days.",
            CriteriaKind.HINTS: "Use hints sparingly to earn this recognition badge.",
        }[self]

    def default_targets(self) -> dict[BadgeTier, int]:
        """Return the standard target value for each tier of this criterion."""
        return {
            CriteriaKind.SOLVES: {
                BadgeTier.BRONZE: 5,
                BadgeTier.SILVER: 15,
                BadgeTier.GOLD: 35,
            },
            CriteriaKind.CATEGORIES: {
                BadgeTier.BRONZE: 2,
                BadgeTier.SILVER: 4,
                BadgeTier.GOLD: 6,
            },
            CriteriaKind.STREAK: {
                BadgeTier.BRONZE: 3,
                BadgeTier.SILVER: 7,
                BadgeTier.GOLD: 14,
            },
            CriteriaKind.HINTS: {
                BadgeTier.BRONZE: 8,
                BadgeTier.SILVER: 4,
                BadgeTier.GOLD: 1,
            },
        }[self]

    def target_for(self, tier: BadgeTier) -> int:
        """Return the default target for ``tier``."""
        return self.default_targets()[tier]


def clamp(value: float, lower: float, upper: float) -> float:
    """Restrict ``value`` to the inclusive ``lower``/``upper`` interval."""
    return max(lower, min(upper, value))


def progress_percent(current: int, target: int) -> float:
    """Compute a clamped, rounded completion percentage.

    Args:
        current: The observed metric value.
        target: The threshold required for the badge.

    Returns:
        A number between ``0.0`` and ``100.0`` rounded to one decimal place.
        A non-positive target always yields ``0.0``.
    """
    if target <= 0:
        return 0.0
    return round(clamp(current / target * 100.0, 0.0, 100.0), 1)


def effective_points(base: int, tier: BadgeTier) -> int:
    """Apply the tier score multiplier to a base point value."""
    return max(0, round(max(0, base) * tier.multiplier))


def parse_metric_number(value: Any) -> float:
    """Coerce a metric input to a non-negative finite float.

    Booleans are interpreted as ``1``/``0`` and unparseable values are ignored
    by returning zero. Infinity and NaN are rejected for determinism.
    """
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        numeric = float(value)
    elif isinstance(value, str):
        try:
            numeric = float(value.strip())
        except ValueError:
            return 0.0
    else:
        return 0.0
    if numeric != numeric or numeric in (float("inf"), float("-inf")):
        return 0.0
    return max(0.0, numeric)


def normalise_metrics(raw: Mapping[str, Any] | None) -> dict[str, float]:
    """Normalise a metrics dictionary into the four canonical criteria keys.

    Aliases such as ``hints_used`` or ``unique_categories`` are folded into the
    canonical key. When several aliases are supplied the largest wins, which
    prevents an older client from accidentally reducing progress.
    """
    source = dict(raw or {})
    normalised: dict[str, float] = dict.fromkeys(KNOWN_METRICS, 0.0)
    for canonical, aliases in METRIC_ALIASES.items():
        candidate = max(
            (parse_metric_number(source.get(alias)) for alias in aliases),
            default=0.0,
        )
        normalised[canonical] = candidate
    return normalised


def metric_value(metrics: Mapping[str, float], kind: CriteriaKind) -> float:
    """Read the canonical metric value for ``kind`` from a normalised mapping."""
    return float(metrics.get(kind.value, 0.0))


def criteria_value(metrics: Mapping[str, float], kind: CriteriaKind, target: int) -> int:
    """Return the observed integer value used to evaluate a criterion.

    Hint badges are inverted: the target is the maximum number of hints a
    member may take. Observed progress is therefore the remaining allowance,
    capped at the target. All other criteria count upward.
    """
    raw = int(metric_value(metrics, kind))
    if kind is CriteriaKind.HINTS:
        return int(clamp(target - raw, 0, target))
    return max(0, raw)


def rarity_score(holders: int, members: int) -> float:
    """Return a 0-100 score describing how rare a badge is.

    A badge held by nobody scores 100 because it has not been diluted yet.
    With no members in the competition the score is zero.
    """
    if members <= 0:
        return 0.0
    return round(clamp((1.0 - holders / members) * 100.0, 0.0, 100.0), 1)


def rarity_label(score: float) -> str:
    """Translate a rarity score into a stable display band."""
    if score >= 90.0:
        return "legendary"
    if score >= 70.0:
        return "rare"
    if score >= 40.0:
        return "uncommon"
    return "common"


def deterministic_award_id(badge_id: str, member_id: str) -> str:
    """Return a stable award identifier derived from its natural key."""
    digest = hashlib.sha256(f"{badge_id}:{member_id}".encode()).hexdigest()
    return f"award-{digest[:16]}"


def award_evidence(
    badge: Badge,
    metrics: Mapping[str, float],
    observed: int,
) -> dict[str, Any]:
    """Build the immutable evidence payload stored alongside an award."""
    return {
        "criteria_kind": badge.criteria_kind.value,
        "criteria_value": badge.criteria_value,
        "observed": observed,
        "tier": badge.tier.value,
        "metrics": {key: round(value, 2) for key, value in sorted(metrics.items())},
    }


def is_recent(timestamp: datetime, *, now: datetime | None = None, hours: int = 24) -> bool:
    """Return whether a timestamp falls inside the recent window."""
    reference = now if now is not None else utcnow()
    return timestamp >= reference - timedelta(hours=hours)


@dataclass(frozen=True, slots=True)
class Badge:
    """A configurable achievement definition."""

    id: str
    name: str
    description: str
    tier: BadgeTier
    criteria_kind: CriteriaKind
    criteria_value: int
    icon: str = "trophy"
    points: int = 100
    secret: bool = False

    @property
    def target(self) -> int:
        """Alias for the criterion threshold used by progress records."""
        return self.criteria_value

    @property
    def metric_key(self) -> str:
        """Return the canonical metric key evaluated by this badge."""
        return self.criteria_kind.value

    @property
    def score(self) -> int:
        """Return the tier-adjusted score granted by this badge."""
        return effective_points(self.points, self.tier)

    @property
    def tier_rank(self) -> int:
        """Return the numeric rank of the badge tier."""
        return self.tier.rank

    @property
    def criteria_label(self) -> str:
        """Return a compact human readable criterion description."""
        if self.criteria_kind is CriteriaKind.HINTS:
            return f"Use at most {self.criteria_value} hints"
        if self.criteria_kind is CriteriaKind.STREAK:
            return f"Maintain a {self.criteria_value}-day solve streak"
        if self.criteria_kind is CriteriaKind.CATEGORIES:
            return f"Solve {self.criteria_value} categories"
        return f"Score {self.criteria_value} solves"

    def evaluate(self, metrics: Mapping[str, float]) -> BadgeEvaluation:
        """Evaluate this badge against a normalised metrics mapping."""
        observed = criteria_value(metrics, self.criteria_kind, self.criteria_value)
        percent = progress_percent(observed, self.criteria_value)
        return BadgeEvaluation(
            badge_id=self.id,
            member_id="",
            current=observed,
            target=self.criteria_value,
            percent=percent,
            qualifies=observed >= self.criteria_value and self.criteria_value > 0,
            criteria_kind=self.criteria_kind,
            tier=self.tier,
        )


@dataclass(frozen=True, slots=True)
class BadgeEvaluation:
    """The result of evaluating one badge against one member's metrics."""

    badge_id: str
    member_id: str
    current: int
    target: int
    percent: float
    qualifies: bool
    criteria_kind: CriteriaKind
    tier: BadgeTier

    @property
    def remaining(self) -> int:
        """Return how much of the criterion is still outstanding."""
        return max(0, self.target - self.current)

    @property
    def status(self) -> str:
        """Return a stable status token for UI rendering."""
        if self.qualifies:
            return "earned"
        if self.percent >= 75.0:
            return "almost"
        if self.percent > 0.0:
            return "in-progress"
        return "locked"

    def with_member(self, member_id: str) -> BadgeEvaluation:
        """Return a copy bound to a member identifier."""
        return BadgeEvaluation(
            badge_id=self.badge_id,
            member_id=member_id,
            current=self.current,
            target=self.target,
            percent=self.percent,
            qualifies=self.qualifies,
            criteria_kind=self.criteria_kind,
            tier=self.tier,
        )


@dataclass(frozen=True, slots=True)
class AchievementAward:
    """An immutable record that a member earned a badge."""

    id: str
    badge_id: str
    member_id: str
    awarded_at: datetime
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def is_fresh(self) -> bool:
        """Return whether the award was granted in the last 24 hours."""
        return is_recent(self.awarded_at)

    @property
    def observed_value(self) -> int:
        """Return the metric value recorded at award time."""
        value = self.evidence.get("observed", 0)
        return int(value) if isinstance(value, (int, float)) else 0

    @property
    def evidence_summary(self) -> str:
        """Return a compact textual summary of the evidence."""
        kind = str(self.evidence.get("criteria_kind", "criteria"))
        return f"{kind}: {self.observed_value}"


@dataclass(frozen=True, slots=True)
class AchievementProgress:
    """The running progress of a member towards one badge."""

    member_id: str
    badge_id: str
    current: int
    target: int

    @property
    def ratio(self) -> float:
        """Return the completion ratio between zero and one."""
        return progress_percent(self.current, self.target) / 100.0

    @property
    def percent(self) -> float:
        """Return the completion percentage."""
        return progress_percent(self.current, self.target)

    @property
    def remaining(self) -> int:
        """Return the outstanding amount of work."""
        return max(0, self.target - self.current)

    @property
    def is_complete(self) -> bool:
        """Return whether the progress record has reached its target."""
        return self.target > 0 and self.current >= self.target

    def advanced_to(self, value: int) -> AchievementProgress:
        """Return a copy with monotonic progress applied."""
        if value <= self.current:
            return self
        return AchievementProgress(
            member_id=self.member_id,
            badge_id=self.badge_id,
            current=min(value, self.target),
            target=self.target,
        )


@dataclass(frozen=True, slots=True)
class BadgeView:
    """A badge prepared for presentation to a particular member."""

    badge: Badge
    progress: AchievementProgress | None
    awarded: bool
    revealed: bool
    rarity: float
    holders: int = 0

    @property
    def display_name(self) -> str:
        """Return the visible name, respecting secret masking."""
        return self.badge.name if self.revealed else SECRET_NAME

    @property
    def display_description(self) -> str:
        """Return the visible description, respecting secret masking."""
        return self.badge.description if self.revealed else SECRET_DESCRIPTION

    @property
    def display_icon(self) -> str:
        """Return the visible icon token, respecting secret masking."""
        return self.badge.icon if self.revealed else SECRET_ICON

    @property
    def current(self) -> int:
        """Return the observed progress value."""
        return self.progress.current if self.progress is not None else 0

    @property
    def target(self) -> int:
        """Return the progress target."""
        return self.progress.target if self.progress is not None else self.badge.target

    @property
    def percent(self) -> float:
        """Return the progress percentage."""
        return self.progress.percent if self.progress is not None else 0.0

    @property
    def rarity_band(self) -> str:
        """Return the rarity band of the badge."""
        return rarity_label(self.rarity)

    @property
    def status(self) -> str:
        """Return a single display status token."""
        if self.awarded:
            return "unlocked"
        if self.current >= self.target and self.target > 0:
            return "ready"
        return "locked"


@dataclass(frozen=True, slots=True)
class EvaluationOutcome:
    """Everything that happened while evaluating one member and badge."""

    evaluation: BadgeEvaluation
    badge: Badge
    award: AchievementAward | None = None
    progress: AchievementProgress | None = None
    newly_awarded: bool = False

    @property
    def reason(self) -> str:
        """Return a human readable explanation of the outcome."""
        if self.newly_awarded:
            return "Badge unlocked"
        if self.evaluation.qualifies:
            return "Already unlocked"
        if self.evaluation.status == "almost":
            return "Almost there"
        return "Criteria not met"


@dataclass(frozen=True, slots=True)
class AwardOutcome:
    """The result of a manual or automatic badge grant."""

    badge: Badge
    award: AchievementAward | None = None
    awarded: bool = False
    progress: float | None = None

    @property
    def status(self) -> str:
        """Return a stable outcome token for the API response."""
        return "awarded" if self.awarded else "already-owned"


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """The aggregate result of one evaluation request."""

    member_id: str
    metrics: dict[str, float]
    outcomes: tuple[EvaluationOutcome, ...] = ()

    @property
    def evaluated(self) -> int:
        """Return the number of badges evaluated."""
        return len(self.outcomes)

    @property
    def unlocked(self) -> int:
        """Return the number of newly awarded badges."""
        return sum(1 for outcome in self.outcomes if outcome.newly_awarded)

    @property
    def eligible(self) -> int:
        """Return the number of badges whose criteria are currently met."""
        return sum(1 for outcome in self.outcomes if outcome.evaluation.qualifies)

    @property
    def unlocked_badges(self) -> tuple[Badge, ...]:
        """Return the badges that were unlocked by this evaluation."""
        return tuple(outcome.badge for outcome in self.outcomes if outcome.newly_awarded)


@dataclass(frozen=True, slots=True)
class LeaderboardRow:
    """One row of the member achievement leaderboard."""

    member_id: str
    handle: str
    display_name: str
    awards: int
    points: int
    rank: int = 0
    rarity: float = 0.0

    @property
    def label(self) -> str:
        """Return the preferred display name of the member."""
        return self.display_name or self.handle

    def with_rank(self, rank: int) -> LeaderboardRow:
        """Return a copy carrying an explicit rank."""
        return LeaderboardRow(
            member_id=self.member_id,
            handle=self.handle,
            display_name=self.display_name,
            awards=self.awards,
            points=self.points,
            rank=rank,
            rarity=self.rarity,
        )


def rank_rows(rows: Sequence[LeaderboardRow]) -> list[LeaderboardRow]:
    """Rank leaderboard rows with dense ties and stable ordering."""
    ordered = sorted(
        rows,
        key=lambda row: (-row.points, -row.awards, row.label.lower(), row.member_id),
    )
    ranked: list[LeaderboardRow] = []
    previous_points: int | None = None
    current_rank = 0
    for position, row in enumerate(ordered, start=1):
        if previous_points is None or row.points != previous_points:
            current_rank = position
            previous_points = row.points
        ranked.append(row.with_rank(current_rank))
    return ranked


@dataclass(frozen=True, slots=True)
class AchievementStats:
    """Aggregated counters rendered by the achievement overview."""

    badges: int
    awards: int
    members_with_awards: int
    members: int
    points: int
    secret_badges: int
    gold_badges: int
    recent_awards: int
    average_rarity: float = 0.0

    @property
    def participation_rate(self) -> float:
        """Return the share of members who own at least one badge."""
        if self.members <= 0:
            return 0.0
        return round(self.members_with_awards / self.members * 100.0, 1)

    @property
    def completion_rate(self) -> float:
        """Return the share of the catalogue that has been awarded at least once."""
        if self.badges <= 0:
            return 0.0
        return round(min(self.awards, self.badges) / self.badges * 100.0, 1)

    @property
    def points_per_member(self) -> float:
        """Return the mean achievement score across all members."""
        if self.members <= 0:
            return 0.0
        return round(self.points / self.members, 1)


@dataclass(frozen=True, slots=True)
class MemberSummary:
    """A complete achievement view for one member."""

    member_id: str
    awards: tuple[AchievementAward, ...] = ()
    progress: tuple[AchievementProgress, ...] = ()
    views: tuple[BadgeView, ...] = ()
    points: int = 0

    @property
    def unlocked(self) -> int:
        """Return the number of badges this member owns."""
        return len(self.awards)

    @property
    def completion(self) -> float:
        """Return the mean progress percentage across all badges."""
        if not self.views:
            return 0.0
        return round(sum(view.percent for view in self.views) / len(self.views), 1)

    @property
    def next_badge(self) -> BadgeView | None:
        """Return the closest badge that has not been unlocked yet."""
        candidates = [view for view in self.views if not view.awarded]
        if not candidates:
            return None
        return max(candidates, key=lambda view: (view.percent, -view.target))

    def recent_awards(self, limit: int = 3) -> tuple[AchievementAward, ...]:
        """Return the most recently granted awards."""
        ordered = sorted(self.awards, key=lambda award: award.awarded_at, reverse=True)
        return tuple(ordered[: max(0, limit)])


def merge_views(
    badges: Iterable[Badge],
    progress: Mapping[str, AchievementProgress],
    awarded_ids: Iterable[str],
    rarity: Mapping[str, float],
    holders: Mapping[str, int],
    viewer_member_id: str | None = None,
) -> list[BadgeView]:
    """Combine domain records into presentation-ready badge views.

    Secret badges stay masked unless the viewer owns them. Ownership is
    deliberately checked by ``viewer_member_id`` rather than trusting a client
    flag, so a caller cannot peek at hidden criteria.
    """
    awarded = set(awarded_ids)
    views: list[BadgeView] = []
    for badge in badges:
        revealed = not badge.secret or badge.id in awarded
        views.append(
            BadgeView(
                badge=badge,
                progress=progress.get(badge.id),
                awarded=badge.id in awarded,
                revealed=revealed,
                rarity=rarity.get(badge.id, 0.0),
                holders=holders.get(badge.id, 0),
            )
        )
    return views
