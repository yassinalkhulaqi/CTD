"""Team roster module for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.team_roster.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_roster_members (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    handle TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL,
    specialty TEXT NOT NULL DEFAULT '',
    timezone TEXT NOT NULL DEFAULT 'UTC',
    availability TEXT NOT NULL DEFAULT 'offline',
    capacity_hours REAL NOT NULL DEFAULT 8,
    joined_at TEXT NOT NULL,
    UNIQUE (team_id, handle)
);
CREATE INDEX IF NOT EXISTS idx_v3_roster_members_team
    ON v3_roster_members (team_id, role);
CREATE INDEX IF NOT EXISTS idx_v3_roster_members_availability
    ON v3_roster_members (availability);

CREATE TABLE IF NOT EXISTS v3_roster_invitations (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_v3_roster_invitations_team
    ON v3_roster_invitations (team_id, status);
CREATE INDEX IF NOT EXISTS idx_v3_roster_invitations_email
    ON v3_roster_invitations (team_id, email, status);
CREATE INDEX IF NOT EXISTS idx_v3_roster_invitations_expiry
    ON v3_roster_invitations (status, expires_at);

CREATE TABLE IF NOT EXISTS v3_roster_assignments (
    id TEXT PRIMARY KEY,
    member_id TEXT NOT NULL,
    challenge_id TEXT NOT NULL,
    hours REAL NOT NULL,
    assigned_at TEXT NOT NULL,
    UNIQUE (member_id, challenge_id)
);
CREATE INDEX IF NOT EXISTS idx_v3_roster_assignments_member
    ON v3_roster_assignments (member_id);
CREATE INDEX IF NOT EXISTS idx_v3_roster_assignments_challenge
    ON v3_roster_assignments (challenge_id);
"""


def register(app: FastAPI) -> None:
    """Mount the team roster API router."""
    app.include_router(router)
