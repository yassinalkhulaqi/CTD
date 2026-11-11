"""Tests for the single page application fallback."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ctf_team_dashboard.app import create_app
from ctf_team_dashboard.config import Settings


def _build_static_dir(tmp_path: Path) -> Path:
    """Create a minimal built frontend on disk."""
    static = tmp_path / "dist"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("<!doctype html><title>CTF</title>", encoding="utf-8")
    (static / "assets" / "index.js").write_text("console.log('app');", encoding="utf-8")
    return static


def test_spa_is_mounted_when_assets_exist(tmp_path: Path) -> None:
    """The built frontend should be served when it is available."""
    static = _build_static_dir(tmp_path)
    settings = Settings(
        database_path=tmp_path / "test.sqlite",
        static_dir=str(static),
        seed_on_startup=False,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/challenges")
        assert response.status_code == 200
        assert "CTF" in response.text

        assets = client.get("/assets/index.js")
        assert assets.status_code == 200


def test_api_routes_are_not_shadowed_by_the_spa(tmp_path: Path) -> None:
    """The API must keep answering even when the SPA is mounted."""
    static = _build_static_dir(tmp_path)
    settings = Settings(
        database_path=tmp_path / "test.sqlite",
        static_dir=str(static),
        seed_on_startup=False,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_spa_is_not_mounted_without_assets(tmp_path: Path) -> None:
    """No fallback route is registered when the assets are missing."""
    settings = Settings(
        database_path=tmp_path / "test.sqlite",
        static_dir=str(tmp_path / "missing"),
        seed_on_startup=False,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        assert client.get("/challenges").status_code == 404
