"""Business rules for authoring, unlocking and accounting tiered hints."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from ctf_team_dashboard.domain.models import Challenge, ensure_utc, utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.hint_engine.models import (
    DEFAULT_VISIBLE_CHARS,
    MAX_TIER,
    MIN_TIER,
    ChallengeHintView,
    CostPoint,
    Hint,
    HintBudget,
    HintState,
    HintTier,
    HintUnlock,
    HintView,
    TeamSpendSummary,
    cost_curve,
    cost_for_tier,
    evaluate_eligibility,
)
from ctf_team_dashboard.features.hint_engine.store import HintStore
from ctf_team_dashboard.repositories import Repositories

DEFAULT_BUDGET_TOTAL = 600
DEFAULT_RESET_AFTER_SECONDS = 7 * 24 * 60 * 60
DEFAULT_BASE_COST = 25
DEFAULT_MULTIPLIER = 2.0


class HintService:
    """Coordinate hint authoring, eligibility checks and budget spending."""

    def __init__(
        self,
        store: HintStore | None = None,
        repositories: Repositories | None = None,
    ) -> None:
        self.store = store or HintStore()
        self.repositories = repositories or Repositories()

    # ------------------------------------------------------------------
    # Catalogue
    # ------------------------------------------------------------------
    def _challenge(self, challenge_id: str) -> Challenge:
        """Return a challenge or raise :class:`NotFoundError`."""
        challenge = self.repositories.challenges.get(challenge_id)
        if challenge is None:
            raise NotFoundError(f"Challenge {challenge_id!r} does not exist")
        return challenge

    def get_hint(self, hint_id: str) -> Hint:
        """Return one hint or raise :class:`NotFoundError`."""
        hint = self.store.hints.get(hint_id)
        if hint is None:
            raise NotFoundError(f"Hint {hint_id!r} does not exist")
        return hint

    def list_hints(
        self, *, challenge_id: str | None = None, team_id: str | None = None
    ) -> list[Hint]:
        """Return hints, optionally scoped to a challenge or a team."""
        if challenge_id is not None:
            self._challenge(challenge_id)
        return self.store.hints.list_all(challenge_id=challenge_id, team_id=team_id)

    def _validate_ladder(self, challenge_id: str, tier: int, exclude: str = "") -> None:
        """Ensure the challenge ladder has one hint per tier."""
        HintTier.parse(tier)
        existing = self.store.hints.find_tier(challenge_id, tier)
        if existing is not None and existing.id != exclude:
            raise ConflictError(
                f"Tier {tier} already has a hint on this challenge",
                details={"challenge_id": challenge_id, "tier": tier},
            )

    @staticmethod
    def _clean(text: str, field: str) -> str:
        """Strip surrounding whitespace and reject empty input."""
        cleaned = text.strip()
        if not cleaned:
            raise ValidationError(f"{field} must not be empty")
        return cleaned

    def create_hint(
        self,
        *,
        challenge_id: str,
        tier: int,
        title: str,
        content: str,
        base_cost: int = DEFAULT_BASE_COST,
        multiplier: float = DEFAULT_MULTIPLIER,
        reveal_after_seconds: int = 0,
        is_active: bool = True,
    ) -> Hint:
        """Author a new hint on a challenge ladder.

        Args:
            challenge_id: The challenge that owns the hint.
            tier: Ladder position between one and three.
            title: Short teaser title.
            content: The full text revealed on unlock.
            base_cost: Price of tier one on this ladder.
            multiplier: Growth factor applied for higher tiers.
            reveal_after_seconds: Minimum wait after the challenge starts.
            is_active: Whether the hint may be unlocked.

        Returns:
            The persisted hint.
        """
        self._challenge(challenge_id)
        self._validate_ladder(challenge_id, tier)
        if base_cost <= 0:
            raise ValidationError("base_cost must be positive")
        if multiplier < 1:
            raise ValidationError("multiplier must be at least 1")
        if reveal_after_seconds < 0:
            raise ValidationError("reveal_after_seconds must not be negative")
        now = utcnow()
        hint = Hint(
            id=f"hint-{uuid.uuid4().hex[:12]}",
            challenge_id=challenge_id,
            tier=tier,
            title=self._clean(title, "title"),
            content=self._clean(content, "content"),
            cost=cost_for_tier(base_cost, multiplier, tier),
            base_cost=base_cost,
            multiplier=multiplier,
            reveal_after_seconds=reveal_after_seconds,
            is_active=is_active,
            created_at=now,
            updated_at=now,
        )
        return self.store.hints.create(hint)

    def update_hint(
        self,
        hint_id: str,
        *,
        tier: int | None = None,
        title: str | None = None,
        content: str | None = None,
        base_cost: int | None = None,
        multiplier: float | None = None,
        reveal_after_seconds: int | None = None,
        is_active: bool | None = None,
    ) -> Hint:
        """Update the mutable fields of a hint and recompute its price."""
        current = self.get_hint(hint_id)
        pricing_changed = (
            (tier is not None and tier != current.tier)
            or (base_cost is not None and base_cost != current.base_cost)
            or (multiplier is not None and multiplier != current.multiplier)
        )
        if pricing_changed and self._has_unlocks(hint_id):
            raise ConflictError("Pricing cannot change after the first unlock")

        next_tier = current.tier if tier is None else tier
        next_base = current.base_cost if base_cost is None else base_cost
        next_multiplier = current.multiplier if multiplier is None else multiplier
        if next_base <= 0:
            raise ValidationError("base_cost must be positive")
        if next_multiplier < 1:
            raise ValidationError("multiplier must be at least 1")
        if reveal_after_seconds is not None and reveal_after_seconds < 0:
            raise ValidationError("reveal_after_seconds must not be negative")
        if next_tier != current.tier:
            self._validate_ladder(current.challenge_id, next_tier, exclude=hint_id)

        updated = Hint(
            id=current.id,
            challenge_id=current.challenge_id,
            tier=next_tier,
            title=self._clean(title, "title") if title is not None else current.title,
            content=self._clean(content, "content") if content is not None else current.content,
            cost=cost_for_tier(next_base, next_multiplier, next_tier),
            base_cost=next_base,
            multiplier=next_multiplier,
            reveal_after_seconds=(
                reveal_after_seconds
                if reveal_after_seconds is not None
                else current.reveal_after_seconds
            ),
            is_active=current.is_active if is_active is None else is_active,
            created_at=current.created_at,
            updated_at=utcnow(),
        )
        return self.store.hints.update(updated)

    def _has_unlocks(self, hint_id: str) -> bool:
        """Return whether a hint has already entered the ledger."""
        return (
            int(
                self.store.unlocks.fetch_value(
                    "SELECT COUNT(*) FROM v3_hint_unlocks WHERE hint_id = ?", (hint_id,), 0
                )
                or 0
            )
            > 0
        )

    def delete_hint(self, hint_id: str) -> None:
        """Delete a hint that has never been unlocked."""
        hint = self.get_hint(hint_id)
        if self._has_unlocks(hint_id):
            raise ConflictError(
                "A revealed hint cannot be deleted",
                details={"hint_id": hint.id},
            )
        self.store.hints.delete(hint_id)

    # ------------------------------------------------------------------
    # Budgets
    # ------------------------------------------------------------------
    def _team_exists(self, team_id: str) -> None:
        """Validate that a team identifier is known."""
        if self.repositories.teams.get(team_id) is None:
            raise NotFoundError(f"Team {team_id!r} does not exist")

    def get_budget(self, team_id: str) -> HintBudget:
        """Return a team's budget, provisioning the default on first use."""
        self._team_exists(team_id)
        return self.store.ensure_budget(
            team_id,
            DEFAULT_BUDGET_TOTAL,
            utcnow() + timedelta(seconds=DEFAULT_RESET_AFTER_SECONDS),
        )

    def reset_budget(
        self,
        team_id: str,
        *,
        total: int | None = None,
        reset_after_seconds: int = DEFAULT_RESET_AFTER_SECONDS,
    ) -> HintBudget:
        """Clear a team's spending and move the next reset instant."""
        self._team_exists(team_id)
        current = self.get_budget(team_id)
        if total is not None and total <= 0:
            raise ValidationError("total must be positive")
        if reset_after_seconds <= 0:
            raise ValidationError("reset_after_seconds must be positive")
        return self.store.budgets.reset(
            team_id,
            current.total if total is None else total,
            utcnow() + timedelta(seconds=reset_after_seconds),
        )

    def spend_summary(self, team_id: str) -> TeamSpendSummary:
        """Return the team's budget usage broken down by hint tier."""
        budget = self.get_budget(team_id)
        return TeamSpendSummary(
            team_id=team_id,
            total=budget.total,
            spent=budget.spent,
            unlock_count=self.store.unlocks.count_for_team(team_id),
            by_tier=self.store.unlocks.spend_by_tier(team_id),
        )

    # ------------------------------------------------------------------
    # Unlocking and challenge views
    # ------------------------------------------------------------------
    def _elapsed_seconds(self, challenge: Challenge, now: datetime) -> float:
        """Return the time elapsed since a challenge became available."""
        start = ensure_utc(challenge.starts_at or challenge.created_at)
        return max(0.0, (ensure_utc(now) - start).total_seconds())

    def unlock_hint(
        self,
        hint_id: str,
        *,
        member_id: str,
        team_id: str,
        now: datetime | None = None,
    ) -> HintUnlock:
        """Spend budget to reveal one hint for a team.

        Args:
            hint_id: The hint to reveal.
            member_id: The member spending the budget.
            team_id: The team whose allowance is debited.
            now: Optional clock injection used by tests.

        Returns:
            The freshly created ledger entry.

        Raises:
            NotFoundError: When the hint, team, member or challenge is unknown.
            ValidationError: When the timing or budget rules reject the unlock.
            ConflictError: When the tier prerequisite or uniqueness rule fails.
        """
        hint = self.get_hint(hint_id)
        challenge = self._challenge(hint.challenge_id)
        self._team_exists(team_id)
        if challenge.team_id != team_id:
            raise ValidationError(
                "The challenge belongs to a different team",
                details={"challenge_id": challenge.id, "team_id": team_id},
            )
        member = self.repositories.members.get(member_id)
        if member is None:
            raise NotFoundError(f"Member {member_id!r} does not exist")
        if member.team_id != team_id:
            raise ValidationError("The member belongs to a different team")
        if not hint.is_active:
            raise ValidationError("This hint is not active")

        unlocked_tiers = self.store.unlocks.unlocked_tiers(challenge.id, team_id)
        previous = hint.previous_tier
        if previous is not None and previous not in unlocked_tiers:
            raise ConflictError(
                f"Tier {previous} must be unlocked first",
                details={"required_tier": previous},
            )
        elapsed = self._elapsed_seconds(challenge, now or utcnow())
        if elapsed < hint.reveal_after_seconds:
            raise ValidationError(
                "This hint is not available yet",
                details={"remaining_seconds": int(hint.reveal_after_seconds - elapsed)},
            )
        if hint.tier in unlocked_tiers:
            raise ConflictError("This hint has already been unlocked by the team")

        budget = self.get_budget(team_id)
        if hint.cost > budget.remaining:
            raise ValidationError(
                "The team does not have enough hint budget",
                details={"cost": hint.cost, "remaining": budget.remaining},
            )

        unlock = HintUnlock(
            id=f"unlock-{uuid.uuid4().hex[:12]}",
            hint_id=hint.id,
            member_id=member.id,
            team_id=team_id,
            cost_paid=hint.cost,
            unlocked_at=ensure_utc(now) if now is not None else utcnow(),
        )
        return self.store.atomic_unlock(unlock, hint)

    def challenge_view(
        self,
        challenge_id: str,
        *,
        team_id: str,
        member_id: str | None = None,
        now: datetime | None = None,
    ) -> ChallengeHintView:
        """Build the masked hint ladder for one team and challenge."""
        challenge = self._challenge(challenge_id)
        self._team_exists(team_id)
        if challenge.team_id != team_id:
            raise ValidationError(
                "The challenge belongs to a different team",
                details={"challenge_id": challenge.id, "team_id": team_id},
            )
        if member_id is not None:
            member = self.repositories.members.get(member_id)
            if member is None:
                raise NotFoundError(f"Member {member_id!r} does not exist")
            if member.team_id != team_id:
                raise ValidationError("The member belongs to a different team")

        now = now or utcnow()
        elapsed = self._elapsed_seconds(challenge, now)
        hints = self.store.hints.list_all(challenge_id=challenge_id)
        unlocked_tiers = self.store.unlocks.unlocked_tiers(challenge_id, team_id)
        budget = self.get_budget(team_id)
        views: list[HintView] = []
        for hint in hints:
            unlock = self.store.unlocks.find(hint.id, team_id)
            eligibility = evaluate_eligibility(
                hint,
                unlocked_tiers=unlocked_tiers,
                elapsed_seconds=elapsed,
                budget_remaining=budget.remaining,
            )
            views.append(
                HintView(
                    hint_id=hint.id,
                    challenge_id=hint.challenge_id,
                    tier=hint.tier,
                    title=hint.title,
                    content=(
                        hint.content
                        if unlock is not None
                        else hint.masked_content(DEFAULT_VISIBLE_CHARS)
                    ),
                    cost=hint.cost,
                    reveal_after_seconds=hint.reveal_after_seconds,
                    is_active=hint.is_active,
                    state=HintState.UNLOCKED if unlock is not None else eligibility.state,
                    reason=(
                        "Already revealed by your team"
                        if unlock is not None
                        else eligibility.reason
                    ),
                    remaining_seconds=eligibility.remaining_seconds,
                    required_tier=eligibility.required_tier,
                    unlocked_at=unlock.unlocked_at if unlock is not None else None,
                    unlocked_by=unlock.member_id if unlock is not None else None,
                )
            )
        curve = self.curve_for(hints[0]) if hints else ()
        return ChallengeHintView(
            challenge_id=challenge_id,
            team_id=team_id,
            hints=tuple(views),
            budget=budget,
            curve=curve,
        )

    @staticmethod
    def curve_for(hint: Hint) -> tuple[CostPoint, ...]:
        """Return the price curve implied by a hint's ladder settings."""
        return cost_curve(hint.base_cost, hint.multiplier, MAX_TIER)

    def hint_price(self, tier: int, base_cost: int, multiplier: float) -> int:
        """Return the rounded price of a hypothetical tier."""
        if tier < MIN_TIER or tier > MAX_TIER:
            raise ValidationError(f"tier must be between {MIN_TIER} and {MAX_TIER}")
        if base_cost <= 0:
            raise ValidationError("base_cost must be positive")
        if multiplier < 1:
            raise ValidationError("multiplier must be at least 1")
        return cost_for_tier(base_cost, multiplier, tier)
