"""CTF event lifecycle feature module for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.ctf_events.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_events (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    format TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    status TEXT NOT NULL,
    max_team_size INTEGER NOT NULL,
    registration_open INTEGER NOT NULL,
    website_url TEXT NOT NULL,
    tags TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_v3_events_window ON v3_events (starts_at, ends_at);
CREATE INDEX IF NOT EXISTS idx_v3_events_status ON v3_events (status);

CREATE TABLE IF NOT EXISTS v3_event_registrations (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    status TEXT NOT NULL,
    registered_at TEXT NOT NULL,
    promoted_at TEXT,
    FOREIGN KEY (event_id) REFERENCES v3_events (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_v3_registrations_event
    ON v3_event_registrations (event_id, status);
CREATE INDEX IF NOT EXISTS idx_v3_registrations_team
    ON v3_event_registrations (team_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_v3_registrations_unique
    ON v3_event_registrations (event_id, team_id)
    WHERE status IN ('confirmed', 'waitlisted');

CREATE TABLE IF NOT EXISTS v3_event_tasks (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    title TEXT NOT NULL,
    done INTEGER NOT NULL,
    due_at TEXT,
    FOREIGN KEY (event_id) REFERENCES v3_events (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_v3_tasks_event ON v3_event_tasks (event_id, done);
"""


def register(app: FastAPI) -> None:
    """Mount the event lifecycle API router."""
    app.include_router(router)
