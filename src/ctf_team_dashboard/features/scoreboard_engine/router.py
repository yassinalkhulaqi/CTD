"""HTTP endpoints of the configurable scoreboard engine."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ctf_team_dashboard.domain.models import utcnow

from .models import RankingEntry, ScoreBreakdown, ScoreRule, ScoreSnapshot
from .schemas import (
    CategoryScoreRead,
    RankingEntryRead,
    RankingResponse,
    ScoreBreakdownRead,
    ScoreRuleRead,
    ScoreRuleWrite,
    ScoreSnapshotRead,
    SolveScoreRead,
)
from .service import RuleDraft, ScoreboardService

router = APIRouter(prefix="/api/scoreboard", tags=["scoreboard"])


def get_scoreboard_service() -> ScoreboardService:
    """Dependency returning a scoreboard service bound to the current database."""
    return ScoreboardService()


ScoreboardServiceDep = Annotated[ScoreboardService, Depends(get_scoreboard_service)]


def _rule_read(rule: ScoreRule) -> ScoreRuleRead:
    """Convert a scoring rule domain object into its API representation."""
    return ScoreRuleRead(
        id=rule.id,
        team_id=rule.team_id,
        name=rule.name,
        base_points=rule.base_points,
        difficulty_multiplier=rule.difficulty_multiplier,
        first_blood_bonus=rule.first_blood_bonus,
        hint_penalty=rule.hint_penalty,
        decay_factor=rule.decay_factor,
        decay_enabled=rule.decay_enabled,
        updated_at=rule.updated_at,
        summary=rule.summary,
    )


def _snapshot_read(snapshot: ScoreSnapshot) -> ScoreSnapshotRead:
    """Convert a snapshot domain object into its API representation."""
    return ScoreSnapshotRead(
        id=snapshot.id,
        team_id=snapshot.team_id,
        recorded_at=snapshot.recorded_at,
        points=snapshot.points,
        solves=snapshot.solves,
        rank=snapshot.rank,
        details_json=snapshot.details_json,
        details=snapshot.details,
        label=snapshot.label,
        rule_name=snapshot.rule_name,
    )


def _ranking_read(entry: RankingEntry) -> RankingEntryRead:
    """Convert a ranking entry domain object into its API representation."""
    return RankingEntryRead(
        team_id=entry.team_id,
        team_name=entry.team_name,
        points=entry.points,
        solves=entry.solves,
        rank=entry.rank,
        previous_rank=entry.previous_rank,
        movement=entry.movement,
        movement_label=entry.movement_label,
        last_solve_at=entry.last_solve_at,
    )


def _breakdown_read(breakdown: ScoreBreakdown) -> ScoreBreakdownRead:
    """Convert a score breakdown domain object into its API representation."""
    return ScoreBreakdownRead(
        team_id=breakdown.team_id,
        team_name=breakdown.team_name,
        rule=_rule_read(breakdown.rule),
        total_points=breakdown.total_points,
        total_solves=breakdown.total_solves,
        first_bloods=breakdown.first_bloods,
        hint_penalties=breakdown.hint_penalties,
        decay_loss=round(breakdown.decay_loss, 2),
        average_points=round(breakdown.average_points, 2),
        challenges=breakdown.challenges,
        generated_at=breakdown.generated_at,
        categories=[
            CategoryScoreRead(
                category=item.category.value,
                label=item.label,
                accent=item.accent,
                points=item.points,
                solves=item.solves,
                challenges=item.challenges,
                solve_rate=round(item.solve_rate, 4),
                share=round(item.share(breakdown.total_points), 4),
            )
            for item in breakdown.categories
        ],
        solves=[
            SolveScoreRead(
                solve_id=score.solve_id,
                challenge_id=score.challenge_id,
                title=score.title,
                category=score.category.value,
                category_label=score.category.label,
                difficulty=score.difficulty.value,
                solve_index=score.solve_index,
                solved_at=score.solved_at,
                base_points=score.base_points,
                difficulty_weight=score.difficulty_weight,
                difficulty_multiplier=score.difficulty_multiplier,
                decay=round(score.decay, 6),
                first_blood=score.first_blood,
                bonus_points=score.bonus_points,
                hint_count=score.hint_count,
                penalty_points=score.penalty_points,
                points=score.points,
                formula=score.formula,
            )
            for score in breakdown.scores
        ],
    )


@router.get("/rules/{team_id}", response_model=ScoreRuleRead)
def get_rule(team_id: str, service: ScoreboardServiceDep) -> ScoreRuleRead:
    """Return the current scoring rule of a team."""
    return _rule_read(service.get_rule(team_id))


@router.put("/rules/{team_id}", response_model=ScoreRuleRead)
def put_rule(team_id: str, payload: ScoreRuleWrite, service: ScoreboardServiceDep) -> ScoreRuleRead:
    """Replace the scoring rule of a team."""
    rule = service.upsert_rule(team_id, RuleDraft.from_values(payload.model_dump()))
    return _rule_read(rule)


@router.post("/snapshot/{team_id}", response_model=ScoreSnapshotRead)
def create_snapshot(team_id: str, service: ScoreboardServiceDep) -> ScoreSnapshotRead:
    """Record a new ranking snapshot for a team."""
    return _snapshot_read(service.create_snapshot(team_id))


@router.get("/ranking", response_model=RankingResponse)
def get_ranking(service: ScoreboardServiceDep) -> RankingResponse:
    """Return the live ranking computed from the current solve data."""
    entries = [_ranking_read(entry) for entry in service.live_ranking()]
    return RankingResponse(
        entries=entries,
        team_count=len(entries),
        generated_at=utcnow(),
        leader_points=entries[0].points if entries else 0,
        total_points=sum(entry.points for entry in entries),
    )


@router.get("/teams/{team_id}/breakdown", response_model=ScoreBreakdownRead)
def get_breakdown(team_id: str, service: ScoreboardServiceDep) -> ScoreBreakdownRead:
    """Return the itemised score breakdown of a team."""
    return _breakdown_read(service.breakdown_for(team_id))


@router.get("/snapshots/{team_id}", response_model=list[ScoreSnapshotRead])
def list_snapshots(
    team_id: str, service: ScoreboardServiceDep, limit: int = 50
) -> list[ScoreSnapshotRead]:
    """Return the snapshot history of a team, newest first."""
    return [
        _snapshot_read(snapshot)
        for snapshot in service.list_snapshots(team_id, max(1, min(limit, 500)))
    ]
