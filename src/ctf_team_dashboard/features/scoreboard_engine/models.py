"""Domain models and pure calculation helpers for the scoreboard engine."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ctf_team_dashboard.domain.enums import (
    ChallengeCategory,
    Difficulty,
    StrEnum,
)
from ctf_team_dashboard.domain.models import Challenge, Solve, Team, ensure_utc, utcnow

MIN_SCORE = 0
MAX_SCORE = 1_000_000
MIN_MULTIPLIER = 0.1
MAX_MULTIPLIER = 10.0
MIN_DECAY = 0.05
MAX_DECAY = 1.0
MAX_RULE_NAME_LENGTH = 64
_NO_LAST_SOLVE = datetime.max.replace(tzinfo=timezone.utc)


class RankMovement(StrEnum):
    """Direction a team moved between two ranking snapshots."""

    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    NEW = "new"

    @property
    def glyph(self) -> str:
        """Return the compact arrow used by the UI."""
        return {
            RankMovement.UP: "↑",
            RankMovement.DOWN: "↓",
            RankMovement.STABLE: "=",
            RankMovement.NEW: "•",
        }[self]

    @property
    def label(self) -> str:
        """Return a human readable description of the movement."""
        return {
            RankMovement.UP: "Climbed",
            RankMovement.DOWN: "Fell",
            RankMovement.STABLE: "Unchanged",
            RankMovement.NEW: "New entry",
        }[self]

    @property
    def tone(self) -> str:
        """Return the semantic colour tone used by the badge."""
        return {
            RankMovement.UP: "success",
            RankMovement.DOWN: "danger",
            RankMovement.STABLE: "neutral",
            RankMovement.NEW: "info",
        }[self]


@dataclass(frozen=True, slots=True)
class ScoreRule:
    """The configurable scoring policy attached to one team."""

    id: str
    team_id: str
    name: str = "Balanced"
    base_points: int = 100
    difficulty_multiplier: float = 1.0
    first_blood_bonus: int = 50
    hint_penalty: int = 10
    decay_factor: float = 0.9
    decay_enabled: bool = True
    updated_at: datetime = field(default_factory=utcnow)

    @property
    def is_decaying(self) -> bool:
        """Return whether later solves are worth fewer points."""
        return self.decay_enabled and self.decay_factor < MAX_DECAY

    def decay_for(self, solve_index: int) -> float:
        """Return the decay coefficient applied at ``solve_index``."""
        if not self.is_decaying or solve_index <= 0:
            return 1.0
        return self.decay_factor**solve_index

    @property
    def summary(self) -> str:
        """Return a one-line description of the policy."""
        decay = f"decay {self.decay_factor:.2f}" if self.is_decaying else "flat scoring"
        return (
            f"{self.name}: {self.base_points} base × {self.difficulty_multiplier:.2f} "
            f"difficulty, {self.first_blood_bonus} first blood, "
            f"{self.hint_penalty} hint penalty, {decay}"
        )

    def fingerprint(self) -> str:
        """Return a stable short signature used in snapshot details."""
        raw = (
            f"{self.name}|{self.base_points}|{self.difficulty_multiplier}|"
            f"{self.first_blood_bonus}|{self.hint_penalty}|"
            f"{self.decay_factor}|{int(self.decay_enabled)}"
        )
        return f"{abs(hash(raw)) & 0xFFFFFFFF:08x}"


@dataclass(frozen=True, slots=True)
class SolveScore:
    """The fully itemised score awarded for one solve."""

    solve_id: str
    challenge_id: str
    title: str
    category: ChallengeCategory
    difficulty: Difficulty
    solve_index: int
    solved_at: datetime
    base_points: float
    difficulty_weight: float
    difficulty_multiplier: float
    decay: float
    first_blood: bool
    first_blood_bonus: int
    hint_count: int
    hint_penalty: int
    points: int

    @property
    def bonus_points(self) -> int:
        """Return the first blood bonus actually awarded."""
        return self.first_blood_bonus if self.first_blood else 0

    @property
    def penalty_points(self) -> int:
        """Return the total hint penalty applied to this solve."""
        return self.hint_penalty * self.hint_count

    @property
    def weighted_base(self) -> float:
        """Return the base score after difficulty and multiplier."""
        return self.base_points * self.difficulty_weight * self.difficulty_multiplier

    @property
    def decayed_base(self) -> float:
        """Return the score after the decay coefficient."""
        return self.weighted_base * self.decay

    @property
    def formula(self) -> str:
        """Return a printable representation of the scoring arithmetic."""
        return (
            f"{self.base_points:g} × {self.difficulty_weight:g} × "
            f"{self.difficulty_multiplier:g} × {self.decay:g} "
            f"+ {self.bonus_points} − {self.penalty_points} = {self.points}"
        )


@dataclass(frozen=True, slots=True)
class CategoryScoreBreakdown:
    """Aggregated points and solves for one challenge category."""

    category: ChallengeCategory
    points: int
    solves: int
    challenges: int

    @property
    def label(self) -> str:
        """Return the display label of the category."""
        return self.category.label

    @property
    def accent(self) -> str:
        """Return the display colour of the category."""
        return self.category.accent

    @property
    def solve_rate(self) -> float:
        """Return the fraction of challenges solved in the category."""
        if self.challenges <= 0:
            return 0.0
        return self.solves / self.challenges

    def share(self, total_points: int) -> float:
        """Return this category's fraction of ``total_points``."""
        if total_points <= 0:
            return 0.0
        return self.points / total_points


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    """Every score component needed to explain a team's total."""

    team_id: str
    team_name: str
    rule: ScoreRule
    scores: tuple[SolveScore, ...] = ()
    categories: tuple[CategoryScoreBreakdown, ...] = ()
    challenges: int = 0
    generated_at: datetime = field(default_factory=utcnow)

    @property
    def total_points(self) -> int:
        """Return the sum of all awarded solve points."""
        return sum(score.points for score in self.scores)

    @property
    def total_solves(self) -> int:
        """Return the number of scored solves."""
        return len(self.scores)

    @property
    def first_bloods(self) -> int:
        """Return the number of solves awarded a first blood bonus."""
        return sum(1 for score in self.scores if score.first_blood)

    @property
    def hint_penalties(self) -> int:
        """Return the total points removed by hint penalties."""
        return sum(score.penalty_points for score in self.scores)

    @property
    def decay_loss(self) -> float:
        """Return the points lost to decay relative to undiscounted scores."""
        return sum(score.weighted_base - score.decayed_base for score in self.scores)

    @property
    def average_points(self) -> float:
        """Return the mean points per solve."""
        if not self.scores:
            return 0.0
        return self.total_points / self.total_solves

    @property
    def best_solve(self) -> SolveScore | None:
        """Return the highest scoring solve, if any."""
        if not self.scores:
            return None
        return max(self.scores, key=lambda score: score.points)

    def to_details(self) -> dict[str, Any]:
        """Return the JSON-serialisable payload stored with a snapshot."""
        return {
            "rule_name": self.rule.name,
            "rule_id": self.rule.id,
            "rule_fingerprint": self.rule.fingerprint(),
            "team_name": self.team_name,
            "first_bloods": self.first_bloods,
            "hint_penalties": self.hint_penalties,
            "decay_loss": round(self.decay_loss, 2),
            "average_points": round(self.average_points, 2),
            "challenges": self.challenges,
            "categories": [
                {
                    "category": item.category.value,
                    "label": item.label,
                    "points": item.points,
                    "solves": item.solves,
                    "share": round(item.share(self.total_points), 4),
                }
                for item in self.categories
            ],
            "top_solves": [
                {
                    "challenge_id": score.challenge_id,
                    "title": score.title,
                    "points": score.points,
                    "formula": score.formula,
                }
                for score in sorted(self.scores, key=lambda item: -item.points)[:5]
            ],
        }


