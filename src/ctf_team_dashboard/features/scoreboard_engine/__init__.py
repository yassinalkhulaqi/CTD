"""Scoreboard engine module for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.scoreboard_engine.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_score_rules (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    base_points INTEGER NOT NULL,
    difficulty_multiplier REAL NOT NULL,
    first_blood_bonus INTEGER NOT NULL,
    hint_penalty INTEGER NOT NULL,
    decay_factor REAL NOT NULL,
    decay_enabled INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS v3_score_snapshots (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    points INTEGER NOT NULL,
    solves INTEGER NOT NULL,
    rank INTEGER NOT NULL,
    details_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_v3_score_snapshots_team
    ON v3_score_snapshots(team_id, recorded_at DESC);
"""


def register(app: FastAPI) -> None:
    """Mount the scoreboard API router on the application."""
    app.include_router(router)
