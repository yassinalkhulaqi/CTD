"""Business rules for badge evaluation, awards and achievement reporting."""

from __future__ import annotations

import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.achievements.catalogue import default_badges
from ctf_team_dashboard.features.achievements.models import (
    AchievementProgress,
    AchievementStats,
    AwardOutcome,
    Badge,
    BadgeTier,
    BadgeView,
    CriteriaKind,
    EvaluationOutcome,
    EvaluationResult,
    LeaderboardRow,
    MemberSummary,
    award_evidence,
    merge_views,
    normalise_metrics,
    rank_rows,
    rarity_score,
)
from ctf_team_dashboard.features.achievements.store import AchievementStore
from ctf_team_dashboard.repositories import Repositories

MAX_BADGE_NAME = 80
MAX_DESCRIPTION = 500
MAX_ICON = 48


@dataclass(frozen=True, slots=True)
class SeedResult:
    """Summary of a catalogue seeding operation."""

    created: int
    total: int


@dataclass(frozen=True, slots=True)
class MemberMetrics:
    """A single member's metrics submitted in a batch evaluation."""

    member_id: str
    metrics: dict[str, Any]


def slugify(value: str) -> str:
    """Convert a human readable label into a stable identifier fragment."""
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "badge"


class AchievementService:
    """Application service coordinating the achievement domain."""

    def __init__(
        self,
        store: AchievementStore | None = None,
        repositories: Repositories | None = None,
    ) -> None:
        self.store = store or AchievementStore()
        self.repositories = repositories or Repositories()

    # ------------------------------------------------------------------
    # Catalogue
    # ------------------------------------------------------------------
    def seed_catalogue(self, *, force: bool = False) -> SeedResult:
        """Seed the built-in badge catalogue without overwriting edits."""
        if force:
            for badge in self.store.badges.list_all():
                self.store.badges.delete(badge.id)
        badges = default_badges()
        created = int(self.store.badges.seed(badges))
        return SeedResult(created=created, total=len(self.store.badges.list_all()))

    def create_badge(
        self,
        *,
        name: str,
        description: str = "",
        tier: BadgeTier = BadgeTier.BRONZE,
        criteria_kind: CriteriaKind = CriteriaKind.SOLVES,
        criteria_value: int = 1,
        icon: str = "trophy",
        points: int = 100,
        secret: bool = False,
        badge_id: str | None = None,
    ) -> Badge:
        """Validate and persist a custom badge definition."""
        cleaned_name = name.strip()
        if not cleaned_name or len(cleaned_name) > MAX_BADGE_NAME:
            raise ValidationError(f"Badge name must be between 1 and {MAX_BADGE_NAME} characters")
        if len(description) > MAX_DESCRIPTION:
            raise ValidationError(f"Description must be at most {MAX_DESCRIPTION} characters")
        if criteria_value <= 0:
            raise ValidationError("Criterion target must be greater than zero")
        if points < 0:
            raise ValidationError("Badge points must not be negative")
        cleaned_icon = icon.strip() or "trophy"
        if len(cleaned_icon) > MAX_ICON:
            raise ValidationError(f"Icon token must be at most {MAX_ICON} characters")
        identifier = badge_id or f"badge-{slugify(cleaned_name)}-{uuid.uuid4().hex[:6]}"
        if self.store.badges.get(identifier) is not None:
            raise ConflictError(f"Badge {identifier!r} already exists")
        badge = Badge(
            id=identifier,
            name=cleaned_name,
            description=description.strip(),
            tier=tier,
            criteria_kind=criteria_kind,
            criteria_value=criteria_value,
            icon=cleaned_icon,
            points=points,
            secret=secret,
        )
        return self.store.badges.create(badge)

    def get_badge(self, badge_id: str, viewer_member_id: str | None = None) -> Badge:
        """Return a badge definition or raise :class:`NotFoundError`."""
        badge = self.store.badges.get(badge_id)
        if badge is None:
            raise NotFoundError(f"Badge {badge_id!r} does not exist")
        if badge.secret and not self._viewer_owns(viewer_member_id, badge_id):
            raise NotFoundError(f"Badge {badge_id!r} does not exist")
        return badge

    def list_badges(
        self,
        *,
        member_id: str | None = None,
        tier: BadgeTier | None = None,
        kind: CriteriaKind | None = None,
        include_secret: bool = True,
    ) -> list[BadgeView]:
        """Return badge views with progress, rarity and masking applied."""
        badges = self.store.badges.list_all(tier=tier, kind=kind, include_secret=include_secret)
        return self._build_views(badges, member_id)

    # ------------------------------------------------------------------
    # Evaluation and awards
    # ------------------------------------------------------------------
    def evaluate_metrics(
        self,
        member_id: str,
        raw_metrics: Mapping[str, Any],
        *,
        persist: bool = True,
        grant_awards: bool = True,
    ) -> EvaluationResult:
        """Evaluate every badge for one member and optionally persist results.

        Progress records never move backwards. Award insertion is idempotent:
        evaluating the same metrics twice never duplicates an award.
        """
        self._ensure_member(member_id)
        metrics = normalise_metrics(raw_metrics)
        badges = self.store.badges.list_all()
        existing = {
            record.badge_id: record for record in self.store.progress.list_for_member(member_id)
        }
        outcomes: list[EvaluationOutcome] = []
        progress_records: list[AchievementProgress] = []

        for badge in badges:
            evaluation = badge.evaluate(metrics).with_member(member_id)
            previous = existing.get(badge.id)
            observed = min(evaluation.current, badge.target)
            progress = AchievementProgress(
                member_id=member_id,
                badge_id=badge.id,
                current=observed,
                target=badge.target,
            )
            if previous is not None:
                progress = previous.advanced_to(observed)
            existing[badge.id] = progress
            progress_records.append(progress)

            award = None
            newly_awarded = False
            if evaluation.qualifies and grant_awards:
                evidence = award_evidence(badge, metrics, evaluation.current)
                award = self.store.awards.award_once(badge.id, member_id, evidence)
                if award is not None:
                    newly_awarded = True
                    progress = AchievementProgress(
                        member_id=member_id,
                        badge_id=badge.id,
                        current=badge.target,
                        target=badge.target,
                    )
                    existing[badge.id] = progress
                    progress_records[-1] = progress
                else:
                    award = self.store.awards.find(badge.id, member_id)
            elif evaluation.qualifies:
                award = self.store.awards.find(badge.id, member_id)

            outcomes.append(
                EvaluationOutcome(
                    evaluation=evaluation,
                    badge=badge,
                    award=award,
                    progress=progress,
                    newly_awarded=newly_awarded,
                )
            )

        if persist and progress_records:
            self.store.progress.upsert_many(progress_records)
        return EvaluationResult(member_id=member_id, metrics=metrics, outcomes=tuple(outcomes))

    def evaluate_many(
        self, submissions: Sequence[MemberMetrics], *, persist: bool = True
    ) -> list[EvaluationResult]:
        """Evaluate several members in one request."""
        results: list[EvaluationResult] = []
        for submission in submissions:
            results.append(
                self.evaluate_metrics(
                    submission.member_id,
                    submission.metrics,
                    persist=persist,
                )
            )
        return results

    def award(
        self,
        member_id: str,
        badge_id: str,
        evidence: Mapping[str, Any] | None = None,
        *,
        strict: bool = False,
    ) -> AwardOutcome:
        """Grant a badge to a member, idempotently by default.

        Args:
            member_id: Identifier of the receiving member.
            badge_id: Identifier of the badge to grant.
            evidence: Optional evidence payload persisted with the award.
            strict: Raise :class:`ConflictError` instead of returning the
                existing award when the member already owns the badge.

        Returns:
            The award outcome, including a flag indicating whether it was new.
        """
        self._ensure_member(member_id)
        badge = self.store.badges.get(badge_id)
        if badge is None:
            raise NotFoundError(f"Badge {badge_id!r} does not exist")
        payload = dict(evidence or {})
        payload.setdefault("source", "manual")
        award = self.store.awards.award_once(badge.id, member_id, payload)
        if award is None:
            if strict:
                raise ConflictError(f"Member {member_id!r} already owns badge {badge_id!r}")
            existing = self.store.awards.find(badge.id, member_id)
            if existing is None:
                raise ConflictError("Award could not be read after insertion")
            progress = self._complete_progress(member_id, badge)
            return AwardOutcome(
                badge=badge,
                award=existing,
                awarded=False,
                progress=progress.percent,
            )
        progress = self._complete_progress(member_id, badge)
        return AwardOutcome(badge=badge, award=award, awarded=True, progress=progress.percent)

    def recompute_progress(
        self, member_id: str, raw_metrics: Mapping[str, Any]
    ) -> list[AchievementProgress]:
        """Rebuild all progress records for a member from supplied metrics."""
        result = self.evaluate_metrics(member_id, raw_metrics, grant_awards=False)
        return [outcome.progress for outcome in result.outcomes if outcome.progress is not None]

    def _complete_progress(self, member_id: str, badge: Badge) -> AchievementProgress:
        """Persist a completed progress record for a manual award."""
        progress = AchievementProgress(
            member_id=member_id,
            badge_id=badge.id,
            current=badge.target,
            target=badge.target,
        )
        self.store.progress.upsert(progress)
        return progress

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def leaderboard(self, limit: int | None = None) -> list[LeaderboardRow]:
        """Return the ranked achievement leaderboard."""
        rows = self.store.awards.leaderboard()
        member_count = self.repositories.members.count_matching()
        holders = self.store.awards.holders_by_badge()
        awards = self.store.awards.list_all()
        awards_by_member: dict[str, list[str]] = {}
        for award in awards:
            awards_by_member.setdefault(award.member_id, []).append(award.badge_id)
        enriched: list[LeaderboardRow] = []
        for row in rows:
            owned = awards_by_member.get(row.member_id, [])
            rarity = (
                max(rarity_score(holders.get(badge_id, 0), member_count) for badge_id in owned)
                if owned
                else 0.0
            )
            enriched.append(
                LeaderboardRow(
                    member_id=row.member_id,
                    handle=row.handle,
                    display_name=row.display_name,
                    awards=row.awards,
                    points=row.points,
                    rarity=rarity,
                )
            )
        ranked = rank_rows(enriched)
        if limit is not None:
            return ranked[: max(0, limit)]
        return ranked

    def stats(self) -> AchievementStats:
        """Aggregate counters for the achievement overview."""
        badges = self.store.badges.list_all()
        members = self.repositories.members.count_matching()
        holders = self.store.awards.holders_by_badge()
        rarity_values = [rarity_score(holders.get(badge.id, 0), members) for badge in badges]
        awards = self.store.awards.list_all()
        recent = sum(1 for award in awards if (utcnow() - award.awarded_at).total_seconds() < 86400)
        return AchievementStats(
            badges=len(badges),
            awards=len(awards),
            members_with_awards=self.store.awards.distinct_members(),
            members=members,
            points=self.store.awards.total_points(),
            secret_badges=sum(1 for badge in badges if badge.secret),
            gold_badges=sum(1 for badge in badges if badge.tier is BadgeTier.GOLD),
            recent_awards=recent,
            average_rarity=(
                round(sum(rarity_values) / len(rarity_values), 1) if rarity_values else 0.0
            ),
        )

    def member_summary(self, member_id: str) -> MemberSummary:
        """Return a full achievement profile for one member."""
        self._ensure_member(member_id)
        awards = self.store.awards.list_for_member(member_id)
        views = self.list_badges(member_id=member_id)
        points = sum(view.badge.score for view in views if view.awarded)
        return MemberSummary(
            member_id=member_id,
            awards=tuple(awards),
            progress=tuple(self.store.progress.list_for_member(member_id)),
            views=tuple(views),
            points=points,
        )

    def _build_views(
        self, badges: Sequence[Badge], member_id: str | None = None
    ) -> list[BadgeView]:
        """Create presentation views for a collection of badges."""
        holders = self.store.awards.holders_by_badge()
        members = self.repositories.members.count_matching()
        rarity = {badge_id: rarity_score(count, members) for badge_id, count in holders.items()}
        awarded_ids: list[str] = []
        progress: dict[str, AchievementProgress] = {}
        if member_id is not None:
            awarded_ids = [award.badge_id for award in self.store.awards.list_for_member(member_id)]
            progress = {
                record.badge_id: record for record in self.store.progress.list_for_member(member_id)
            }
        return merge_views(badges, progress, awarded_ids, rarity, holders, member_id)

    def _viewer_owns(self, viewer_member_id: str | None, badge_id: str) -> bool:
        """Return whether a viewer has earned the given badge."""
        if viewer_member_id is None:
            return False
        return self.store.awards.find(badge_id, viewer_member_id) is not None

    def _ensure_member(self, member_id: str) -> None:
        """Ensure a member exists, raising :class:`NotFoundError` otherwise."""
        if not member_id.strip():
            raise ValidationError("Member identifier must not be empty")
        if self.repositories.members.get(member_id) is None:
            raise NotFoundError(f"Member {member_id!r} does not exist")


def evaluation_summary(result: EvaluationResult) -> dict[str, Any]:
    """Convert an evaluation result into a compact API summary."""
    return {
        "member_id": result.member_id,
        "evaluated": result.evaluated,
        "eligible": result.eligible,
        "unlocked": result.unlocked,
        "unlocked_ids": [badge.id for badge in result.unlocked_badges],
    }


__all__ = [
    "MAX_BADGE_NAME",
    "AchievementService",
    "MemberMetrics",
    "SeedResult",
    "evaluation_summary",
    "slugify",
]
