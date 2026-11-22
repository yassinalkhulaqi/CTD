"""Onboarding tour module for the CTF Team Dashboard.

The package contributes the setup wizard catalogue, per-user progress, the
setup checklist and the guided tour API. It is discovered automatically by the
feature registry, so no shared module needs to be edited.
"""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.onboarding_tour.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_onboarding_steps (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    target TEXT NOT NULL,
    step_order INTEGER NOT NULL,
    completion_key TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    estimated_seconds INTEGER NOT NULL,
    required INTEGER NOT NULL,
    hint TEXT NOT NULL,
    icon TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS v3_onboarding_progress (
    user_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    skipped INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, step_id)
);

CREATE INDEX IF NOT EXISTS idx_v3_onboarding_progress_user
    ON v3_onboarding_progress(user_id);

CREATE TABLE IF NOT EXISTS v3_checklists (
    user_id TEXT PRIMARY KEY,
    items_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def register(app: FastAPI) -> None:
    """Mount the onboarding API router on the application."""
    app.include_router(router)
