"""Application factory for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.routers import challenges, health, stats, teams


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="CTF Team Dashboard", version="0.1.0")
    app.include_router(health.router)
    app.include_router(teams.router)
    app.include_router(challenges.router)
    app.include_router(stats.router)
    return app
