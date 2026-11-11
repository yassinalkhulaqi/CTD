-- Schema for the CTF Team Dashboard (SQLite dialect).

CREATE TABLE IF NOT EXISTS teams (
    id          TEXT PRIMARY KEY,
    name        TEXT    NOT NULL,
    slug        TEXT    NOT NULL UNIQUE,
    color       TEXT    NOT NULL DEFAULT '#6366f1',
    description TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS members (
    id           TEXT PRIMARY KEY,
    team_id      TEXT    NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    handle       TEXT    NOT NULL,
    display_name TEXT    NOT NULL,
    role         TEXT    NOT NULL DEFAULT 'analyst',
    presence     TEXT    NOT NULL DEFAULT 'offline',
    joined_at    TEXT    NOT NULL,
    UNIQUE (team_id, handle)
);

CREATE TABLE IF NOT EXISTS challenges (
    id          TEXT PRIMARY KEY,
    team_id     TEXT    NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    title       TEXT    NOT NULL,
    category    TEXT    NOT NULL,
    difficulty  TEXT    NOT NULL,
    points      INTEGER NOT NULL DEFAULT 100,
    description TEXT    NOT NULL DEFAULT '',
    status      TEXT    NOT NULL DEFAULT 'pending',
    tags        TEXT    NOT NULL DEFAULT '[]',
    starts_at   TEXT,
    ends_at     TEXT,
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS solves (
    id             TEXT PRIMARY KEY,
    challenge_id   TEXT    NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    member_id      TEXT    NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    flag           TEXT    NOT NULL DEFAULT '',
    points_awarded INTEGER NOT NULL DEFAULT 0,
    solved_at      TEXT    NOT NULL,
    UNIQUE (challenge_id, member_id)
);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id     TEXT REFERENCES teams(id) ON DELETE CASCADE,
    kind        TEXT    NOT NULL,
    payload     TEXT    NOT NULL DEFAULT '{}',
    occurred_at TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_members_team ON members(team_id);
CREATE INDEX IF NOT EXISTS idx_challenges_team ON challenges(team_id);
CREATE INDEX IF NOT EXISTS idx_challenges_category ON challenges(category);
CREATE INDEX IF NOT EXISTS idx_challenges_status ON challenges(status);
CREATE INDEX IF NOT EXISTS idx_solves_challenge ON solves(challenge_id);
CREATE INDEX IF NOT EXISTS idx_solves_member ON solves(member_id);
CREATE INDEX IF NOT EXISTS idx_solves_solved_at ON solves(solved_at);
CREATE INDEX IF NOT EXISTS idx_events_team ON events(team_id);
CREATE INDEX IF NOT EXISTS idx_events_occurred_at ON events(occurred_at);

CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    username      TEXT    NOT NULL UNIQUE,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'viewer',
    team_id       TEXT    REFERENCES teams(id) ON DELETE SET NULL,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS notes (
    id           TEXT PRIMARY KEY,
    challenge_id TEXT    NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    member_id    TEXT    NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    body         TEXT    NOT NULL,
    created_at   TEXT    NOT NULL,
    updated_at   TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_notes_challenge ON notes(challenge_id);
CREATE INDEX IF NOT EXISTS idx_notes_member ON notes(member_id);
CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at);

CREATE TABLE IF NOT EXISTS api_keys (
    id           TEXT PRIMARY KEY,
    user_id      TEXT    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name         TEXT    NOT NULL,
    prefix       TEXT    NOT NULL UNIQUE,
    secret_hash  TEXT    NOT NULL,
    scopes       TEXT    NOT NULL DEFAULT '[]',
    created_at   TEXT    NOT NULL,
    last_used_at TEXT,
    revoked_at   TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id             TEXT PRIMARY KEY,
    user_id        TEXT    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_hash   TEXT    NOT NULL,
    created_at     TEXT    NOT NULL,
    expires_at     TEXT    NOT NULL,
    revoked_at     TEXT,
    user_agent     TEXT    NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(prefix);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
