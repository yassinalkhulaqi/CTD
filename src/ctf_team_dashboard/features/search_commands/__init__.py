"""Search module for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.search_commands.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_search_documents (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]',
    path TEXT NOT NULL DEFAULT '/',
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_v3_search_documents_kind
    ON v3_search_documents(kind);
CREATE TABLE IF NOT EXISTS v3_commands (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    command_group TEXT NOT NULL DEFAULT 'General',
    shortcut TEXT NOT NULL DEFAULT '',
    keywords TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_v3_commands_group
    ON v3_commands(command_group);
"""


def register(app: FastAPI) -> None:
    """Mount the search API router."""
    app.include_router(router)
