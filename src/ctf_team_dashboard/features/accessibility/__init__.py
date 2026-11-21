"""Accessibility module for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.accessibility.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_a11y_issues (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    description TEXT NOT NULL,
    suggestion TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_v3_a11y_issues_path ON v3_a11y_issues(path);
CREATE INDEX IF NOT EXISTS idx_v3_a11y_issues_severity ON v3_a11y_issues(severity);
CREATE INDEX IF NOT EXISTS idx_v3_a11y_issues_resolved ON v3_a11y_issues(resolved_at);

CREATE TABLE IF NOT EXISTS v3_shortcuts (
    id TEXT PRIMARY KEY,
    keys TEXT NOT NULL,
    action TEXT NOT NULL,
    scope TEXT NOT NULL,
    UNIQUE (keys, scope)
);
CREATE INDEX IF NOT EXISTS idx_v3_shortcuts_scope ON v3_shortcuts(scope);

CREATE TABLE IF NOT EXISTS v3_focus_orders (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_v3_focus_orders_position ON v3_focus_orders(sort_order);
"""


def register(app: FastAPI) -> None:
    """Mount the accessibility API router."""
    app.include_router(router)
