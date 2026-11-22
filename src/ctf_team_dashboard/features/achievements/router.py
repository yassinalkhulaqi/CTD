"""HTTP API for badges, evaluations and achievement reporting."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from ctf_team_dashboard.errors import ConflictError
from ctf_team_dashboard.features.achievements.models import (
    AchievementAward,
    AchievementProgress,
    Badge,
    BadgeTier,
    BadgeView,
    CriteriaKind,
    EvaluationOutcome,
    EvaluationResult,
    MemberSummary,
)
from ctf_team_dashboard.features.achievements.schemas import (
    AchievementStatsRead,
    AwardRead,
    AwardRequest,
    AwardResult,
    BadgeCreate,
    BadgeDetailResponse,
    BadgeListResponse,
    BadgeRead,
    BadgeWithProgress,
    BatchEvaluationRequest,
    BatchEvaluationResultRead,
    EvaluationOutcomeRead,
    EvaluationRequest,
    EvaluationResultRead,
    LeaderboardEntry,
    LeaderboardResponse,
    MemberAchievementResponse,
    ProgressRead,
    SeedResultRead,
)
from ctf_team_dashboard.features.achievements.service import (
    AchievementService,
    MemberMetrics,
)

router = APIRouter(prefix="/api/achievements", tags=["achievements"])


def get_achievement_service() -> AchievementService:
    """Return a service, seeding the built-in catalogue on first use."""
    service = AchievementService()
    if service.store.badges.count() == 0:
        service.seed_catalogue()
    return service


AchievementServiceDep = Annotated[AchievementService, Depends(get_achievement_service)]


def badge_read(badge: Badge) -> BadgeRead:
    """Map a domain badge onto its API model."""
    return BadgeRead(
        id=badge.id,
        name=badge.name,
        description=badge.description,
        tier=badge.tier,
        criteria_kind=badge.criteria_kind,
        criteria_value=badge.criteria_value,
        icon=badge.icon,
        points=badge.points,
        secret=badge.secret,
        score=badge.score,
        target=badge.target,
        tier_rank=badge.tier_rank,
        criteria_label=badge.criteria_label,
        metric_key=badge.metric_key,
    )


def progress_read(progress: AchievementProgress) -> ProgressRead:
    """Map a progress record onto its API model."""
    return ProgressRead(
        member_id=progress.member_id,
        badge_id=progress.badge_id,
        current=progress.current,
        target=progress.target,
        percent=progress.percent,
        remaining=progress.remaining,
        is_complete=progress.is_complete,
    )


def award_read(award: AchievementAward) -> AwardRead:
    """Map an award record onto its API model."""
    return AwardRead(
        id=award.id,
        badge_id=award.badge_id,
        member_id=award.member_id,
        awarded_at=award.awarded_at,
        evidence=award.evidence,
        observed_value=award.observed_value,
        is_fresh=award.is_fresh,
    )


def badge_view_read(view: BadgeView) -> BadgeWithProgress:
    """Map a presentation view onto its API model."""
    return BadgeWithProgress(
        badge=badge_read(view.badge),
        awarded=view.awarded,
        revealed=view.revealed,
        rarity=view.rarity,
        holders=view.holders,
        current=view.current,
        target=view.target,
        percent=view.percent,
        rarity_band=view.rarity_band,
        status=view.status,
        display_name=view.display_name,
        display_description=view.display_description,
        display_icon=view.display_icon,
    )


def outcome_read(outcome: EvaluationOutcome) -> EvaluationOutcomeRead:
    """Map one evaluation outcome onto its API model."""
    return EvaluationOutcomeRead(
        badge_id=outcome.evaluation.badge_id,
        member_id=outcome.evaluation.member_id,
        current=outcome.evaluation.current,
        target=outcome.evaluation.target,
        percent=outcome.evaluation.percent,
        qualifies=outcome.evaluation.qualifies,
        remaining=outcome.evaluation.remaining,
        status=outcome.evaluation.status,
        criteria_kind=outcome.evaluation.criteria_kind,
        tier=outcome.evaluation.tier,
        awarded=outcome.award is not None,
        newly_awarded=outcome.newly_awarded,
        reason=outcome.reason,
    )


def result_read(result: EvaluationResult) -> EvaluationResultRead:
    """Map a complete evaluation result onto its API model."""
    return EvaluationResultRead(
        member_id=result.member_id,
        metrics=result.metrics,
        evaluated=result.evaluated,
        eligible=result.eligible,
        unlocked=result.unlocked,
        outcomes=[outcome_read(outcome) for outcome in result.outcomes],
    )


def member_read(summary: MemberSummary) -> MemberAchievementResponse:
    """Map a member summary onto its API model."""
    next_badge = summary.next_badge
    return MemberAchievementResponse(
        member_id=summary.member_id,
        points=summary.points,
        unlocked=summary.unlocked,
        completion=summary.completion,
        next_badge=badge_view_read(next_badge) if next_badge is not None else None,
        awards=[award_read(award) for award in summary.awards],
        progress=[progress_read(record) for record in summary.progress],
        badges=[badge_view_read(view) for view in summary.views],
    )


@router.get("", response_model=BadgeListResponse)
def list_achievements(
    service: AchievementServiceDep,
    member_id: str | None = None,
    tier: BadgeTier | None = None,
    criteria_kind: CriteriaKind | None = None,
    include_secret: bool = True,
) -> BadgeListResponse:
    """Return the badge catalogue with optional filters and member progress."""
    views = service.list_badges(
        member_id=member_id,
        tier=tier,
        kind=criteria_kind,
        include_secret=include_secret,
    )
    return BadgeListResponse(
        badges=[badge_view_read(view) for view in views],
        total=len(views),
        tier=tier,
        criteria_kind=criteria_kind,
    )


@router.get("/badges", response_model=BadgeListResponse)
def list_badges(
    service: AchievementServiceDep,
    member_id: str | None = None,
    tier: BadgeTier | None = None,
    criteria_kind: CriteriaKind | None = None,
    include_secret: bool = True,
) -> BadgeListResponse:
    """Return the badge catalogue; alias of the root endpoint."""
    return list_achievements(service, member_id, tier, criteria_kind, include_secret)


@router.post("/badges", response_model=BadgeRead, status_code=status.HTTP_201_CREATED)
def create_badge(payload: BadgeCreate, service: AchievementServiceDep) -> BadgeRead:
    """Create a custom badge definition."""
    badge = service.create_badge(
        name=payload.name,
        description=payload.description,
        tier=payload.tier,
        criteria_kind=payload.criteria_kind,
        criteria_value=payload.criteria_value,
        icon=payload.icon,
        points=payload.points,
        secret=payload.secret,
        badge_id=payload.id,
    )
    return badge_read(badge)


@router.get("/badges/{badge_id}", response_model=BadgeDetailResponse)
def get_badge(
    badge_id: str,
    service: AchievementServiceDep,
    member_id: str | None = None,
) -> BadgeDetailResponse:
    """Return one badge and its holder count."""
    badge = service.get_badge(badge_id, viewer_member_id=member_id)
    views = service.list_badges(member_id=member_id)
    matching = next(candidate for candidate in views if candidate.badge.id == badge.id)
    return BadgeDetailResponse(
        badge=badge_view_read(matching),
        awarded_to=service.store.awards.count_for_badge(badge.id),
    )


@router.post(
    "/evaluate",
    response_model=EvaluationResultRead | BatchEvaluationResultRead,
)
def evaluate(
    payload: EvaluationRequest | BatchEvaluationRequest,
    service: AchievementServiceDep,
) -> EvaluationResultRead | BatchEvaluationResultRead:
    """Evaluate a single member or a batch of members."""
    if isinstance(payload, BatchEvaluationRequest):
        return evaluate_batch(payload, service)
    result = service.evaluate_metrics(payload.member_id, payload.metrics)
    return result_read(result)


@router.post("/evaluate/batch", response_model=BatchEvaluationResultRead)
def evaluate_batch(
    payload: BatchEvaluationRequest,
    service: AchievementServiceDep,
) -> BatchEvaluationResultRead:
    """Evaluate several members in a single request."""
    submissions = [
        MemberMetrics(member_id=item.member_id, metrics=item.metrics)
        for item in payload.submissions
    ]
    results = service.evaluate_many(submissions)
    return BatchEvaluationResultRead(
        results=[result_read(result) for result in results],
        evaluated_members=len(results),
        total_unlocked=sum(result.unlocked for result in results),
    )


@router.get("/members/{member_id}", response_model=MemberAchievementResponse)
def get_member_achievements(
    member_id: str, service: AchievementServiceDep
) -> MemberAchievementResponse:
    """Return a member's awards, progress and badge views."""
    return member_read(service.member_summary(member_id))


