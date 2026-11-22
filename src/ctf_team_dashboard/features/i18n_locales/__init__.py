"""Internationalisation module for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.i18n_locales.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_locales (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    direction TEXT NOT NULL,
    plural_rules TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS v3_messages (
    id TEXT PRIMARY KEY,
    locale TEXT NOT NULL,
    namespace TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (locale, namespace, key)
);

CREATE INDEX IF NOT EXISTS idx_v3_messages_lookup
    ON v3_messages (locale, namespace, key);

CREATE TABLE IF NOT EXISTS v3_format_rules (
    locale TEXT PRIMARY KEY,
    number_pattern TEXT NOT NULL,
    date_pattern TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def register(app: FastAPI) -> None:
    """Mount the i18n API router."""
    app.include_router(router)
