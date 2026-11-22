"""Webhook and integration module for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.integrations_webhooks.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_integrations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    endpoint_url TEXT NOT NULL,
    events_json TEXT NOT NULL,
    secret_hash TEXT NOT NULL DEFAULT '',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS v3_deliveries (
    id TEXT PRIMARY KEY,
    integration_id TEXT NOT NULL,
    event TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    response_code INTEGER,
    sent_at TEXT,
    FOREIGN KEY (integration_id) REFERENCES v3_integrations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS v3_adapters (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    event_map_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_v3_deliveries_integration
    ON v3_deliveries (integration_id);
CREATE INDEX IF NOT EXISTS idx_v3_deliveries_status
    ON v3_deliveries (status);
"""


def register(app: FastAPI) -> None:
    """Mount the integrations API router."""
    app.include_router(router)
