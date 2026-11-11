"""Tests for the aggregated dashboard endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_dashboard_snapshot_returns_every_section(client: TestClient) -> None:
    """The snapshot should expose the overview, leaderboard and categories."""
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload["overview"]["teams"] >= 1
    assert isinstance(payload["scoreboard"], list)
    assert isinstance(payload["categories"], list)
    assert isinstance(payload["contributions"], list)
    assert isinstance(payload["recent_events"], list)
    assert payload["competition_seconds_remaining"] >= 0
    assert payload["generated_at"]


def test_dashboard_snapshot_can_be_filtered(client: TestClient) -> None:
    """The snapshot should honour the optional team filter."""
    teams = client.get("/api/teams").json()
    response = client.get("/api/dashboard", params={"team_id": teams[0]["id"]})
    assert response.status_code == 200
    payload = response.json()
    assert all(row["team_id"] == teams[0]["id"] for row in payload["contributions"])


def test_dashboard_categories_endpoint(client: TestClient) -> None:
    """The categories endpoint should return labelled categories."""
    response = client.get("/api/dashboard/categories")
    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert {"category", "label", "accent", "challenges", "solves"} <= set(payload[0])


def test_dashboard_single_category_endpoint(client: TestClient) -> None:
    """A single category should be addressable by name."""
    response = client.get("/api/dashboard/categories/web")
    assert response.status_code == 200
    payload = response.json()
    assert payload["category"] == "web"
    assert payload["accent"].startswith("#")


def test_dashboard_unknown_category_returns_zeroes(client: TestClient) -> None:
    """An unknown category should return an empty breakdown."""
    response = client.get("/api/dashboard/categories/misc")
    assert response.status_code == 200
    assert response.json()["challenges"] >= 0
