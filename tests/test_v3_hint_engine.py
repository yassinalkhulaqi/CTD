"""Backend tests for the tiered hint engine."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.domain.enums import ChallengeCategory, ChallengeStatus, Difficulty
from ctf_team_dashboard.domain.models import Challenge, utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.hint_engine.models import (
    Hint,
    HintBudget,
    HintState,
    HintTier,
    cost_curve,
    cost_for_tier,
    evaluate_eligibility,
    mask_content,
)
from ctf_team_dashboard.features.hint_engine.service import (
    DEFAULT_BUDGET_TOTAL,
    HintService,
)
from ctf_team_dashboard.repositories import Repositories


@pytest.fixture
def ladder(seeded: Repositories) -> SimpleNamespace:
    """Provision a three-tier ladder on a seeded challenge."""
    repositories = seeded
    team = repositories.teams.list_all()[0]
    challenge = next(item for item in repositories.challenges.list_all() if item.team_id == team.id)
    member = repositories.members.list_all(team.id)[0]
    service = HintService()
    hints = [
        service.create_hint(
            challenge_id=challenge.id,
            tier=tier,
            title=f"Tier {tier} nudge",
            content=f"The solution is in layer {tier} of the binary.",
            base_cost=25,
            multiplier=2.0,
        )
        for tier in (1, 2, 3)
    ]
    return SimpleNamespace(
        team=team,
        member=member,
        challenge=challenge,
        hints=hints,
        service=service,
        repositories=repositories,
    )


def payload(hint: object, member_id: str, team_id: str) -> dict[str, str]:
    """Build an unlock request body."""
    return {"member_id": member_id, "team_id": team_id}


def test_cost_curve_uses_geometric_rounding() -> None:
    assert cost_for_tier(25, 2.0, 1) == 25
    assert cost_for_tier(25, 2.0, 2) == 50
    assert cost_for_tier(25, 2.0, 3) == 100
    assert cost_for_tier(10, 1.5, 3) == 23
    points = cost_curve(10, 1.5)
    assert [point.cost for point in points] == [10, 15, 23]
    assert [point.cumulative for point in points] == [10, 25, 48]
    assert points[2].label == "T3: 23"


def test_cost_curve_validates_inputs() -> None:
    with pytest.raises(ValueError):
        cost_for_tier(0, 2.0, 1)
    with pytest.raises(ValueError):
        cost_for_tier(10, 0.5, 1)
    with pytest.raises(ValueError):
        cost_for_tier(10, 2.0, 4)
    with pytest.raises(ValueError):
        HintTier.parse(7)


def test_content_masking_preserves_length_and_teaser() -> None:
    assert mask_content("short", 28) == "short"
    masked = mask_content("ABCDEFGHIJKLMNOPQRSTUVWXYZ", 4)
    assert masked.startswith("ABCD")
    assert len(masked) == 26
    assert masked[4:] == "*" * 22
    with pytest.raises(ValueError):
        mask_content("abc", -1)


def test_eligibility_rules() -> None:
    hint = ladder_hint(tier=2, reveal_after_seconds=10, cost=50)
    locked_tier = evaluate_eligibility(
        hint, unlocked_tiers=frozenset(), elapsed_seconds=100, budget_remaining=500
    )
    assert locked_tier.state is HintState.LOCKED
    assert locked_tier.required_tier == 1

    too_early = evaluate_eligibility(
        hint, unlocked_tiers=frozenset({1}), elapsed_seconds=4, budget_remaining=500
    )
    assert too_early.state is HintState.LOCKED
    assert too_early.remaining_seconds == 6

    no_budget = evaluate_eligibility(
        hint, unlocked_tiers=frozenset({1}), elapsed_seconds=20, budget_remaining=10
    )
    assert no_budget.state is HintState.EXHAUSTED

    ready = evaluate_eligibility(
        hint, unlocked_tiers=frozenset({1}), elapsed_seconds=20, budget_remaining=500
    )
    assert ready.state is HintState.ELIGIBLE
    assert ready.eligible

    revealed = evaluate_eligibility(
        hint, unlocked_tiers=frozenset({1, 2}), elapsed_seconds=20, budget_remaining=500
    )
    assert revealed.state is HintState.UNLOCKED
    assert revealed.unlocked


def ladder_hint(*, tier: int, reveal_after_seconds: int, cost: int) -> Hint:
    """Build a detached hint for pure rule tests."""
    return Hint(
        id="hint-test",
        challenge_id="challenge-test",
        tier=tier,
        title="Test",
        content="x" * 40,
        cost=cost,
        reveal_after_seconds=reveal_after_seconds,
    )


def test_budget_properties() -> None:
    budget = HintBudget(team_id="team-1", total=100, spent=60)
    assert budget.remaining == 40
    assert budget.utilization == pytest.approx(0.6)
    assert budget.can_afford(40)
    assert not budget.can_afford(41)
    assert not HintBudget(team_id="team-2", total=10, spent=10).can_afford(1)


def test_router_create_list_and_masking(ladder: SimpleNamespace, client: TestClient) -> None:
    response = client.get("/api/hints")
    assert response.status_code == 200
    assert len(response.json()) == 3
    first = response.json()[0]
    assert first["tier"] == 1
    assert first["cost"] == 25
    assert "*" in first["teaser"]
    assert [point["cost"] for point in first["curve"]] == [25, 50, 100]

    created = client.post(
        "/api/hints",
        json={
            "challenge_id": ladder.challenge.id,
            "tier": 1,
            "title": "Duplicate",
            "content": "nope",
            "base_cost": 5,
        },
    )
    assert created.status_code == 409
    assert created.json()["error"]["code"] == "conflict"


def test_router_create_unknown_challenge(client: TestClient) -> None:
    response = client.post(
        "/api/hints",
        json={
            "challenge_id": "challenge-missing",
            "tier": 1,
            "title": "Orphan",
            "content": "nope",
            "base_cost": 10,
        },
    )
    assert response.status_code == 404


def test_router_update_and_delete(ladder: SimpleNamespace, client: TestClient) -> None:
    hint_id = ladder.hints[0].id
    updated = client.patch(
        f"/api/hints/{hint_id}",
        json={"base_cost": 40, "title": "Rewritten nudge"},
    )
    assert updated.status_code == 200
    assert updated.json()["cost"] == 40
    assert updated.json()["title"] == "Rewritten nudge"

    invalid = client.patch(f"/api/hints/{hint_id}", json={"tier": 9})
    assert invalid.status_code == 422

    assert client.delete(f"/api/hints/{hint_id}").status_code == 204
    remaining = client.get(f"/api/hints?challenge_id={ladder.challenge.id}").json()
    assert len(remaining) == 2
    assert [item["tier"] for item in remaining] == [2, 3]


def test_unlock_tier_one_debits_budget(ladder: SimpleNamespace, client: TestClient) -> None:
    response = client.post(
        f"/api/hints/{ladder.hints[0].id}/unlock",
        json=payload(ladder.hints[0], ladder.member.id, ladder.team.id),
    )
    assert response.status_code == 201
    assert response.json()["cost_paid"] == 25
    budget = client.get(f"/api/hints/budget/{ladder.team.id}")
    assert budget.json()["spent"] == 25
    assert budget.json()["remaining"] == DEFAULT_BUDGET_TOTAL - 25


def test_unlock_enforces_tier_prerequisite_and_duplicates(
    ladder: SimpleNamespace, client: TestClient
) -> None:
    second = ladder.hints[1]
    body = payload(second, ladder.member.id, ladder.team.id)
    assert client.post(f"/api/hints/{second.id}/unlock", json=body).status_code == 409

    for hint in ladder.hints[:2]:
        assert (
            client.post(
                f"/api/hints/{hint.id}/unlock",
                json=payload(hint, ladder.member.id, ladder.team.id),
            ).status_code
            == 201
        )

    duplicate = client.post(f"/api/hints/{second.id}/unlock", json=body)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict"


def test_unlock_rejects_foreign_member_and_team(
    ladder: SimpleNamespace, client: TestClient, seeded: object
) -> None:
    other_team = seeded.teams.list_all()[1]
    other_member = seeded.members.list_all(other_team.id)[0]
    hint = ladder.hints[0]
    foreign = client.post(
        f"/api/hints/{hint.id}/unlock",
        json=payload(hint, other_member.id, other_team.id),
    )
    assert foreign.status_code == 422

    wrong_team = client.post(
        f"/api/hints/{hint.id}/unlock",
        json=payload(hint, ladder.member.id, other_team.id),
    )
    assert wrong_team.status_code == 422

    missing_member = client.post(
        f"/api/hints/{hint.id}/unlock",
        json=payload(hint, "member-missing", ladder.team.id),
    )
    assert missing_member.status_code == 404


def test_unlock_fails_when_budget_is_insufficient(
    ladder: SimpleNamespace, client: TestClient
) -> None:
    ladder.service.store.budgets.upsert(HintBudget(team_id=ladder.team.id, total=10, spent=0))
    response = client.post(
        f"/api/hints/{ladder.hints[0].id}/unlock",
        json=payload(ladder.hints[0], ladder.member.id, ladder.team.id),
    )
    assert response.status_code == 422
    assert response.json()["error"]["details"]["remaining"] == 10
    assert ladder.service.store.unlocks.count_for_team(ladder.team.id) == 0


def test_reveal_delay_blocks_early_unlock(ladder: SimpleNamespace) -> None:
    start = utcnow() - timedelta(minutes=1)
    challenge = Challenge(
        id="challenge-timed",
        team_id=ladder.team.id,
        title="Timed challenge",
        category=ChallengeCategory.MISC,
        difficulty=Difficulty.EASY,
        status=ChallengeStatus.ACTIVE,
        starts_at=start,
        created_at=start,
    )
    ladder.repositories.challenges.create(challenge)
    hint = ladder.service.create_hint(
        challenge_id=challenge.id,
        tier=1,
        title="Too early",
        content="Wait a moment.",
        base_cost=10,
        reveal_after_seconds=300,
    )
    with pytest.raises(ValidationError) as exc:
        ladder.service.unlock_hint(
            hint.id,
            member_id=ladder.member.id,
            team_id=ladder.team.id,
            now=utcnow(),
        )
    assert exc.value.details["remaining_seconds"] > 0

    unlocked = ladder.service.unlock_hint(
        hint.id,
        member_id=ladder.member.id,
        team_id=ladder.team.id,
        now=start + timedelta(minutes=6),
    )
    assert unlocked.cost_paid == 10


def test_budget_reset_clears_spending(ladder: SimpleNamespace, client: TestClient) -> None:
    client.post(
        f"/api/hints/{ladder.hints[0].id}/unlock",
        json=payload(ladder.hints[0], ladder.member.id, ladder.team.id),
    )
    reset = client.post(
        f"/api/hints/budget/{ladder.team.id}/reset",
        json={"total": 900, "reset_after_seconds": 3600},
    )
    assert reset.status_code == 200
    assert reset.json()["spent"] == 0
    assert reset.json()["total"] == 900
    assert client.get(f"/api/hints/budget/{ladder.team.id}").json()["remaining"] == 900


def test_challenge_view_states_and_masking(ladder: SimpleNamespace, client: TestClient) -> None:
    response = client.get(f"/api/hints/challenges/{ladder.challenge.id}?team_id={ladder.team.id}")
    assert response.status_code == 200
    body = response.json()
    assert [item["state"] for item in body["hints"]] == ["eligible", "locked", "locked"]
    assert "*" in body["hints"][0]["content"]
    assert body["hints"][1]["required_tier"] == 1
    assert body["budget"]["total"] == DEFAULT_BUDGET_TOTAL
    assert [point["cost"] for point in body["curve"]] == [25, 50, 100]

    client.post(
        f"/api/hints/{ladder.hints[0].id}/unlock",
        json=payload(ladder.hints[0], ladder.member.id, ladder.team.id),
    )
    revealed = client.get(
        f"/api/hints/challenges/{ladder.challenge.id}?team_id={ladder.team.id}"
    ).json()
    assert revealed["hints"][0]["state"] == "unlocked"
    assert revealed["hints"][1]["state"] == "eligible"
    assert revealed["unlocked_count"] == 1
    assert "*" not in revealed["hints"][0]["content"]


def test_ledger_aggregation(ladder: SimpleNamespace, client: TestClient) -> None:
    for hint in ladder.hints[:2]:
        assert (
            client.post(
                f"/api/hints/{hint.id}/unlock",
                json=payload(hint, ladder.member.id, ladder.team.id),
            ).status_code
            == 201
        )

    ledger = client.get(f"/api/hints/ledger/{ladder.team.id}")
    assert ledger.status_code == 200
    body = ledger.json()
    assert body["team_id"] == ladder.team.id
    assert len(body["entries"]) == 2
    assert body["entries"][0]["member_handle"] == ladder.member.handle
    assert body["summary"]["spent"] == 75
    assert body["summary"]["unlock_count"] == 2
    assert [row["tier"] for row in body["summary"]["by_tier"]] == [1, 2]


def test_delete_revealed_hint_is_conflict(ladder: SimpleNamespace, client: TestClient) -> None:
    hint = ladder.hints[0]
    client.post(
        f"/api/hints/{hint.id}/unlock",
        json=payload(hint, ladder.member.id, ladder.team.id),
    )
    assert client.delete(f"/api/hints/{hint.id}").status_code == 409
    assert client.patch(f"/api/hints/{hint.id}", json={"base_cost": 5}).status_code == 409


def test_atomic_unlock_rejects_duplicate(ladder: SimpleNamespace) -> None:
    hint = ladder.hints[0]
    unlock = ladder.service.store.unlocks.find(hint.id, ladder.team.id)
    assert unlock is None
    ladder.service.unlock_hint(hint.id, member_id=ladder.member.id, team_id=ladder.team.id)
    from ctf_team_dashboard.features.hint_engine.models import HintUnlock

    duplicate = HintUnlock(
        id="unlock-duplicate",
        hint_id=hint.id,
        member_id=ladder.member.id,
        team_id=ladder.team.id,
        cost_paid=hint.cost,
    )
    with pytest.raises(ConflictError):
        ladder.service.store.atomic_unlock(duplicate, hint)


def test_hint_service_helpers(ladder: SimpleNamespace) -> None:
    assert [point.cost for point in ladder.service.curve_for(ladder.hints[0])] == [25, 50, 100]
    assert ladder.service.hint_price(3, 25, 2.0) == 100
    with pytest.raises(ValidationError):
        ladder.service.hint_price(4, 25, 2.0)
    assert ladder.service.get_budget(ladder.team.id).total == DEFAULT_BUDGET_TOTAL


def test_challenge_view_validates_scope(ladder: SimpleNamespace) -> None:
    with pytest.raises(NotFoundError):
        ladder.service.challenge_view(ladder.challenge.id, team_id="team-missing")
    with pytest.raises(NotFoundError):
        ladder.service.challenge_view("challenge-missing", team_id=ladder.team.id)
