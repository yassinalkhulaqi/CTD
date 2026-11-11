"""End to end integration tests exercising the whole stack."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from tests.factories import Factory, build_scenario

from ctf_team_dashboard.repositories import Repositories


def _persist(repositories: Repositories) -> None:
    """Persist a complete competition scenario."""
    teams, members, challenges, solves = build_scenario()
    for team in teams:
        repositories.teams.create(team)
    for member in members:
        repositories.members.create(member)
    for challenge in challenges:
        repositories.challenges.create(challenge)
    for solve in solves:
        repositories.solves.create(solve)


def test_full_competition_lifecycle(client: TestClient, repositories: Repositories) -> None:
    """A team, a member, a challenge and a solve should flow through the API."""
    team = client.post("/api/teams", json={"name": "Lifecycle Crew"}).json()
    member = client.post(
        "/api/members", json={"team_id": team["id"], "handle": "lifecycle"}
    ).json()
    challenge = client.post(
        "/api/challenges",
        json={
            "team_id": team["id"],
            "title": "Lifecycle Challenge",
            "category": "web",
            "difficulty": "medium",
            "points": 150,
        },
    ).json()

    solve = client.post(
        "/api/solves",
        json={
            "challenge_id": challenge["id"],
            "member_id": member["id"],
            "flag": "flag{lifecycle}",
        },
    )
    assert solve.status_code == 201
    assert solve.json()["points_awarded"] == 262

    board = client.get("/api/challenges/board", params={"team_id": team["id"]}).json()
    assert len(board["solved"]) == 1

    leaderboard = client.get("/api/teams/scoreboard").json()
    row = next(entry for entry in leaderboard if entry["team_id"] == team["id"])
    assert row["solves"] == 1
    assert row["points"] == 262


def test_dashboard_snapshot_matches_the_individual_endpoints(
    client: TestClient, repositories: Repositories
) -> None:
    """The snapshot should agree with the granular endpoints."""
    _persist(repositories)

    snapshot = client.get("/api/dashboard").json()
    overview = client.get("/api/stats/overview").json()
    assert snapshot["overview"] == overview

    leaderboard = client.get("/api/stats/leaderboard").json()
    assert snapshot["scoreboard"] == leaderboard

    categories = client.get("/api/stats/categories").json()
    assert snapshot["categories"] == categories


def test_challenge_filters_are_applied(
    client: TestClient, repositories: Repositories
) -> None:
    """The challenge filters should narrow the result."""
    _persist(repositories)

    everything = client.get("/api/challenges").json()
    crypto = client.get("/api/challenges", params={"category": "crypto"}).json()
    assert len(crypto) < len(everything)
    assert all(challenge["category"] == "crypto" for challenge in crypto)


def test_status_filter_is_applied(client: TestClient, repositories: Repositories) -> None:
    """The status filter should narrow the result."""
    _persist(repositories)

    active = client.get("/api/challenges", params={"status": "active"}).json()
    assert all(challenge["status"] == "active" for challenge in active)


def test_member_contributions_are_aggregated(
    client: TestClient, repositories: Repositories
) -> None:
    """The contribution endpoint should aggregate the solves per member."""
    _persist(repositories)

    contributions = client.get("/api/members/contributions").json()
    assert contributions
    assert all("solves" in entry and "points" in entry for entry in contributions)
    assert sum(entry["solves"] for entry in contributions) == len(
        repositories.solves.list_all()
    )


def test_solve_withdrawal_reopens_the_challenge(
    client: TestClient, repositories: Repositories
) -> None:
    """Withdrawing the last solve should reopen the challenge."""
    factory = Factory(prefix="w")
    team = factory.team(name="Withdrawal Crew")
    repositories.teams.create(team)
    member = factory.member(team_id=team.id, handle="withdrawer")
    repositories.members.create(member)
    challenge = factory.challenge(team_id=team.id, title="Withdrawable")
    repositories.challenges.create(challenge)

    solve = client.post(
        "/api/solves",
        json={"challenge_id": challenge.id, "member_id": member.id, "flag": "flag{undo}"},
    ).json()
    assert client.get(f"/api/challenges/{challenge.id}").json()["status"] == "solved"

    assert client.delete(f"/api/solves/{solve['id']}").status_code == 204
    assert client.get(f"/api/challenges/{challenge.id}").json()["status"] == "active"


def test_duplicate_solve_is_rejected(client: TestClient, repositories: Repositories) -> None:
    """The same member cannot solve a challenge twice."""
    factory = Factory(prefix="d")
    team = factory.team(name="Duplicate Crew")
    repositories.teams.create(team)
    member = factory.member(team_id=team.id, handle="duplicator")
    repositories.members.create(member)
    challenge = factory.challenge(team_id=team.id, title="Duplicate")
    repositories.challenges.create(challenge)

    payload = {
        "challenge_id": challenge.id,
        "member_id": member.id,
        "flag": "flag{dupe}",
    }
    assert client.post("/api/solves", json=payload).status_code == 201
    conflict = client.post("/api/solves", json=payload)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "conflict"


def test_deleting_a_team_removes_its_challenges(
    client: TestClient, repositories: Repositories
) -> None:
    """Deleting a team should cascade to its dependent records."""
    factory = Factory(prefix="c")
    team = factory.team(name="Cascade Crew")
    repositories.teams.create(team)
    member = factory.member(team_id=team.id, handle="cascader")
    repositories.members.create(member)
    challenge = factory.challenge(team_id=team.id, title="Cascade")
    repositories.challenges.create(challenge)

    assert client.delete(f"/api/teams/{team.id}").status_code == 204
    assert repositories.challenges.get(challenge.id) is None
    assert repositories.members.get(member.id) is None


def test_activity_feed_records_the_mutations(
    client: TestClient, repositories: Repositories
) -> None:
    """Every mutation should leave a trace in the activity feed."""
    team = client.post("/api/teams", json={"name": "Audited Crew"}).json()
    client.post("/api/members", json={"team_id": team["id"], "handle": "tracer"})
    client.post(
        "/api/challenges",
        json={
            "team_id": team["id"],
            "title": "Traced Challenge",
            "category": "misc",
            "difficulty": "easy",
        },
    )

    events = client.get("/api/stats/events", params={"limit": 50}).json()
    kinds = {event["kind"] for event in events}
    assert "team.updated" in kinds
    assert "member.updated" in kinds
    assert "challenge.created" in kinds


def test_competition_window_is_derived_from_the_challenges(
    client: TestClient, repositories: Repositories
) -> None:
    """The competition window should reflect the persisted challenges."""
    factory = Factory(prefix="w")
    team = factory.team(name="Window Crew")
    repositories.teams.create(team)
    now = datetime.now(timezone.utc)
    challenge = factory.challenge(
        team_id=team.id,
        title="Windowed",
        starts_at=now - timedelta(hours=2),
        ends_at=now + timedelta(hours=4),
    )
    repositories.challenges.create(challenge)

    competition = client.get("/api/stats/competition").json()
    assert competition["total_seconds"] > 0
    assert competition["seconds_remaining"] > 0
    assert 0 < competition["progress"] < 1
