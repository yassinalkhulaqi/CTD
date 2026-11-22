"""HTTP endpoints for the tiered hint engine."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, status

from ctf_team_dashboard.features.hint_engine.models import (
    ChallengeHintView,
    CostPoint,
    Hint,
    HintBudget,
    HintUnlock,
    LedgerEntry,
    TeamSpendSummary,
)
from ctf_team_dashboard.features.hint_engine.schemas import (
    BudgetResetRequest,
    ChallengeHintViewRead,
    CostPointRead,
    HintBudgetRead,
    HintCreate,
    HintLedgerRead,
    HintRead,
    HintUnlockRead,
    HintUnlockRequest,
    HintUpdate,
    HintViewRead,
    LedgerEntryRead,
    TeamSpendSummaryRead,
    TierSpendRead,
)
from ctf_team_dashboard.features.hint_engine.service import HintService

router = APIRouter(prefix="/api/hints", tags=["hints"])


def get_hint_service() -> HintService:
    """Dependency returning a configured hint service."""
    return HintService()


ServiceDep = Annotated[HintService, Depends(get_hint_service)]


def cost_point_reads(points: Sequence[CostPoint]) -> list[CostPointRead]:
    """Map cost curve domain records onto response models."""
    return [
        CostPointRead(
            tier=point.tier,
            cost=point.cost,
            cumulative=point.cumulative,
            label=point.label,
        )
        for point in points
    ]


def hint_read(hint: Hint, service: HintService) -> HintRead:
    """Map a hint onto its author-facing response model."""
    return HintRead(
        id=hint.id,
        challenge_id=hint.challenge_id,
        tier=hint.tier,
        title=hint.title,
        content=hint.content,
        cost=hint.cost,
        base_cost=hint.base_cost,
        multiplier=hint.multiplier,
        reveal_after_seconds=hint.reveal_after_seconds,
        is_active=hint.is_active,
        teaser=hint.masked_content(),
        curve=cost_point_reads(service.curve_for(hint)),
        created_at=hint.created_at,
        updated_at=hint.updated_at,
    )


def budget_read(budget: HintBudget) -> HintBudgetRead:
    """Map a budget onto its response model."""
    return HintBudgetRead(
        team_id=budget.team_id,
        total=budget.total,
        spent=budget.spent,
        remaining=budget.remaining,
        reset_at=budget.reset_at,
        created_at=budget.created_at,
        utilization=budget.utilization,
        is_exhausted=budget.is_exhausted,
    )


def unlock_read(unlock: HintUnlock) -> HintUnlockRead:
    """Map a ledger row onto its response model."""
    return HintUnlockRead(
        id=unlock.id,
        hint_id=unlock.hint_id,
        member_id=unlock.member_id,
        team_id=unlock.team_id,
        cost_paid=unlock.cost_paid,
        unlocked_at=unlock.unlocked_at,
    )


def spend_read(summary: TeamSpendSummary) -> TeamSpendSummaryRead:
    """Map a spend summary onto its response model."""
    return TeamSpendSummaryRead(
        team_id=summary.team_id,
        total=summary.total,
        spent=summary.spent,
        remaining=summary.remaining,
        unlock_count=summary.unlock_count,
        utilization=summary.utilization,
        average_cost=summary.average_cost,
        by_tier=[
            TierSpendRead(
                tier=row.tier,
                unlocks=row.unlocks,
                spent=row.spent,
                average_cost=row.average_cost,
            )
            for row in summary.by_tier
        ],
    )


def ledger_read(entry: LedgerEntry) -> LedgerEntryRead:
    """Map a joined ledger row onto its response model."""
    return LedgerEntryRead(
        id=entry.id,
        hint_id=entry.hint_id,
        hint_title=entry.hint_title,
        tier=entry.tier,
        member_id=entry.member_id,
        member_handle=entry.member_handle,
        team_id=entry.team_id,
        cost_paid=entry.cost_paid,
        unlocked_at=entry.unlocked_at,
        description=entry.description,
    )


@router.get("", response_model=list[HintRead])
def list_hints(
    service: ServiceDep,
    challenge_id: str | None = None,
    team_id: str | None = None,
) -> list[HintRead]:
    """List hints, optionally restricted to a challenge or a team."""
    return [
        hint_read(hint, service)
        for hint in service.list_hints(challenge_id=challenge_id, team_id=team_id)
    ]


@router.post("", response_model=HintRead, status_code=status.HTTP_201_CREATED)
def create_hint(payload: HintCreate, service: ServiceDep) -> HintRead:
    """Author a new hint on a challenge ladder."""
    hint = service.create_hint(
        challenge_id=payload.challenge_id,
        tier=payload.tier,
        title=payload.title,
        content=payload.content,
        base_cost=payload.base_cost,
        multiplier=payload.multiplier,
        reveal_after_seconds=payload.reveal_after_seconds,
        is_active=payload.is_active,
    )
    return hint_read(hint, service)


@router.get("/challenges/{challenge_id}", response_model=ChallengeHintViewRead)
def challenge_hints(
    challenge_id: str,
    service: ServiceDep,
    team_id: str,
    member_id: str | None = None,
) -> ChallengeHintViewRead:
    """Return a team's masked hint ladder for a challenge."""
    view: ChallengeHintView = service.challenge_view(
        challenge_id, team_id=team_id, member_id=member_id
    )
    return ChallengeHintViewRead(
        challenge_id=view.challenge_id,
        team_id=view.team_id,
        hints=[
            HintViewRead(
                hint_id=hint.hint_id,
                challenge_id=hint.challenge_id,
                tier=hint.tier,
                title=hint.title,
                content=hint.content,
                cost=hint.cost,
                reveal_after_seconds=hint.reveal_after_seconds,
                is_active=hint.is_active,
                state=hint.state,
                reason=hint.reason,
                remaining_seconds=hint.remaining_seconds,
                required_tier=hint.required_tier,
                unlocked=hint.unlocked,
                eligible=hint.eligible,
                badge_label=hint.badge_label,
                unlocked_at=hint.unlocked_at,
                unlocked_by=hint.unlocked_by,
            )
            for hint in view.hints
        ],
        budget=budget_read(view.budget),
        curve=cost_point_reads(view.curve),
        unlocked_count=view.unlocked_count,
    )


