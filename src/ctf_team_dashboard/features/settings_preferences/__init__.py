"""Settings and preferences module for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.settings_preferences.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_preferences (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, key)
);
CREATE INDEX IF NOT EXISTS idx_v3_preferences_user
    ON v3_preferences(user_id);

CREATE TABLE IF NOT EXISTS v3_theme_tokens (
    name TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS v3_layouts (
    user_id TEXT PRIMARY KEY,
    density TEXT NOT NULL,
    sidebar_position TEXT NOT NULL,
    show_activity INTEGER NOT NULL DEFAULT 1,
    timezone TEXT NOT NULL,
    date_format TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def register(app: FastAPI) -> None:
    """Mount the settings preferences API router."""
    app.include_router(router)
