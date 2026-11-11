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
