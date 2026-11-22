"""Offline mutation queue and synchronisation feature for the dashboard."""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.offline_sync.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_pending_mutations (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    entity TEXT NOT NULL,
    operation TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    base_version INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT NOT NULL DEFAULT '',
    resolved_version INTEGER
);

CREATE INDEX IF NOT EXISTS idx_v3_pending_client_status
    ON v3_pending_mutations(client_id, status);
CREATE INDEX IF NOT EXISTS idx_v3_pending_created
    ON v3_pending_mutations(created_at, id);
CREATE INDEX IF NOT EXISTS idx_v3_pending_entity
    ON v3_pending_mutations(entity);

CREATE TABLE IF NOT EXISTS v3_sync_snapshots (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    synced_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 0,
    mutation_count INTEGER NOT NULL DEFAULT 0,
    conflict_count INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_v3_snapshot_client_time
    ON v3_sync_snapshots(client_id, synced_at);

CREATE TABLE IF NOT EXISTS v3_conflict_resolutions (
    id TEXT PRIMARY KEY,
    mutation_id TEXT NOT NULL,
    strategy TEXT NOT NULL,
    resolved_at TEXT NOT NULL,
    local_version INTEGER NOT NULL DEFAULT 0,
    remote_version INTEGER NOT NULL DEFAULT 0,
    field_changes_json TEXT NOT NULL DEFAULT '[]',
    notes TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_v3_resolution_mutation
    ON v3_conflict_resolutions(mutation_id);
CREATE INDEX IF NOT EXISTS idx_v3_resolution_time
    ON v3_conflict_resolutions(resolved_at);
"""


def register(app: FastAPI) -> None:
    """Mount the offline synchronisation API router."""
    app.include_router(router)
