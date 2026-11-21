"""Report studio and exports module for the CTF Team Dashboard.

The feature owns three tables and mounts the ``/api/reports`` router. Both the
schema and the router are discovered automatically by the platform kernel.
"""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.reports_exports.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_report_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    sections_json TEXT NOT NULL,
    format TEXT NOT NULL,
    scope TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS v3_reports (
    id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL REFERENCES v3_report_templates(id),
    title TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    data_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS v3_exports (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL REFERENCES v3_reports(id),
    format TEXT NOT NULL,
    status TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_v3_reports_status ON v3_reports(status);
CREATE INDEX IF NOT EXISTS idx_v3_reports_template ON v3_reports(template_id);
CREATE INDEX IF NOT EXISTS idx_v3_exports_report ON v3_exports(report_id);
CREATE INDEX IF NOT EXISTS idx_v3_exports_format ON v3_exports(format);
"""


def register(app: FastAPI) -> None:
    """Mount the report studio API router."""
    app.include_router(router)
