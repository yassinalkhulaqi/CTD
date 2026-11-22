"""Notes workspace module for the CTF Team Dashboard.

The package exposes the schema owned by the feature and a ``register`` hook
used by the dynamic feature installer in the application factory.
"""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.notes_workspace.router import (
    router,
    template_router,
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_notes (
    id TEXT PRIMARY KEY,
    challenge_id TEXT NOT NULL,
    member_id TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    format TEXT NOT NULL DEFAULT 'markdown',
    tags TEXT NOT NULL DEFAULT '[]',
    pinned INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_v3_notes_challenge ON v3_notes(challenge_id);
CREATE INDEX IF NOT EXISTS idx_v3_notes_member ON v3_notes(member_id);
CREATE INDEX IF NOT EXISTS idx_v3_notes_updated ON v3_notes(updated_at);

CREATE TABLE IF NOT EXISTS v3_note_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    body TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_v3_note_templates_category
    ON v3_note_templates(category);

CREATE TABLE IF NOT EXISTS v3_note_revisions (
    id TEXT PRIMARY KEY,
    note_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    body TEXT NOT NULL,
    author_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(note_id, version)
);
CREATE INDEX IF NOT EXISTS idx_v3_note_revisions_note
    ON v3_note_revisions(note_id);
"""


def register(app: FastAPI) -> None:
    """Mount the notes workspace API routers on the application."""
    app.include_router(router)
    app.include_router(template_router)
