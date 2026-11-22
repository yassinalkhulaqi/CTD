"""Tiered hint engine module for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.hint_engine.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_hints (
    id TEXT PRIMARY KEY,
    challenge_id TEXT NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    tier INTEGER NOT NULL CHECK (tier BETWEEN 1 AND 3),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    cost INTEGER NOT NULL CHECK (cost > 0),
    base_cost INTEGER NOT NULL CHECK (base_cost > 0),
    multiplier REAL NOT NULL CHECK (multiplier >= 1),
    reveal_after_seconds INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (challenge_id, tier)
);

CREATE INDEX IF NOT EXISTS v3_hints_challenge_idx ON v3_hints(challenge_id);

CREATE TABLE IF NOT EXISTS v3_hint_unlocks (
    id TEXT PRIMARY KEY,
    hint_id TEXT NOT NULL REFERENCES v3_hints(id) ON DELETE CASCADE,
    member_id TEXT NOT NULL REFERENCES members(id),
    team_id TEXT NOT NULL REFERENCES teams(id),
    cost_paid INTEGER NOT NULL CHECK (cost_paid >= 0),
    unlocked_at TEXT NOT NULL,
    UNIQUE (hint_id, team_id)
);

CREATE INDEX IF NOT EXISTS v3_hint_unlocks_team_idx ON v3_hint_unlocks(team_id);

CREATE TABLE IF NOT EXISTS v3_hint_budgets (
    team_id TEXT PRIMARY KEY REFERENCES teams(id) ON DELETE CASCADE,
    total INTEGER NOT NULL CHECK (total > 0),
    spent INTEGER NOT NULL DEFAULT 0 CHECK (spent >= 0),
    reset_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def register(app: FastAPI) -> None:
    """Mount the hint engine API router."""
    app.include_router(router)