@dataclass(frozen=True, slots=True)
class ScoreSnapshot:
    """An immutable record of one team's score at a point in time."""

    id: str
    team_id: str
    recorded_at: datetime
    points: int
    solves: int
    rank: int
    details_json: str = "{}"

    @property
    def details(self) -> dict[str, Any]:
        """Decode the snapshot detail payload, tolerating malformed data."""
        if not self.details_json:
            return {}
        try:
            decoded = json.loads(self.details_json)
        except json.JSONDecodeError:
            return {}
        if not isinstance(decoded, dict):
            return {}
        return decoded

    @property
    def label(self) -> str:
        """Return a concise label for the snapshot in a timeline."""
        return f"#{self.rank} · {self.points} pts · {self.solves} solves"

    @property
    def is_podium(self) -> bool:
        """Return whether the snapshot was taken on the podium."""
        return self.rank <= 3

    @property
    def rule_name(self) -> str:
        """Return the scoring rule name captured with the snapshot."""
        return str(self.details.get("rule_name", "Unknown rule"))


@dataclass(frozen=True, slots=True)
class RankingEntry:
    """A single row of the live team ranking."""

    team_id: str
    team_name: str
    points: int
    solves: int
    rank: int
    previous_rank: int | None
    movement: RankMovement
    last_solve_at: datetime | None = None

    @property
    def movement_steps(self) -> int:
        """Return how many positions the team moved since the last snapshot."""
        if self.previous_rank is None:
            return 0
        return abs(self.previous_rank - self.rank)

    @property
    def movement_label(self) -> str:
        """Return the compact movement label used in tables."""
        if self.movement is RankMovement.NEW:
            return "NEW"
        if self.movement is RankMovement.STABLE:
            return "—"
        return f"{self.movement.glyph}{self.movement_steps}"

    @property
    def climbed(self) -> bool:
        """Return whether the team improved its position."""
        return self.movement is RankMovement.UP

    @property
    def descended(self) -> bool:
        """Return whether the team lost positions."""
        return self.movement is RankMovement.DOWN

    @property
    def is_podium(self) -> bool:
        """Return whether the entry belongs on the podium."""
        return self.rank <= 3


