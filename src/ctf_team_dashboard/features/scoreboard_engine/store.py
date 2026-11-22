"""SQLite persistence for scoring rules and ranking snapshots."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any
from uuid import uuid4

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    format_datetime,
    parse_datetime,
    row_to_dict,
)

from .models import ScoreRule, ScoreSnapshot

_RULE_COLUMNS = (
    "id",
    "team_id",
    "name",
    "base_points",
    "difficulty_multiplier",
    "first_blood_bonus",
    "hint_penalty",
    "decay_factor",
    "decay_enabled",
    "updated_at",
)


class ScoreStore(BaseRepository):
    """Repository for the tables owned by the scoreboard engine."""

    table = "v3_score_rules"

    @staticmethod
    def row_to_rule(row: sqlite3.Row) -> ScoreRule:
        """Map a rule row onto its domain model."""
        data = row_to_dict(row)
        updated_at = parse_datetime(str(data["updated_at"]))
        return ScoreRule(
            id=str(data["id"]),
            team_id=str(data["team_id"]),
            name=str(data["name"]),
            base_points=int(data["base_points"]),
            difficulty_multiplier=float(data["difficulty_multiplier"]),
            first_blood_bonus=int(data["first_blood_bonus"]),
            hint_penalty=int(data["hint_penalty"]),
            decay_factor=float(data["decay_factor"]),
            decay_enabled=bool(data["decay_enabled"]),
            updated_at=updated_at if updated_at is not None else utcnow(),
        )

    @staticmethod
    def row_to_snapshot(row: sqlite3.Row) -> ScoreSnapshot:
        """Map a snapshot row onto its domain model."""
        data = row_to_dict(row)
        recorded_at = parse_datetime(str(data["recorded_at"]))
        return ScoreSnapshot(
            id=str(data["id"]),
            team_id=str(data["team_id"]),
            recorded_at=recorded_at if recorded_at is not None else utcnow(),
            points=int(data["points"]),
            solves=int(data["solves"]),
            rank=int(data["rank"]),
            details_json=str(data["details_json"]),
        )

    def get_rule(self, team_id: str) -> ScoreRule | None:
        """Return the scoring rule configured for one team."""
        row = self.fetch_one("SELECT * FROM v3_score_rules WHERE team_id = ?", (team_id,))
        return self.row_to_rule(row) if row is not None else None

    def upsert_rule(self, rule: ScoreRule) -> ScoreRule:
        """Insert or update the rule for a team, preserving its row identity."""
        self.execute(
            """
            INSERT INTO v3_score_rules
                (id, team_id, name, base_points, difficulty_multiplier,
                 first_blood_bonus, hint_penalty, decay_factor, decay_enabled,
                 updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(team_id) DO UPDATE SET
                name = excluded.name,
                base_points = excluded.base_points,
                difficulty_multiplier = excluded.difficulty_multiplier,
                first_blood_bonus = excluded.first_blood_bonus,
                hint_penalty = excluded.hint_penalty,
                decay_factor = excluded.decay_factor,
                decay_enabled = excluded.decay_enabled,
                updated_at = excluded.updated_at
            """,
            (
                rule.id,
                rule.team_id,
                rule.name,
                rule.base_points,
                rule.difficulty_multiplier,
                rule.first_blood_bonus,
                rule.hint_penalty,
                rule.decay_factor,
                int(rule.decay_enabled),
                format_datetime(rule.updated_at),
            ),
        )
        stored = self.get_rule(rule.team_id)
        if stored is None:
            raise RuntimeError("score rule disappeared after upsert")
        return stored

    def list_rules(self) -> list[ScoreRule]:
        """Return every configured rule ordered by team identifier."""
        rows = self.fetch_all("SELECT * FROM v3_score_rules ORDER BY team_id ASC")
        return [self.row_to_rule(row) for row in rows]

    def insert_snapshot(
        self,
        team_id: str,
        points: int,
        solves: int,
        rank: int,
        details: dict[str, Any] | None = None,
        *,
        recorded_at: datetime | None = None,
    ) -> ScoreSnapshot:
        """Persist a new snapshot for a team and return the stored record."""
        snapshot = ScoreSnapshot(
            id=f"snap-{uuid4().hex[:12]}",
            team_id=team_id,
            recorded_at=utcnow() if recorded_at is None else recorded_at,
            points=points,
            solves=solves,
            rank=rank,
            details_json=json.dumps(details or {}, separators=(",", ":"), default=str),
        )
        self.execute(
            """
            INSERT INTO v3_score_snapshots
                (id, team_id, recorded_at, points, solves, rank, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.id,
                snapshot.team_id,
                format_datetime(snapshot.recorded_at),
                snapshot.points,
                snapshot.solves,
                snapshot.rank,
                snapshot.details_json,
            ),
        )
        return snapshot

    def list_snapshots(self, team_id: str, limit: int = 50) -> list[ScoreSnapshot]:
        """Return a team's snapshots, newest first."""
        rows = self.fetch_all(
            """
            SELECT * FROM v3_score_snapshots
             WHERE team_id = ?
             ORDER BY recorded_at DESC, id DESC
             LIMIT ?
            """,
            (team_id, max(1, min(limit, 500))),
        )
        return [self.row_to_snapshot(row) for row in rows]

    def latest_snapshot(self, team_id: str) -> ScoreSnapshot | None:
        """Return the most recent snapshot recorded for a team."""
        rows = self.fetch_all(
            """
            SELECT * FROM v3_score_snapshots
             WHERE team_id = ?
             ORDER BY recorded_at DESC, id DESC
             LIMIT 1
            """,
            (team_id,),
        )
        return self.row_to_snapshot(rows[0]) if rows else None

    def latest_snapshots(self) -> dict[str, ScoreSnapshot]:
        """Return the most recent snapshot of every team."""
        rows = self.fetch_all(
            """
            SELECT s.* FROM v3_score_snapshots AS s
             JOIN (
                 SELECT team_id, MAX(recorded_at) AS recorded_at
                   FROM v3_score_snapshots
                  GROUP BY team_id
             ) AS latest
               ON latest.team_id = s.team_id
              AND latest.recorded_at = s.recorded_at
            """
        )
        result: dict[str, ScoreSnapshot] = {}
        for row in rows:
            snapshot = self.row_to_snapshot(row)
            current = result.get(snapshot.team_id)
            if current is None or snapshot.recorded_at > current.recorded_at:
                result[snapshot.team_id] = snapshot
        return result

    def latest_ranks(self) -> dict[str, int]:
        """Return the last known rank of each team that has a snapshot."""
        return {team_id: snapshot.rank for team_id, snapshot in self.latest_snapshots().items()}

    def snapshot_count(self, team_id: str) -> int:
        """Return the number of snapshots recorded for one team."""
        value = self.fetch_value(
            "SELECT COUNT(*) FROM v3_score_snapshots WHERE team_id = ?", (team_id,), 0
        )
        return int(value or 0)
