"""API level tests for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ctf_team_dashboard.repositories import Repositories


def test_health_endpoint(client: TestClient) -> None:
    """The health endpoint should report an ok status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_endpoint(client: TestClient) -> None:
    """The readiness endpoint should confirm database connectivity."""
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    assert response.json()["database"] is True


def test_list_teams_is_seeded(client: TestClient) -> None:
    """The seeded dataset should expose several teams."""
    response = client.get("/api/teams")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 1
    assert payload[0]["initials"]


def test_overview_stats(client: TestClient) -> None:
    """The overview endpoint should return the aggregated counters."""
    response = client.get("/api/stats/overview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["teams"] >= 1
    assert payload["challenges"] >= 1
    assert 0 <= payload["completion_rate"] <= 1


def test_category_stats(client: TestClient) -> None:
    """The category endpoint should return labelled categories."""
    response = client.get("/api/stats/categories")
    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert "label" in payload[0]
    assert "accent" in payload[0]


def test_create_and_fetch_team(client: TestClient) -> None:
    """A created team should be retrievable through the API."""
    created = client.post(
        "/api/teams",
        json={"name": "Neon Phantoms", "color": "#22d3ee"},
    )
    assert created.status_code == 201
    team_id = created.json()["id"]

    fetched = client.get(f"/api/teams/{team_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Neon Phantoms"


def test_create_team_rejects_invalid_colour(client: TestClient) -> None:
    """An invalid colour should be rejected by the schema."""
    response = client.post("/api/teams", json={"name": "Bad", "color": "red"})
    assert response.status_code == 422


def test_unknown_team_returns_error_envelope(client: TestClient) -> None:
    """Unknown resources should return the shared error envelope."""
    response = client.get("/api/teams/does-not-exist")
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "not_found"


def test_create_challenge_and_solve(client: TestClient) -> None:
    """A full create/solve cycle should be reflected in the statistics."""
    team = client.post("/api/teams", json={"name": "Cycle Team"}).json()
    member = client.post(
        "/api/members", json={"team_id": team["id"], "handle": "analyst"}
    ).json()
    challenge = client.post(
        "/api/challenges",
        json={
            "team_id": team["id"],
            "title": "Test Challenge",
            "category": "web",
            "difficulty": "easy",
            "points": 100,
        },
    ).json()

    solve = client.post(
        "/api/solves",
        json={
            "challenge_id": challenge["id"],
            "member_id": member["id"],
            "flag": "flag{test}",
        },
    )
    assert solve.status_code == 201
    assert solve.json()["points_awarded"] == 100

    refreshed = client.get(f"/api/challenges/{challenge['id']}").json()
    assert refreshed["status"] == "solved"


def test_board_endpoint_groups_by_status(client: TestClient) -> None:
    """The board endpoint should group challenges by lifecycle status."""
    teams = client.get("/api/teams").json()
    team_id = teams[0]["id"]
    response = client.get("/api/challenges/board", params={"team_id": team_id})
    assert response.status_code == 200
    payload = response.json()
    assert "pending" in payload
    assert "solved" in payload


def test_leaderboard_endpoint(client: TestClient) -> None:
    """The leaderboard endpoint should return scoreboard rows."""
    response = client.get("/api/stats/leaderboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert "completion_rate" in payload[0]


def test_activity_endpoint(client: TestClient) -> None:
    """The activity endpoint should return the event feed."""
    response = client.get("/api/stats/activity")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_scoreboard_endpoint(client: TestClient) -> None:
    """The team scoreboard endpoint should be reachable."""
    response = client.get("/api/teams/scoreboard")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_contributions_endpoint(client: TestClient) -> None:
    """The contribution endpoint should list member statistics."""
    response = client.get("/api/members/contributions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_competition_endpoint(client: TestClient) -> None:
    """The competition endpoint should report the timing envelope."""
    response = client.get("/api/stats/competition")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_seconds"] >= 0


def test_heatmap_endpoint(client: TestClient) -> None:
    """The heatmap endpoint should return a 7x24 matrix."""
    response = client.get("/api/stats/heatmap")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 7
    assert all(len(row) == 24 for row in payload)


def test_timeline_endpoint(client: TestClient) -> None:
    """The timeline endpoint should return hourly buckets."""
    response = client.get("/api/stats/timeline", params={"hours": 12})
    assert response.status_code == 200
    assert len(response.json()) == 12


def test_openapi_schema_is_valid(client: TestClient) -> None:
    """The OpenAPI document should be generated without errors."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "paths" in response.json()


def test_seed_data_persists_solves(repositories: Repositories) -> None:
    """The seeded dataset should include solves."""
    from ctf_team_dashboard.seed import persist_seed_data

    counts = persist_seed_data(repositories, force=True)
    assert counts["teams"] > 0
    assert counts["members"] > 0
    assert counts["challenges"] > 0
