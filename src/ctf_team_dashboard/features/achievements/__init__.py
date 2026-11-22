"""Achievement module for the CTF Team Dashboard.

The module owns three tables: badge definitions, member awards and the rolling
progress records used by the gallery. Discovery and migration are handled by
the platform kernel, so this package only exports its schema and an installer.
"""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.achievements.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_badges (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    tier TEXT NOT NULL,
    criteria_kind TEXT NOT NULL,
    criteria_value INTEGER NOT NULL CHECK (criteria_value > 0),
    icon TEXT NOT NULL DEFAULT 'trophy',
    points INTEGER NOT NULL DEFAULT 0,
    secret INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_v3_badges_tier
    ON v3_badges(tier, criteria_kind);

CREATE TABLE IF NOT EXISTS v3_awards (
    id TEXT PRIMARY KEY,
    badge_id TEXT NOT NULL REFERENCES v3_badges(id) ON DELETE CASCADE,
    member_id TEXT NOT NULL,
    awarded_at TEXT NOT NULL,
    evidence TEXT NOT NULL DEFAULT '{}'
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_v3_awards_member_badge
    ON v3_awards(member_id, badge_id);

CREATE INDEX IF NOT EXISTS idx_v3_awards_badge
    ON v3_awards(badge_id);

CREATE INDEX IF NOT EXISTS idx_v3_awards_member
    ON v3_awards(member_id, awarded_at);

CREATE TABLE IF NOT EXISTS v3_progress (
    member_id TEXT NOT NULL,
    badge_id TEXT NOT NULL REFERENCES v3_badges(id) ON DELETE CASCADE,
    current INTEGER NOT NULL DEFAULT 0,
    target INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (member_id, badge_id)
);

CREATE INDEX IF NOT EXISTS idx_v3_progress_badge
    ON v3_progress(badge_id, current);
"""


def register(app: FastAPI) -> None:
    """Mount the achievement API router on the application."""
    app.include_router(router)