def clamp_score(value: float, *, low: int = MIN_SCORE, high: int = MAX_SCORE) -> int:
    """Round a raw score to an integer and clamp it into the legal range."""
    rounded = round(value)
    return max(low, min(high, rounded))


def movement_for(rank: int, previous_rank: int | None) -> RankMovement:
    """Derive a movement direction from a current and previous rank."""
    if previous_rank is None or previous_rank <= 0:
        return RankMovement.NEW
    if rank < previous_rank:
        return RankMovement.UP
    if rank > previous_rank:
        return RankMovement.DOWN
    return RankMovement.STABLE


def score_solve(
    rule: ScoreRule,
    challenge: Challenge,
    solve: Solve,
    *,
    solve_index: int = 0,
    is_first_blood: bool = False,
    hint_count: int = 0,
) -> SolveScore:
    """Compute the itemised score of one solve under ``rule``."""
    weight = challenge.difficulty.weight
    base = float(rule.base_points)
    multiplier = rule.difficulty_multiplier
    decay = rule.decay_for(solve_index)
    bonus = rule.first_blood_bonus if is_first_blood else 0
    hints = max(0, hint_count)
    penalty = rule.hint_penalty * hints
    raw = base * weight * multiplier * decay + bonus - penalty
    return SolveScore(
        solve_id=solve.id,
        challenge_id=challenge.id,
        title=challenge.title,
        category=challenge.category,
        difficulty=challenge.difficulty,
        solve_index=solve_index,
        solved_at=ensure_utc(solve.solved_at),
        base_points=base,
        difficulty_weight=weight,
        difficulty_multiplier=multiplier,
        decay=decay,
        first_blood=is_first_blood,
        first_blood_bonus=bonus,
        hint_count=hints,
        hint_penalty=penalty,
        points=clamp_score(raw),
    )


