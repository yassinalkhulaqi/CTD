"""Notification centre module for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.notifications.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS v3_notifications (
    id TEXT PRIMARY KEY,
    recipient_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    severity TEXT NOT NULL,
    read_at TEXT,
    created_at TEXT NOT NULL,
    action_url TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_v3_notifications_recipient
    ON v3_notifications (recipient_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_v3_notifications_unread
    ON v3_notifications (recipient_id, read_at);

CREATE TABLE IF NOT EXISTS v3_notification_preferences (
    recipient_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    kind TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    quiet_start_hour INTEGER NOT NULL DEFAULT 0,
    quiet_end_hour INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (recipient_id, channel, kind)
);

CREATE INDEX IF NOT EXISTS idx_v3_notification_preferences_recipient
    ON v3_notification_preferences (recipient_id);

CREATE TABLE IF NOT EXISTS v3_digests (
    id TEXT PRIMARY KEY,
    recipient_id TEXT NOT NULL,
    period TEXT NOT NULL,
    entries_json TEXT NOT NULL DEFAULT '[]',
    sent_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_v3_digests_recipient
    ON v3_digests (recipient_id, period);
"""


def register(app: FastAPI) -> None:
    """Mount the notification API router."""
    app.include_router(router)
