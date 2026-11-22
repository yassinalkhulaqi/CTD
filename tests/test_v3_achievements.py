"""Tests for the achievement badge engine."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.achievements.models import (
    AchievementProgress,
    Badge,
    BadgeTier,
    CriteriaKind,
    deterministic_award_id,
    merge_views,
    normalise_metrics,
    progress_percent,
    rank_rows,
    rarity_label,
    rarity_score,
)
from ctf_team_dashboard.features.achievements.service import (
    AchievementService,
    MemberMetrics,
)
from ctf_team_dashboard.features.achievements.store import AchievementStore
from ctf_team_dashboard.repositories import Repositories


def make_badge(
    badge_id: str = "badge-test",
    *,
    target: int = 3,
    kind: CriteriaKind = CriteriaKind.SOLVES,
    tier: BadgeTier = BadgeTier.BRONZE,
    secret: bool = False,
) -> Badge:
    """Build a badge fixture with predictable values."""
    return Badge(
        id=badge_id,
        name=f"Badge {badge_id}",
        description="A test badge",
        tier=tier,
        criteria_kind=kind,
        criteria_value=target,
        icon="star",
        points=100,
        secret=secret,
    )


# ----------------------------------------------------------------------
# Pure domain tests
# ----------------------------------------------------------------------
def test_progress_percent_is_clamped_and_rounded() -> None:
    assert progress_percent(0, 10) == 0.0
    assert progress_percent(3, 4) == 75.0
    assert progress_percent(1, 3) == 33.3
    assert progress_percent(50, 10) == 100.0
    assert progress_percent(5, 0) == 0.0


def test_tier_properties_follow_prestige_order() -> None:
    assert [tier.rank for tier in BadgeTier] == [1, 2, 3]
    assert BadgeTier.BRONZE.multiplier == 1.0
    assert BadgeTier.GOLD.multiplier == 2.25
    assert BadgeTier.SILVER.next() is BadgeTier.GOLD
    assert BadgeTier.GOLD.next() is None
    assert make_badge(tier=BadgeTier.GOLD).score == 225


def test_normalise_metrics_folds_aliases_and_rejects_garbage() -> None:
    metrics = normalise_metrics(
        {
            "solved": 4,
            "solve_count": 6,
            "unique_categories": 3,
            "current_streak": "5",
            "hints_used": -2,
            "unknown": 99,
        }
    )
    assert metrics["solves"] == 6.0
    assert metrics["categories"] == 3.0
    assert metrics["streak"] == 5.0
    assert metrics["hints"] == 0.0
    assert set(metrics) == {"solves", "categories", "streak", "hints"}


def test_hint_criteria_counts_down_to_target() -> None:
    badge = make_badge(kind=CriteriaKind.HINTS, target=4)
    metrics = normalise_metrics({"hints_used": 2})
    evaluation = badge.evaluate(metrics)
    assert evaluation.current == 2
    assert evaluation.percent == 50.0
    assert not evaluation.qualifies

    success = badge.evaluate(normalise_metrics({"hints": 0}))
    assert success.current == 4
    assert success.qualifies


def test_rarity_score_and_bands() -> None:
    assert rarity_score(0, 10) == 100.0
    assert rarity_score(5, 10) == 50.0
    assert rarity_score(10, 10) == 0.0
    assert rarity_score(1, 0) == 0.0
    assert rarity_label(95) == "legendary"
    assert rarity_label(72) == "rare"
    assert rarity_label(45) == "uncommon"
    assert rarity_label(10) == "common"


def test_badge_view_masks_secret_until_revealed() -> None:
    badge = make_badge(secret=True)
    hidden = merge_views([badge], {}, [], {}, {}).pop()
    assert hidden.display_name == "???"
    assert hidden.display_icon == "question-mark"
    assert not hidden.revealed

    revealed = merge_views([badge], {}, [badge.id], {}, {}).pop()
    assert revealed.display_name == badge.name
    assert revealed.revealed
    assert revealed.status == "unlocked"


def test_leaderboard_ranking_uses_dense_ties() -> None:
    from ctf_team_dashboard.features.achievements.models import LeaderboardRow

    rows = [
        LeaderboardRow("m1", "amy", "Amy", 2, 300),
        LeaderboardRow("m2", "bob", "Bob", 3, 300),
        LeaderboardRow("m3", "cy", "Cy", 1, 100),
    ]
    ranked = rank_rows(rows)
    assert [row.rank for row in ranked] == [1, 1, 3]
    assert ranked[0].member_id == "m2"


def test_progress_record_is_monotonic() -> None:
    record = AchievementProgress("member-1", "badge-1", 4, 10)
    assert record.percent == 40.0
    assert record.remaining == 6
    assert record.advanced_to(2) is record
    assert record.advanced_to(8).current == 8
    assert record.advanced_to(40).current == 10
    assert record.advanced_to(10).is_complete


# ----------------------------------------------------------------------
# Store tests
# ----------------------------------------------------------------------
def test_store_seeding_is_idempotent(database: Any) -> None:
    del database
    store = AchievementStore()
    first = store.badges.seed([make_badge("badge-one"), make_badge("badge-two")])
    second = store.badges.seed([make_badge("badge-one"), make_badge("badge-three")])
    assert first == 2
    assert second == 1
    assert len(store.badges.list_all()) == 3
    assert store.badges.get("badge-one") is not None
    assert store.badges.delete("badge-two")
    assert store.badges.get("badge-two") is None


def test_store_award_once_is_idempotent(database: Any) -> None:
    del database
    store = AchievementStore()
    store.badges.create(make_badge())
    first = store.awards.award_once("badge-test", "member-1", {"observed": 3})
    second = store.awards.award_once("badge-test", "member-1", {"observed": 99})
    assert first is not None
    assert second is None
    assert first.id == deterministic_award_id("badge-test", "member-1")
    assert store.awards.count_for_badge("badge-test") == 1
    assert store.awards.count_all() == 1


def test_store_progress_upsert_and_retrieval(database: Any) -> None:
    del database
    store = AchievementStore()
    store.badges.create(make_badge())
    record = AchievementProgress("member-1", "badge-test", 2, 5)
    store.progress.upsert(record)
    assert store.progress.get("member-1", "badge-test") == record
    store.progress.upsert(AchievementProgress("member-1", "badge-test", 4, 5))
    assert store.progress.get("member-1", "badge-test").current == 4
    assert len(store.progress.list_for_member("member-1")) == 1
    assert store.progress.clear_member("member-1") == 1


# ----------------------------------------------------------------------
# Service tests
# ----------------------------------------------------------------------
def test_service_seeds_and_lists_catalogue(seeded: Repositories) -> None:
    del seeded
    service = AchievementService()
    result = service.seed_catalogue()
    assert result.total >= 16
    badges = service.list_badges()
    assert badges
    assert any(view.badge.secret and not view.revealed for view in badges)
    assert all(view.display_name for view in badges)


def test_service_create_badge_validation(seeded: Repositories) -> None:
    del seeded
    service = AchievementService()
    service.seed_catalogue()
    with pytest.raises(ValidationError):
        service.create_badge(name="   ")
    with pytest.raises(ValidationError):
        service.create_badge(name="Bad", criteria_value=0)
    with pytest.raises(ValidationError):
        service.create_badge(name="Bad", points=-5)
    with pytest.raises(ConflictError):
        service.create_badge(name="Duplicate", badge_id="badge-first-blood")
    created = service.create_badge(name="  Custom Badge  ", criteria_value=2)
    assert created.name == "Custom Badge"
    assert created.id.startswith("badge-custom-badge")


def test_service_evaluate_awards_and_is_idempotent(seeded: Repositories) -> None:
    member = seeded.members.list_all()[0]
    service = AchievementService()
    service.seed_catalogue()
    first = service.evaluate_metrics(member.id, {"solves": 1})
    assert first.unlocked >= 1
    assert any(outcome.newly_awarded for outcome in first.outcomes)
    second = service.evaluate_metrics(member.id, {"solves": 1})
    assert second.unlocked == 0
    assert second.eligible >= 1
    assert len(service.store.awards.list_for_member(member.id)) == first.unlocked


def test_service_evaluate_can_skip_persistence(seeded: Repositories) -> None:
    member = seeded.members.list_all()[0]
    service = AchievementService()
    service.seed_catalogue()
    result = service.evaluate_metrics(member.id, {"solves": 50}, persist=False, grant_awards=False)
    assert result.evaluated > 0
    assert result.unlocked == 0
    assert service.store.awards.list_for_member(member.id) == []
    assert service.store.progress.list_for_member(member.id) == []


def test_service_progress_never_regresses(seeded: Repositories) -> None:
    member = seeded.members.list_all()[0]
    service = AchievementService()
    service.seed_catalogue()
    service.evaluate_metrics(member.id, {"solves": 10}, grant_awards=False)
    service.evaluate_metrics(member.id, {"solves": 2}, grant_awards=False)
    records = {
        record.badge_id: record for record in service.store.progress.list_for_member(member.id)
    }
    assert records["badge-warmup"].current == 5
    assert records["badge-veteran-solver"].current == 10


def test_service_recompute_progress(seeded: Repositories) -> None:
    member = seeded.members.list_all()[0]
    service = AchievementService()
    service.seed_catalogue()
    records = service.recompute_progress(member.id, {"categories": 4, "streak": 7})
    assert len(records) >= 16
    assert any(record.badge_id == "badge-wide-spectrum" for record in records)
    assert service.store.awards.list_for_member(member.id) == []


def test_service_award_is_idempotent_and_strict_mode_conflicts(
    seeded: Repositories,
) -> None:
    member = seeded.members.list_all()[0]
    service = AchievementService()
    service.seed_catalogue()
    first = service.award(member.id, "badge-first-blood")
    assert first.awarded
    assert first.award is not None
    second = service.award(member.id, "badge-first-blood")
    assert not second.awarded
    assert second.award is not None
    assert second.award.id == first.award.id
    with pytest.raises(ConflictError):
        service.award(member.id, "badge-first-blood", strict=True)


def test_service_award_rejects_unknown_resources(seeded: Repositories) -> None:
    del seeded
    service = AchievementService()
    service.seed_catalogue()
    with pytest.raises(NotFoundError):
        service.award("missing-member", "badge-first-blood")
    with pytest.raises(NotFoundError):
        service.award("member-0001", "missing-badge")


def test_service_get_badge_hides_secrets(seeded: Repositories) -> None:
    del seeded
    service = AchievementService()
    service.seed_catalogue()
    assert service.get_badge("badge-first-blood").name == "First Blood"
    with pytest.raises(NotFoundError):
        service.get_badge("badge-night-owl")


def test_service_batch_evaluation(seeded: Repositories) -> None:
    members = seeded.members.list_all()[:2]
    service = AchievementService()
    service.seed_catalogue()
    results = service.evaluate_many(
        [
            MemberMetrics(member_id=members[0].id, metrics={"solves": 1}),
            MemberMetrics(member_id=members[1].id, metrics={"solves": 5}),
        ]
    )
    assert len(results) == 2
    assert results[0].member_id == members[0].id
    assert results[1].unlocked >= results[0].unlocked


def test_service_leaderboard_and_stats(seeded: Repositories) -> None:
    member = seeded.members.list_all()[0]
    service = AchievementService()
    service.seed_catalogue()
    service.evaluate_metrics(member.id, {"solves": 5, "categories": 2})
    leaderboard = service.leaderboard()
    assert leaderboard
    assert leaderboard[0].member_id == member.id
    assert leaderboard[0].rank == 1
    stats = service.stats()
    assert stats.badges >= 16
    assert stats.awards >= 1
    assert stats.members == len(seeded.members.list_all())
    assert stats.participation_rate > 0
    assert stats.points_per_member > 0


def test_service_member_summary(seeded: Repositories) -> None:
    member = seeded.members.list_all()[0]
    service = AchievementService()
    service.seed_catalogue()
    service.evaluate_metrics(member.id, {"solves": 2})
    summary = service.member_summary(member.id)
    assert summary.unlocked >= 1
    assert summary.points > 0
    assert summary.next_badge is not None
    assert summary.completion > 0
    assert summary.recent_awards()


# ----------------------------------------------------------------------
# Router tests
# ----------------------------------------------------------------------
def test_router_lists_badges(client: TestClient, seeded: Repositories) -> None:
    del seeded
    response = client.get("/api/achievements")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 16
    assert payload["badges"][0]["badge"]["id"]

    filtered = client.get("/api/achievements/badges", params={"tier": "gold"})
    assert filtered.status_code == 200
    assert all(item["badge"]["tier"] == "gold" for item in filtered.json()["badges"])

    public = client.get("/api/achievements", params={"include_secret": "false"})
    assert all(not item["badge"]["secret"] for item in public.json()["badges"])


def test_router_creates_badge(client: TestClient, seeded: Repositories) -> None:
    del seeded
    response = client.post(
        "/api/achievements/badges",
        json={
            "name": "Router Badge",
            "tier": "silver",
            "criteria_kind": "streak",
            "criteria_value": 4,
            "points": 120,
            "icon": "bolt",
        },
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Router Badge"
    assert response.json()["score"] == 180

    duplicate = client.post(
        "/api/achievements/badges",
        json={"name": "Router Badge", "id": response.json()["id"]},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict"


def test_router_badge_detail(client: TestClient, seeded: Repositories) -> None:
    del seeded
    response = client.get("/api/achievements/badges/badge-first-blood")
    assert response.status_code == 200
    assert response.json()["badge"]["badge"]["name"] == "First Blood"
    hidden = client.get("/api/achievements/badges/badge-night-owl")
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "not_found"


def test_router_evaluates_member(client: TestClient, seeded: Repositories) -> None:
    member = seeded.members.list_all()[0]
    response = client.post(
        "/api/achievements/evaluate",
        json={"member_id": member.id, "metrics": {"solves": 1}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["member_id"] == member.id
    assert payload["unlocked"] >= 1
    assert payload["outcomes"][0]["criteria_kind"] in {"solves", "categories", "streak", "hints"}

    missing = client.post(
        "/api/achievements/evaluate",
        json={"member_id": "absent", "metrics": {}},
    )
    assert missing.status_code == 404


def test_router_evaluates_batch(client: TestClient, seeded: Repositories) -> None:
    members = seeded.members.list_all()[:2]
    response = client.post(
        "/api/achievements/evaluate/batch",
        json={
            "submissions": [
                {"member_id": members[0].id, "metrics": {"solves": 2}},
                {"member_id": members[1].id, "metrics": {"categories": 3}},
            ]
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["evaluated_members"] == 2
    assert len(payload["results"]) == 2
    assert payload["total_unlocked"] >= 1


def test_router_member_views(client: TestClient, seeded: Repositories) -> None:
    member = seeded.members.list_all()[0]
    client.post(
        "/api/achievements/evaluate",
        json={"member_id": member.id, "metrics": {"solves": 6}},
    )
    response = client.get(f"/api/achievements/members/{member.id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["unlocked"] >= 2
    assert payload["badges"]
    assert payload["next_badge"] is not None

    progress = client.get(f"/api/achievements/members/{member.id}/progress")
    assert progress.status_code == 200
    assert progress.json()

    missing = client.get("/api/achievements/members/unknown")
    assert missing.status_code == 404


def test_router_leaderboard_and_stats(client: TestClient, seeded: Repositories) -> None:
    member = seeded.members.list_all()[0]
    client.post(
        "/api/achievements/evaluate",
        json={"member_id": member.id, "metrics": {"solves": 3}},
    )
    board = client.get("/api/achievements/leaderboard")
    assert board.status_code == 200
    assert board.json()["entries"][0]["member_id"] == member.id

    stats = client.get("/api/achievements/stats")
    assert stats.status_code == 200
    assert stats.json()["badges"] >= 16
    assert stats.json()["participation_rate"] > 0


def test_router_manual_award_is_idempotent(client: TestClient, seeded: Repositories) -> None:
    member = seeded.members.list_all()[0]
    url = f"/api/achievements/members/{member.id}/awards/badge-first-blood"
    first = client.post(url, json={"evidence": {"source": "test"}})
    assert first.status_code == 201
    assert first.json()["awarded"] is True
    second = client.post(url, json={})
    assert second.status_code == 201
    assert second.json()["awarded"] is False
    assert second.json()["award"]["id"] == first.json()["award"]["id"]


def test_router_seed_endpoint_and_validation(client: TestClient, seeded: Repositories) -> None:
    assert client.get("/api/achievements").status_code == 200
    service = AchievementService()
    service.store.badges.delete("badge-first-blood")
    seeded_result = client.post("/api/achievements/seed")
    assert seeded_result.status_code == 201
    assert seeded_result.json()["created"] == 1

    invalid = client.get("/api/achievements", params={"tier": "platinum"})
    assert invalid.status_code == 422

    created = client.post("/api/achievements/badges", json={"name": "   "})
    assert created.status_code == 422


def test_award_freshness_uses_timezone_aware_timestamps() -> None:
    from ctf_team_dashboard.features.achievements.models import AchievementAward

    fresh = AchievementAward("a", "b", "m", utcnow(), {})
    stale = AchievementAward("b", "b", "m", utcnow() - timedelta(hours=48), {})
    assert fresh.is_fresh
    assert not stale.is_fresh
    assert fresh.evidence_summary
