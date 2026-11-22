"""Advanced data visualisation module for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.data_visualization.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_charts (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    title TEXT NOT NULL,
    chart_type TEXT NOT NULL,
    series_json TEXT NOT NULL,
    options_json TEXT NOT NULL,
    palette TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_v3_charts_team_updated
    ON v3_charts(team_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_v3_charts_type ON v3_charts(chart_type);

CREATE TABLE IF NOT EXISTS v3_chart_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chart_id TEXT NOT NULL REFERENCES v3_charts(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    value REAL NOT NULL,
    category TEXT NOT NULL,
    position INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_v3_chart_data_chart
    ON v3_chart_data(chart_id, position, id);
"""


def register(app: FastAPI) -> None:
    """Mount the visualisation API router."""
    app.include_router(router)