@router.get("/members/{member_id}/progress", response_model=list[ProgressRead])
def get_member_progress(member_id: str, service: AchievementServiceDep) -> list[ProgressRead]:
    """Return only the progress records of a member."""
    summary = service.member_summary(member_id)
    return [progress_read(record) for record in summary.progress]


@router.post(
    "/members/{member_id}/awards/{badge_id}",
    response_model=AwardResult,
    status_code=status.HTTP_201_CREATED,
)
def award_badge(
    member_id: str,
    badge_id: str,
    payload: AwardRequest,
    service: AchievementServiceDep,
) -> AwardResult:
    """Manually grant a badge to a member."""
    outcome = service.award(member_id, badge_id, payload.evidence)
    if outcome.award is None:
        raise ConflictError("Award could not be created")
    return AwardResult(
        badge=badge_read(outcome.badge),
        award=award_read(outcome.award),
        awarded=outcome.awarded,
        progress=outcome.progress,
    )


@router.get("/leaderboard", response_model=LeaderboardResponse)
def get_leaderboard(
    service: AchievementServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] | None = None,
) -> LeaderboardResponse:
    """Return the ranked achievement leaderboard."""
    rows = service.leaderboard(limit)
    return LeaderboardResponse(
        entries=[
            LeaderboardEntry(
                member_id=row.member_id,
                handle=row.handle,
                display_name=row.display_name,
                label=row.label,
                awards=row.awards,
                points=row.points,
                rank=row.rank,
                rarity=row.rarity,
            )
            for row in rows
        ],
        total=len(rows),
    )


@router.get("/stats", response_model=AchievementStatsRead)
def get_stats(service: AchievementServiceDep) -> AchievementStatsRead:
    """Return aggregate achievement statistics."""
    stats = service.stats()
    return AchievementStatsRead(
        badges=stats.badges,
        awards=stats.awards,
        members_with_awards=stats.members_with_awards,
        members=stats.members,
        points=stats.points,
        secret_badges=stats.secret_badges,
        gold_badges=stats.gold_badges,
        recent_awards=stats.recent_awards,
        average_rarity=stats.average_rarity,
        participation_rate=stats.participation_rate,
        completion_rate=stats.completion_rate,
        points_per_member=stats.points_per_member,
    )


@router.post("/seed", response_model=SeedResultRead)
def seed_catalogue(service: AchievementServiceDep, response: Response) -> SeedResultRead:
    """Seed missing built-in badges into the catalogue."""
    result = service.seed_catalogue()
    response.status_code = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    return SeedResultRead(created=result.created, total=result.total)
