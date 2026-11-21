"""Administration console module for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.admin_console.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_moderation_cases (
    id TEXT PRIMARY KEY,
    report_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    reporter_id TEXT NOT NULL,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    assignee_id TEXT,
    resolution TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_v3_cases_status
    ON v3_moderation_cases (status, created_at);
CREATE INDEX IF NOT EXISTS idx_v3_cases_priority
    ON v3_moderation_cases (priority, created_at);

CREATE TABLE IF NOT EXISTS v3_admin_actions (
    id TEXT PRIMARY KEY,
    actor_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_v3_actions_created
    ON v3_admin_actions (created_at);
CREATE INDEX IF NOT EXISTS idx_v3_actions_target
    ON v3_admin_actions (target_type, target_id);

CREATE TABLE IF NOT EXISTS v3_account_controls (
    user_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    flags TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_v3_controls_status
    ON v3_account_controls (status);

CREATE TABLE IF NOT EXISTS v3_health_checks (
    id TEXT PRIMARY KEY,
    checked_at TEXT NOT NULL,
    database_ok INTEGER NOT NULL,
    api_latency_ms REAL NOT NULL,
    cache_hit_ratio REAL NOT NULL,
    queue_depth INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_v3_health_checked
    ON v3_health_checks (checked_at);
"""


def register(app: FastAPI) -> None:
    """Mount the administration console API router."""
    app.include_router(router)
