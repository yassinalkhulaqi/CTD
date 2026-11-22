"""Flag submission pipeline module for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.submission_pipeline.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_submissions (
    id TEXT PRIMARY KEY,
    challenge_id TEXT NOT NULL,
    member_id TEXT NOT NULL,
    flag_cipher TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    error TEXT,
    flag_digest TEXT NOT NULL,
    next_attempt_at TEXT,
    accepted INTEGER NOT NULL DEFAULT 0,
    UNIQUE (challenge_id, flag_digest)
);

CREATE INDEX IF NOT EXISTS idx_v3_submissions_status
    ON v3_submissions (status);
CREATE INDEX IF NOT EXISTS idx_v3_submissions_challenge
    ON v3_submissions (challenge_id);
CREATE INDEX IF NOT EXISTS idx_v3_submissions_member
    ON v3_submissions (member_id);
CREATE INDEX IF NOT EXISTS idx_v3_submissions_due
    ON v3_submissions (status, next_attempt_at);

CREATE TABLE IF NOT EXISTS v3_validation_rules (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    pattern TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    enabled INTEGER NOT NULL DEFAULT 1,
    priority INTEGER NOT NULL DEFAULT 100,
    kind TEXT NOT NULL DEFAULT 'format'
);

CREATE INDEX IF NOT EXISTS idx_v3_validation_rules_priority
    ON v3_validation_rules (priority, id);
"""


def register(app: FastAPI) -> None:
    """Mount the submission pipeline API router."""
    app.include_router(router)
