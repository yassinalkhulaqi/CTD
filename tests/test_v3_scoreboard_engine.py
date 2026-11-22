"""Tests for the V3 configurable scoreboard engine.

The suite covers the pure scoring arithmetic, tie-breaking and movement rules,
rule validation, snapshot persistence, service orchestration and every mounted
HTTP endpoint.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.db.engine import Database
from ctf_team_dashboard.domain.enums import ChallengeCategory, Difficulty
from ctf_team_dashboard.domain.models import Challenge, Solve, Team
from ctf_team_dashboard.errors import NotFoundError, ValidationError
from ctf_team_dashboard.features.scoreboard_engine.models import (
    MAX_SCORE,
    RankMovement,
    ScoreRule,
    ScoreSnapshot,
    SolveScore,
    build_ranking,
    categorize_scores,
    clamp_score,
    compute_solve_points,
    movement_for,
    score_solve,
    score_solves,
)
from ctf_team_dashboard.features.scoreboard_engine.service import (
    RuleDraft,
    ScoreboardService,
    raise_for_rule,
    validate_rule,
)
from ctf_team_dashboard.features.scoreboard_engine.store import ScoreStore
from ctf_team_dashboard.repositories import Repositories

BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_rule(**overrides: object) -> ScoreRule:
    """Build a scoring rule with predictable defaults for tests."""
    values: dict[str, object] = {
        "id": "rule-team-1",
        "team_id": "team-1",
        "name": "Balanced",
        "base_points": 100,
        "difficulty_multiplier": 1.0,
        "first_blood_bonus": 50,
        "hint_penalty": 10,
        "decay_factor": 0.9,
        "decay_enabled": True,
        "updated_at": BASE_TIME,
    }
    values.update(overrides)
    return ScoreRule(**values)  # type: ignore[arg-type]


def make_challenge(**overrides: object) -> Challenge:
    """Build a challenge with predictable defaults for tests."""
    values: dict[str, object] = {
        "id": "challenge-1",
        "team_id": "team-1",
        "title": "Nonce Reuse",
        "category": ChallengeCategory.CRYPTO,
        "difficulty": Difficulty.EASY,
        "points": 100,
        "created_at": BASE_TIME,
    }
    values.update(overrides)
    return Challenge(**values)  # type: ignore[arg-type]


def make_solve(**overrides: object) -> Solve:
    """Build a solve with predictable defaults for tests."""
    values: dict[str, object] = {
        "id": "solve-1",
        "challenge_id": "challenge-1",
        "member_id": "member-1",
        "solved_at": BASE_TIME,
    }
    values.update(overrides)
    return Solve(**values)  # type: ignore[arg-type]


def make_score(
    points: int,
    solved_at: datetime = BASE_TIME,
    category: ChallengeCategory = ChallengeCategory.WEB,
) -> object:
    """Build a minimal solve score used by ranking tests."""
    return SolveScore(
        solve_id=f"solve-{points}",
        challenge_id="challenge-1",
        title="Challenge",
        category=category,
        difficulty=Difficulty.EASY,
        solve_index=0,
        solved_at=solved_at,
        base_points=float(points),
        difficulty_weight=1.0,
        difficulty_multiplier=1.0,
        decay=1.0,
        first_blood=False,
        first_blood_bonus=0,
        hint_count=0,
        hint_penalty=0,
        points=points,
    )


def make_draft(**overrides: object) -> RuleDraft:
    """Build a valid rule draft with optional overrides."""
    values: dict[str, object] = {
        "name": "Balanced",
        "base_points": 100,
        "difficulty_multiplier": 1.0,
        "first_blood_bonus": 50,
        "hint_penalty": 10,
        "decay_factor": 0.9,
        "decay_enabled": True,
    }
    values.update(overrides)
    return RuleDraft(**values)  # type: ignore[arg-type]


def first_team(seeded: Repositories) -> Team:
    """Return the first seeded team."""
    teams = seeded.teams.list_all()
    assert teams
    return teams[0]


# ----------------------------------------------------------------------
# Pure scoring arithmetic
# ----------------------------------------------------------------------
def test_solve_points_apply_difficulty_weight_and_multiplier() -> None:
    """The base score is scaled by difficulty weight and the rule multiplier."""
    rule = make_rule(base_points=100, difficulty_multiplier=2.0)
    easy = make_challenge(difficulty=Difficulty.EASY)
    hard = make_challenge(difficulty=Difficulty.HARD)
    solve = make_solve()
    assert compute_solve_points(rule, easy, solve) == 200
    assert compute_solve_points(rule, hard, solve) == 600


def test_decay_reduces_later_solve_points() -> None:
    """The decay exponent grows with the chronological solve index."""
    rule = make_rule(base_points=100, decay_factor=0.5)
    challenge = make_challenge()
    solve = make_solve()
    assert compute_solve_points(rule, challenge, solve, solve_index=0) == 100
    assert compute_solve_points(rule, challenge, solve, solve_index=1) == 50
    assert compute_solve_points(rule, challenge, solve, solve_index=2) == 25


def test_decay_can_be_disabled() -> None:
    """A flat policy awards identical points for every solve index."""
    rule = make_rule(decay_factor=0.2, decay_enabled=False)
    challenge = make_challenge()
    solve = make_solve()
    assert rule.is_decaying is False
    assert compute_solve_points(rule, challenge, solve, solve_index=9) == 100


def test_first_blood_bonus_and_hint_penalty() -> None:
    """Bonuses and penalties are added after difficulty and decay."""
    rule = make_rule(base_points=100, first_blood_bonus=50, hint_penalty=10)
    challenge = make_challenge()
    solve = make_solve()
    assert compute_solve_points(rule, challenge, solve, is_first_blood=True) == 150
    assert compute_solve_points(rule, challenge, solve, hint_count=2) == 80
    assert compute_solve_points(rule, challenge, solve, is_first_blood=True, hint_count=2) == 130


def test_points_are_clamped_to_the_legal_range() -> None:
    """Heavy penalties clamp to zero and extreme scores clamp to the maximum."""
    rule = make_rule(base_points=100, hint_penalty=1000)
    assert compute_solve_points(rule, make_challenge(), make_solve(), hint_count=3) == 0
    huge = make_rule(base_points=100_000, difficulty_multiplier=10.0)
    insane = make_challenge(difficulty=Difficulty.INSANE)
    assert compute_solve_points(huge, insane, make_solve()) == MAX_SCORE


def test_clamp_score_rounds_before_clamping() -> None:
    """Raw scores are rounded to the nearest integer."""
    assert clamp_score(12.4) == 12
    assert clamp_score(12.6) == 13
    assert clamp_score(-4.0) == 0


def test_score_solve_exposes_the_full_formula() -> None:
    """The itemised result carries each component and a printable formula."""
    rule = make_rule(base_points=100, difficulty_multiplier=2.0, decay_factor=0.5)
    scored = score_solve(
        rule,
        make_challenge(difficulty=Difficulty.EASY),
        make_solve(),
        solve_index=1,
        is_first_blood=True,
        hint_count=1,
    )
    assert scored.weighted_base == 200.0
    assert scored.decayed_base == 100.0
    assert scored.bonus_points == 50
    assert scored.penalty_points == 10
    assert scored.points == 140
    assert "140" in scored.formula


def test_score_solves_orders_chronologically_and_marks_first_blood() -> None:
    """Earlier solves receive the lower index and the first blood bonus."""
    first = make_solve(id="solve-first", solved_at=BASE_TIME)
    second = make_solve(id="solve-second", solved_at=BASE_TIME + timedelta(minutes=5))
    scores = score_solves(
        make_rule(first_blood_bonus=50),
        [make_challenge()],
        [second, first],
    )
    assert [score.solve_id for score in scores] == ["solve-first", "solve-second"]
    assert scores[0].first_blood is True
    assert scores[0].solve_index == 0
    assert scores[1].first_blood is False
    assert scores[1].solve_index == 1
    assert scores[0].points > scores[1].points


def test_score_solves_uses_hint_counts_and_skips_unknown_challenges() -> None:
    """Hint counts are per solve and orphaned solves are ignored."""
    known = make_solve(id="solve-known")
    orphan = make_solve(id="solve-orphan", challenge_id="missing")
    scores = score_solves(
        make_rule(first_blood_bonus=0, hint_penalty=10),
        [make_challenge()],
        [known, orphan],
        hint_counts={"solve-known": 3},
    )
    assert len(scores) == 1
    assert scores[0].points == 70
    assert scores[0].hint_count == 3


# ----------------------------------------------------------------------
# Ranking, tie-breaks and movement
# ----------------------------------------------------------------------
def test_ranking_sorts_by_points_then_solves_then_earliest_last_solve() -> None:
    """Ties on points fall through to solves and then to solve timing."""
    teams = [
        Team(id="team-a", name="Alpha", slug="alpha"),
        Team(id="team-b", name="Bravo", slug="bravo"),
        Team(id="team-c", name="Charlie", slug="charlie"),
        Team(id="team-d", name="Delta", slug="delta"),
    ]
    single = make_score(200, BASE_TIME)
    early_pair = [
        make_score(200, BASE_TIME, ChallengeCategory.WEB),
        make_score(200, BASE_TIME, ChallengeCategory.WEB),
    ]
    middle_pair = [
        make_score(100, BASE_TIME, ChallengeCategory.WEB),
        make_score(100, BASE_TIME + timedelta(hours=3), ChallengeCategory.WEB),
    ]
    late_pair = [
        make_score(100, BASE_TIME, ChallengeCategory.WEB),
        make_score(100, BASE_TIME + timedelta(hours=6), ChallengeCategory.WEB),
    ]
    ranking = build_ranking(
        teams,
        {
            "team-a": early_pair,
            "team-b": [single],
            "team-c": middle_pair,
            "team-d": late_pair,
        },
    )
    assert [entry.team_id for entry in ranking] == [
        "team-a",
        "team-c",
        "team-d",
        "team-b",
    ]


def test_ranking_computes_movement_against_previous_ranks() -> None:
    """Current ranks are compared with the last persisted snapshot ranks."""
    teams = [
        Team(id="team-a", name="Alpha", slug="alpha"),
        Team(id="team-b", name="Bravo", slug="bravo"),
        Team(id="team-c", name="Charlie", slug="charlie"),
    ]
    ranking = build_ranking(
        teams,
        {
            "team-a": [make_score(300)],
            "team-b": [make_score(200)],
            "team-c": [make_score(100)],
        },
        {"team-a": 2, "team-b": 1},
    )
    assert ranking[0].movement is RankMovement.UP
    assert ranking[0].movement_steps == 1
    assert ranking[1].movement is RankMovement.DOWN
    assert ranking[2].movement is RankMovement.NEW


def test_movement_for_handles_every_direction() -> None:
    """Movement derivation covers improvement, regression and stability."""
    assert movement_for(2, 4) is RankMovement.UP
    assert movement_for(4, 2) is RankMovement.DOWN
    assert movement_for(3, 3) is RankMovement.STABLE
    assert movement_for(1, None) is RankMovement.NEW
    assert movement_for(1, 0) is RankMovement.NEW


def test_ranking_entry_exposes_display_helpers() -> None:
    """Ranking rows expose the labels consumed by the table and badges."""
    entry = build_ranking(
        [Team(id="team-a", name="Alpha", slug="alpha")],
        {"team-a": [make_score(120)]},
        {"team-a": 3},
    )[0]
    assert entry.movement_label == "↑2"
    assert entry.climbed is True
    assert entry.descended is False
    assert entry.is_podium is True
    assert RankMovement.DOWN.glyph == "↓"
    assert RankMovement.STABLE.tone == "neutral"


def test_categorize_scores_groups_by_category() -> None:
    """Category breakdowns sum points and count solved challenges."""
    web = make_score(100, category=ChallengeCategory.WEB)
    crypto = make_score(250, category=ChallengeCategory.CRYPTO)
    crypto2 = make_score(250, category=ChallengeCategory.CRYPTO)
    challenges = [
        make_challenge(category=ChallengeCategory.WEB),
        make_challenge(id="challenge-2", category=ChallengeCategory.CRYPTO),
        make_challenge(id="challenge-3", category=ChallengeCategory.CRYPTO),
    ]
    breakdown = categorize_scores([web, crypto, crypto2], challenges)
    assert [item.category for item in breakdown] == [
        ChallengeCategory.CRYPTO,
        ChallengeCategory.WEB,
    ]
    assert breakdown[0].points == 500
    assert breakdown[0].solves == 2
    assert breakdown[0].challenges == 2
    assert breakdown[0].share(600) == pytest.approx(500 / 600)
    assert breakdown[1].solve_rate == pytest.approx(1.0)
    assert breakdown[0].label == "Crypto"
    assert breakdown[0].accent.startswith("#")


# ----------------------------------------------------------------------
# Rules and snapshots as domain objects
# ----------------------------------------------------------------------
def test_rule_summary_and_fingerprint_are_stable() -> None:
    """Rule metadata is useful in snapshot details and stable across calls."""
    rule = make_rule()
    assert "Balanced" in rule.summary
    assert "decay 0.90" in rule.summary
    assert rule.fingerprint() == rule.fingerprint()
    assert len(rule.fingerprint()) == 8


def test_snapshot_details_tolerate_malformed_json() -> None:
    """Snapshot detail decoding never raises on corrupt payloads."""
    snapshot = ScoreSnapshot(
        id="snap-1",
        team_id="team-1",
        recorded_at=BASE_TIME,
        points=100,
        solves=2,
        rank=1,
        details_json=json.dumps({"rule_name": "Balanced", "first_bloods": 1}),
    )
    assert snapshot.details["rule_name"] == "Balanced"
    assert snapshot.rule_name == "Balanced"
    assert snapshot.is_podium is True
    assert "100 pts" in snapshot.label
    assert (
        ScoreSnapshot(
            id="snap-2",
            team_id="team-1",
            recorded_at=BASE_TIME,
            points=0,
            solves=0,
            rank=4,
            details_json="not json",
        ).details
        == {}
    )


def test_validate_rule_accepts_a_valid_draft() -> None:
    """A fully specified balanced rule passes validation."""
    assert validate_rule(make_draft()) == {}


def test_validate_rule_rejects_negative_values() -> None:
    """Every numeric field rejects negative input."""
    errors = validate_rule(make_draft(base_points=-1, first_blood_bonus=-5, hint_penalty=-2))
    assert "base_points" in errors
    assert "first_blood_bonus" in errors
    assert "hint_penalty" in errors


def test_validate_rule_rejects_multiplier_and_decay_out_of_range() -> None:
    """Multiplier and decay factors are constrained to documented intervals."""
    errors = validate_rule(make_draft(difficulty_multiplier=11.0, decay_factor=1.5))
    assert "difficulty_multiplier" in errors
    assert "decay_factor" in errors
    assert validate_rule(make_draft(decay_factor=0.01))["decay_factor"]


def test_validate_rule_requires_a_name() -> None:
    """An empty rule name is rejected."""
    assert "name" in validate_rule(make_draft(name="   "))


def test_raise_for_rule_raises_typed_validation_error() -> None:
    """Invalid drafts surface a domain error carrying field details."""
    with pytest.raises(ValidationError) as excinfo:
        raise_for_rule(make_draft(base_points=-10))
    assert excinfo.value.status_code == 422
    assert "base_points" in excinfo.value.details["fields"]


# ----------------------------------------------------------------------
# Store and service
# ----------------------------------------------------------------------
def test_schema_creates_scoreboard_tables(database: Database) -> None:
    """Migrations install both feature tables."""
    assert {"v3_score_rules", "v3_score_snapshots"} <= database.table_names()


def test_store_upsert_preserves_rule_identity(database: Database) -> None:
    """Repeated upserts update one row without changing its identifier."""
    store = ScoreStore()
    first = store.upsert_rule(make_rule(id="rule-original", team_id="team-x"))
    updated = store.upsert_rule(make_rule(id="rule-replacement", team_id="team-x", base_points=250))
    assert first.id == updated.id == "rule-original"
    assert updated.base_points == 250
    assert len(store.list_rules()) == 1


def test_store_snapshot_history_and_latest(database: Database) -> None:
    """Snapshots are listed newest first and the latest one is retrievable."""
    store = ScoreStore()
    old = store.insert_snapshot(
        "team-x",
        100,
        1,
        2,
        {"rule_name": "Balanced"},
        recorded_at=BASE_TIME - timedelta(hours=1),
    )
    new = store.insert_snapshot(
        "team-x", 250, 3, 1, {"rule_name": "Aggressive"}, recorded_at=BASE_TIME
    )
    history = store.list_snapshots("team-x")
    assert [item.id for item in history] == [new.id, old.id]
    assert store.latest_snapshot("team-x").id == new.id
    assert store.latest_ranks() == {"team-x": 1}
    assert store.snapshot_count("team-x") == 2
    assert history[0].details["rule_name"] == "Aggressive"


def test_service_returns_default_rule_and_persists_updates(
    seeded: Repositories,
) -> None:
    """A team without a stored policy receives the balanced default."""
    service = ScoreboardService()
    team = first_team(seeded)
    default = service.get_rule(team.id)
    assert default.name == "Balanced"
    saved = service.upsert_rule(team.id, make_draft(name="Aggressive", base_points=200))
    assert saved.name == "Aggressive"
    assert service.get_rule(team.id).base_points == 200


def test_service_unknown_team_raises_not_found(seeded: Repositories) -> None:
    """Operations on unknown teams raise a typed not-found error."""
    service = ScoreboardService()
    with pytest.raises(NotFoundError):
        service.get_rule("missing-team")
    with pytest.raises(NotFoundError):
        service.list_snapshots("missing-team")


def test_service_breakdown_uses_real_solve_data(seeded: Repositories) -> None:
    """The breakdown scores the seeded challenges and groups the categories."""
    team = first_team(seeded)
    breakdown = ScoreboardService().breakdown_for(team.id)
    assert breakdown.team_name == team.name
    assert breakdown.challenges == 12
    assert breakdown.total_solves == len(breakdown.scores)
    assert breakdown.total_points == sum(score.points for score in breakdown.scores)
    assert breakdown.total_points > 0
    assert breakdown.categories
    assert breakdown.first_bloods >= 0
    assert breakdown.average_points >= 0
    details = breakdown.to_details()
    assert details["team_name"] == team.name
    assert isinstance(details["categories"], list)
    assert isinstance(details["top_solves"], list)


def test_service_rule_change_affects_scores(seeded: Repositories) -> None:
    """Changing a rule immediately changes the live breakdown."""
    service = ScoreboardService()
    team = first_team(seeded)
    before = service.breakdown_for(team.id).total_points
    service.upsert_rule(team.id, make_draft(base_points=400, difficulty_multiplier=1.0))
    after = service.breakdown_for(team.id).total_points
    assert after > before


def test_service_snapshot_captures_rank_and_details(seeded: Repositories) -> None:
    """Creating a snapshot persists the score, rank and rule fingerprint."""
    service = ScoreboardService()
    team = first_team(seeded)
    snapshot = service.create_snapshot(team.id)
    assert snapshot.rank == 1
    assert snapshot.points == service.breakdown_for(team.id).total_points
    assert snapshot.details["rule_name"] == "Balanced"
    assert "rule_fingerprint" in snapshot.details
    assert service.latest_snapshot(team.id).id == snapshot.id


def test_service_ranking_uses_previous_snapshot_for_movement(
    seeded: Repositories,
) -> None:
    """After snapshots exist, live ranking entries report stable movement."""
    service = ScoreboardService()
    teams = seeded.teams.list_all()
    for team in teams:
        service.create_snapshot(team.id)
    ranking = service.ranking()
    assert len(ranking) == len(teams)
    assert [entry.rank for entry in ranking] == list(range(1, len(teams) + 1))
    assert all(entry.movement is RankMovement.STABLE for entry in ranking)
    assert all(entry.previous_rank == entry.rank for entry in ranking)


def test_service_snapshot_series_is_chronological(seeded: Repositories) -> None:
    """The points series returned to the sparkline is oldest first."""
    service = ScoreboardService()
    team = first_team(seeded)
    first = service.create_snapshot(team.id)
    second = service.create_snapshot(team.id)
    series = service.snapshot_series(team.id)
    assert len(series) == 2
    assert series[0] == first.points
    assert series[1] == second.points


# ----------------------------------------------------------------------
# Router endpoints
# ----------------------------------------------------------------------
def test_router_get_rule_returns_default(client: TestClient, seeded: Repositories) -> None:
    """GET /rules returns the effective rule of a team."""
    team = first_team(seeded)
    response = client.get(f"/api/scoreboard/rules/{team.id}")
    assert response.status_code == 200
    assert response.json()["team_id"] == team.id
    assert response.json()["name"] == "Balanced"


def test_router_put_rule_updates_policy(client: TestClient, seeded: Repositories) -> None:
    """PUT /rules persists valid configuration."""
    team = first_team(seeded)
    payload = {
        "name": "Aggressive",
        "base_points": 220,
        "difficulty_multiplier": 2.0,
        "first_blood_bonus": 75,
        "hint_penalty": 5,
        "decay_factor": 0.8,
        "decay_enabled": False,
    }
    response = client.put(f"/api/scoreboard/rules/{team.id}", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["base_points"] == 220
    assert body["decay_enabled"] is False
    assert client.get(f"/api/scoreboard/rules/{team.id}").json()["name"] == "Aggressive"


def test_router_put_rule_rejects_invalid_values(client: TestClient, seeded: Repositories) -> None:
    """Invalid rules return the shared error envelope."""
    team = first_team(seeded)
    response = client.put(
        f"/api/scoreboard/rules/{team.id}",
        json={
            "name": "Broken",
            "base_points": -1,
            "difficulty_multiplier": 50.0,
            "first_blood_bonus": 0,
            "hint_penalty": 0,
            "decay_factor": 0.9,
            "decay_enabled": True,
        },
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "difficulty_multiplier" in body["error"]["details"]["fields"]


def test_router_ranking_returns_ranked_entries(client: TestClient, seeded: Repositories) -> None:
    """GET /ranking returns one entry per team with contiguous ranks."""
    response = client.get("/api/scoreboard/ranking")
    assert response.status_code == 200
    body = response.json()
    assert body["team_count"] == len(seeded.teams.list_all())
    assert [entry["rank"] for entry in body["entries"]] == list(range(1, body["team_count"] + 1))
    assert body["leader_points"] >= body["total_points"] / body["team_count"]


def test_router_breakdown_returns_categories(client: TestClient, seeded: Repositories) -> None:
    """GET /breakdown exposes itemised categories and solve formulas."""
    team = first_team(seeded)
    response = client.get(f"/api/scoreboard/teams/{team.id}/breakdown")
    assert response.status_code == 200
    body = response.json()
    assert body["total_solves"] == len(body["solves"])
    assert body["categories"]
    assert body["solves"][0]["formula"]
    assert body["rule"]["team_id"] == team.id


def test_router_snapshot_endpoints(client: TestClient, seeded: Repositories) -> None:
    """POST /snapshot followed by GET /snapshots returns the new record."""
    team = first_team(seeded)
    created = client.post(f"/api/scoreboard/snapshot/{team.id}")
    assert created.status_code == 200
    assert created.json()["details"]["rule_name"] == "Balanced"
    history = client.get(f"/api/scoreboard/snapshots/{team.id}")
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["id"] == created.json()["id"]


def test_router_unknown_team_returns_not_found(client: TestClient, seeded: Repositories) -> None:
    """Missing teams produce a typed 404 response."""
    for path in (
        "/api/scoreboard/rules/missing",
        "/api/scoreboard/teams/missing/breakdown",
        "/api/scoreboard/snapshots/missing",
    ):
        response = client.get(path)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
