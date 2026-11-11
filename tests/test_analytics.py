"""Tests for the analytics endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from ctf_team_dashboard.domain.enums import ChallengeCategory, Difficulty
from ctf_team_dashboard.domain.models import Challenge, Member, Solve, Team
from ctf_team_dashboard.repositories import Repositories


def _seed(repositories: Repositories) -> None:
    """Persist a small deterministic dataset."""
    now = datetime.now(timezone.utc)
    team = Team(id="team-analytics", name="Analytics Crew", slug="analytics-crew", created_at=now)
    repositories.teams.create(team)
    member = Member(
        id="member-analytics",
        team_id="team-analytics",
        handle="nyx",
        display_name="Nyx",
        joined_at=now,
    )
    repositories.members.create(member)
    second_member = Member(
        id="member-analytics-2",
        team_id="team-analytics",
        handle="kestrel",
        display_name="Kestrel",
        joined_at=now,
    )
    repositories.members.create(second_member)
    challenge = Challenge(
        id="challenge-analytics",
        team_id="team-analytics",
        title="Nonce Reuse",
        category=ChallengeCategory.CRYPTO,
        difficulty=Difficulty.HARD,
        created_at=now,
    )
    repositories.challenges.create(challenge)
    repositories.solves.create(
        Solve(
            id="solve-analytics-1",
            challenge_id="challenge-analytics",
            member_id="member-analytics",
            points_awarded=300,
            solved_at=now - timedelta(hours=2),
        )
    )
    repositories.solves.create(
        Solve(
            id="solve-analytics-2",
            challenge_id="challenge-analytics",
            member_id="member-analytics-2",
            points_awarded=300,
            solved_at=now - timedelta(hours=1),
        )
    )


def test_velocity_endpoint_returns_hourly_points(client: TestClient) -> None:
    """The velocity endpoint should return one point per hour."""
    response = client.get("/api/analytics/velocity", params={"hours": 12})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 12
    assert payload[0]["at"]
    assert isinstance(payload[0]["count"], int)


def test_velocity_endpoint_can_be_filtered(client: TestClient) -> None:
    """The velocity endpoint should honour the team filter."""
    response = client.get("/api/analytics/velocity", params={"team_id": "team-analytics"})
    assert response.status_code == 200
    assert len(response.json()) == 24


def test_intervals_endpoint(client: TestClient) -> None:
    """The intervals endpoint should describe the gaps between the solves."""
    response = client.get("/api/analytics/intervals")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 0
    assert payload["median_seconds"] >= 0


def test_difficulty_matrix_endpoint(client: TestClient) -> None:
    """The difficulty matrix should cover every tier and category."""
    response = client.get("/api/analytics/difficulty")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["difficulties"]) == 5
    assert len(payload["categories"]) == 7
    assert set(payload["totals"]) == set(payload["difficulties"])


def test_category_analytics_endpoint(client: TestClient) -> None:
    """The category analytics should return the labelled categories."""
    response = client.get("/api/analytics/categories")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    for entry in payload:
        assert {"category", "label", "accent", "challenges", "solves"} <= set(entry)


def test_leaderboard_endpoint(client: TestClient) -> None:
    """The leaderboard should be ordered by points."""
    response = client.get("/api/analytics/leaderboard")
    assert response.status_code == 200
    payload = response.json()
    points = [row["points"] for row in payload]
    assert points == sorted(points, reverse=True)


def test_heatmap_endpoint(client: TestClient) -> None:
    """The analytics heatmap should be a 7x24 matrix."""
    response = client.get("/api/analytics/heatmap")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 7
    assert all(len(row) == 24 for row in payload)


def test_summary_endpoint(client: TestClient) -> None:
    """The summary should expose the headline metrics."""
    response = client.get("/api/analytics/summary")
    assert response.status_code == 200
    payload = response.json()
    assert 0 <= payload["completion_rate"] <= 1
    assert payload["seconds_remaining"] >= 0


def test_analytics_reflect_the_persisted_data(
    client: TestClient, repositories: Repositories
) -> None:
    """The analytics should count the solves persisted in the database."""
    _seed(repositories)
    response = client.get(
        "/api/analytics/velocity",
        params={"hours": 24, "team_id": "team-analytics"},
    )
    assert response.status_code == 200
    assert sum(point["count"] for point in response.json()) == 2
