"""Writeups library for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.writeups_library.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_writeups (
    id TEXT PRIMARY KEY,
    challenge_id TEXT NOT NULL,
    author_id TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    body TEXT NOT NULL,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'draft',
    rating_sum INTEGER NOT NULL DEFAULT 0,
    rating_count INTEGER NOT NULL DEFAULT 0,
    ratings_json TEXT NOT NULL DEFAULT '{}',
    views INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    published_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_v3_writeups_status ON v3_writeups(status);
CREATE INDEX IF NOT EXISTS idx_v3_writeups_category ON v3_writeups(category);
CREATE INDEX IF NOT EXISTS idx_v3_writeups_author ON v3_writeups(author_id);
CREATE INDEX IF NOT EXISTS idx_v3_writeups_challenge ON v3_writeups(challenge_id);

CREATE TABLE IF NOT EXISTS v3_writeup_reviews (
    id TEXT PRIMARY KEY,
    writeup_id TEXT NOT NULL,
    reviewer_id TEXT NOT NULL,
    verdict TEXT NOT NULL,
    comment TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(writeup_id, reviewer_id)
);
CREATE INDEX IF NOT EXISTS idx_v3_writeup_reviews_writeup ON v3_writeup_reviews(writeup_id);

CREATE TABLE IF NOT EXISTS v3_writeup_bookmarks (
    id TEXT PRIMARY KEY,
    writeup_id TEXT NOT NULL,
    member_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(writeup_id, member_id)
);
CREATE INDEX IF NOT EXISTS idx_v3_writeup_bookmarks_member ON v3_writeup_bookmarks(member_id);
"""


def register(app: FastAPI) -> None:
    """Mount the writeups API router."""
    app.include_router(router)