def compute_solve_points(
    rule: ScoreRule,
    challenge: Challenge,
    solve: Solve,
    *,
    solve_index: int = 0,
    is_first_blood: bool = False,
    hint_count: int = 0,
) -> int:
    """Return only the integer points awarded for one solve."""
    return score_solve(
        rule,
        challenge,
        solve,
        solve_index=solve_index,
        is_first_blood=is_first_blood,
        hint_count=hint_count,
    ).points


def score_solves(
    rule: ScoreRule,
    challenges: Sequence[Challenge],
    solves: Sequence[Solve],
    *,
    hint_counts: Mapping[str, int] | None = None,
) -> list[SolveScore]:
    """Score an ordered collection of solves using a team's rule.

    Solves are processed chronologically so that the decay exponent grows with
    the team's solve index. First blood is determined across every supplied
    solve, not just the ones belonging to the current team.
    """
    challenge_by_id = {challenge.id: challenge for challenge in challenges}
    hints = hint_counts or {}
    first_solve_by_challenge: dict[str, datetime] = {}
    for solve in solves:
        solved_at = ensure_utc(solve.solved_at)
        previous = first_solve_by_challenge.get(solve.challenge_id)
        if previous is None or solved_at < previous:
            first_solve_by_challenge[solve.challenge_id] = solved_at

    ordered = sorted(solves, key=lambda item: (ensure_utc(item.solved_at), item.id))
    scored: list[SolveScore] = []
    for index, solve in enumerate(ordered):
        challenge = challenge_by_id.get(solve.challenge_id)
        if challenge is None:
            continue
        solved_at = ensure_utc(solve.solved_at)
        is_first = first_solve_by_challenge.get(solve.challenge_id) == solved_at
        scored.append(
            score_solve(
                rule,
                challenge,
                solve,
                solve_index=index,
                is_first_blood=is_first,
                hint_count=hints.get(solve.id, 0),
            )
        )
    return scored


def categorize_scores(
    scores: Sequence[SolveScore],
    challenges: Sequence[Challenge],
) -> list[CategoryScoreBreakdown]:
    """Group scored solves and their challenges by category."""
    buckets: dict[ChallengeCategory, list[int]] = {}
    for challenge in challenges:
        entry = buckets.setdefault(challenge.category, [0, 0, 0])
        entry[2] += 1
    for score in scores:
        entry = buckets.setdefault(score.category, [0, 0, 0])
        entry[0] += score.points
        entry[1] += 1
    return [
        CategoryScoreBreakdown(
            category=category,
            points=values[0],
            solves=values[1],
            challenges=values[2],
        )
        for category, values in sorted(
            buckets.items(), key=lambda item: (-item[1][0], item[0].value)
        )
    ]


def build_ranking(
    teams: Sequence[Team],
    scores_by_team: Mapping[str, Sequence[SolveScore]],
    previous_ranks: Mapping[str, int] | None = None,
) -> list[RankingEntry]:
    """Rank teams by points, solves and earliest last solve."""
    previous = previous_ranks or {}
    candidates: list[tuple[Team, int, int, datetime | None]] = []
    for team in teams:
        scores = list(scores_by_team.get(team.id, ()))
        last_solve = max((score.solved_at for score in scores), default=None)
        candidates.append((team, sum(score.points for score in scores), len(scores), last_solve))

    candidates.sort(
        key=lambda item: (
            -item[1],
            -item[2],
            ensure_utc(item[3]) if item[3] is not None else _NO_LAST_SOLVE,
            item[0].name.casefold(),
        )
    )
    return [
        RankingEntry(
            team_id=team.id,
            team_name=team.name,
            points=points,
            solves=solves,
            rank=rank,
            previous_rank=previous.get(team.id),
            movement=movement_for(rank, previous.get(team.id)),
            last_solve_at=last_solve,
        )
        for rank, (team, points, solves, last_solve) in enumerate(candidates, start=1)
    ]


def rank_for_team(ranking: Sequence[RankingEntry], team_id: str) -> int:
    """Return the rank of one team, raising when it is absent."""
    for entry in ranking:
        if entry.team_id == team_id:
            return entry.rank
    raise KeyError(team_id)
