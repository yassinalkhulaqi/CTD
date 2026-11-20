"""Activity timeline module for the CTF Team Dashboard.

The package exposes the schema owned by the feature and a ``register`` hook
used by the dynamic feature installer in the application factory.
"""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.activity_timeline.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_timeline_events (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    actor_name TEXT NOT NULL,
    summary TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    importance TEXT NOT NULL DEFAULT 'normal',
    occurred_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_v3_timeline_team
    ON v3_timeline_events(team_id);
CREATE INDEX IF NOT EXISTS idx_v3_timeline_occurred
    ON v3_timeline_events(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_v3_timeline_kind
    ON v3_timeline_events(kind);
CREATE INDEX IF NOT EXISTS idx_v3_timeline_actor
    ON v3_timeline_events(actor_id);
CREATE INDEX IF NOT EXISTS idx_v3_timeline_importance
    ON v3_timeline_events(importance);
CREATE INDEX IF NOT EXISTS idx_v3_timeline_team_occurred
    ON v3_timeline_events(team_id, occurred_at DESC);
"""


def register(app: FastAPI) -> None:
    """Mount the activity timeline API router on the application."""
    app.include_router(router)