@router.get("/budget/{team_id}", response_model=HintBudgetRead)
def get_budget(team_id: str, service: ServiceDep) -> HintBudgetRead:
    """Return a team's hint allowance."""
    return budget_read(service.get_budget(team_id))


@router.post("/budget/{team_id}/reset", response_model=HintBudgetRead)
def reset_budget(team_id: str, payload: BudgetResetRequest, service: ServiceDep) -> HintBudgetRead:
    """Clear a team's spending and provision the next window."""
    budget = service.reset_budget(
        team_id,
        total=payload.total,
        reset_after_seconds=payload.reset_after_seconds,
    )
    return budget_read(budget)


@router.get("/ledger/{team_id}", response_model=HintLedgerRead)
def get_ledger(team_id: str, service: ServiceDep) -> HintLedgerRead:
    """Return the reveal history and spend summary for a team."""
    return HintLedgerRead(
        team_id=team_id,
        entries=[ledger_read(entry) for entry in service.store.unlocks.ledger(team_id)],
        summary=spend_read(service.spend_summary(team_id)),
    )


@router.post(
    "/{hint_id}/unlock",
    response_model=HintUnlockRead,
    status_code=status.HTTP_201_CREATED,
)
def unlock_hint(hint_id: str, payload: HintUnlockRequest, service: ServiceDep) -> HintUnlockRead:
    """Reveal a hint by spending budget from the member's team."""
    return unlock_read(
        service.unlock_hint(hint_id, member_id=payload.member_id, team_id=payload.team_id)
    )


@router.patch("/{hint_id}", response_model=HintRead)
def update_hint(hint_id: str, payload: HintUpdate, service: ServiceDep) -> HintRead:
    """Edit an existing hint."""
    hint = service.update_hint(
        hint_id,
        tier=payload.tier,
        title=payload.title,
        content=payload.content,
        base_cost=payload.base_cost,
        multiplier=payload.multiplier,
        reveal_after_seconds=payload.reveal_after_seconds,
        is_active=payload.is_active,
    )
    return hint_read(hint, service)


@router.delete("/{hint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hint(hint_id: str, service: ServiceDep) -> None:
    """Delete a hint that has never been revealed."""
    service.delete_hint(hint_id)
