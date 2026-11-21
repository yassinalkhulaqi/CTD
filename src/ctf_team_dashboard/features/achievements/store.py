"""SQLite persistence for badges, awards and achievement progress.

All statements are parameterised. The repositories are intentionally small and
composable: :class:`AchievementStore` is the only object the service layer needs
to know about.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.features.achievements.models import (
    AchievementAward,
    AchievementProgress,
    Badge,
    BadgeTier,
    CriteriaKind,
    LeaderboardRow,
    deterministic_award_id,
)
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    format_datetime,
    parse_datetime,
    parse_payload,
    row_to_dict,
)


class BadgeRepository(BaseRepository):
    """Persistence operations for badge definitions."""

    table = "v3_badges"

    @staticmethod
    def to_model(row: sqlite3.Row) -> Badge:
        """Map a database row onto a :class:`Badge`."""
        data = row_to_dict(row)
        return Badge(
            id=str(data["id"]),
            name=str(data["name"]),
            description=str(data["description"] or ""),
            tier=BadgeTier.parse(str(data["tier"]), BadgeTier.BRONZE),
            criteria_kind=CriteriaKind.parse(str(data["criteria_kind"]), CriteriaKind.SOLVES),
            criteria_value=max(1, int(data["criteria_value"])),
            icon=str(data["icon"] or "trophy"),
            points=max(0, int(data["points"] or 0)),
            secret=bool(int(data["secret"] or 0)),
        )

    def create(self, badge: Badge) -> Badge:
        """Insert a badge definition."""
        self.execute(
            """
            INSERT INTO v3_badges
                (id, name, description, tier, criteria_kind, criteria_value,
                 icon, points, secret)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                badge.id,
                badge.name,
                badge.description,
                badge.tier.value,
                badge.criteria_kind.value,
                badge.criteria_value,
                badge.icon,
                badge.points,
                int(badge.secret),
            ),
        )
        return badge

    def seed(self, badges: Sequence[Badge]) -> int:
        """Insert missing badges without overwriting existing definitions."""
        return int(
            self.execute_many(
                """
                INSERT OR IGNORE INTO v3_badges
                    (id, name, description, tier, criteria_kind, criteria_value,
                     icon, points, secret)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        badge.id,
                        badge.name,
                        badge.description,
                        badge.tier.value,
                        badge.criteria_kind.value,
                        badge.criteria_value,
                        badge.icon,
                        badge.points,
                        int(badge.secret),
                    )
                    for badge in badges
                ],
            )
        )

    def get(self, badge_id: str) -> Badge | None:
        """Return a badge by identifier, when it exists."""
        row = self.fetch_one("SELECT * FROM v3_badges WHERE id = ?", (badge_id,))
        return self.to_model(row) if row is not None else None

    def list_all(
        self,
        *,
        tier: BadgeTier | None = None,
        kind: CriteriaKind | None = None,
        include_secret: bool = True,
        limit: int | None = None,
    ) -> list[Badge]:
        """Return badges matching the requested filters."""
        clauses: list[str] = []
        params: list[Any] = []
        if tier is not None:
            clauses.append("tier = ?")
            params.append(tier.value)
        if kind is not None:
            clauses.append("criteria_kind = ?")
            params.append(kind.value)
        if not include_secret:
            clauses.append("secret = 0")
        sql = "SELECT * FROM v3_badges"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY tier, criteria_value, name"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(max(0, limit))
        return [self.to_model(row) for row in self.fetch_all(sql, params)]

    def count(self, where: str = "", params: Sequence[Any] = ()) -> int:
        """Return the number of badge rows, optionally filtered."""
        return int(super().count(where, params))

    def delete(self, badge_id: str) -> bool:
        """Delete a badge and cascade its awards and progress records."""
        return self.execute("DELETE FROM v3_badges WHERE id = ?", (badge_id,)) > 0


class AwardRepository(BaseRepository):
    """Persistence operations for award records."""

    table = "v3_awards"

    @staticmethod
    def to_model(row: sqlite3.Row) -> AchievementAward:
        """Map a database row onto an :class:`AchievementAward`."""
        data = row_to_dict(row)
        awarded_at = parse_datetime(str(data["awarded_at"]))
        return AchievementAward(
            id=str(data["id"]),
            badge_id=str(data["badge_id"]),
            member_id=str(data["member_id"]),
            awarded_at=awarded_at if awarded_at is not None else utcnow(),
            evidence=parse_payload(str(data["evidence"] or "{}")),
        )

    @staticmethod
    def new_id(badge_id: str, member_id: str) -> str:
        """Return the stable identifier for an award of badge to member."""
        return deterministic_award_id(badge_id, member_id)

    def award_once(
        self,
        badge_id: str,
        member_id: str,
        evidence: Mapping[str, Any] | None = None,
        *,
        awarded_at: datetime | None = None,
    ) -> AchievementAward | None:
        """Insert an award if it does not exist yet.

        Returns the persisted award on success and ``None`` when the member
        already owns the badge. The unique index makes repeated concurrent
        calls safe.
        """
        award_id = self.new_id(badge_id, member_id)
        timestamp = format_datetime(awarded_at) if awarded_at else format_datetime(utcnow())
        changed = self.execute(
            """
            INSERT OR IGNORE INTO v3_awards
                (id, badge_id, member_id, awarded_at, evidence)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                award_id,
                badge_id,
                member_id,
                timestamp,
                json.dumps(dict(evidence or {}), sort_keys=True, separators=(",", ":")),
            ),
        )
        if changed == 0:
            return None
        return self.get(award_id)

    def get(self, award_id: str) -> AchievementAward | None:
        """Return an award by identifier."""
        row = self.fetch_one("SELECT * FROM v3_awards WHERE id = ?", (award_id,))
        return self.to_model(row) if row is not None else None

    def find(self, badge_id: str, member_id: str) -> AchievementAward | None:
        """Return the award linking a member and badge, when present."""
        row = self.fetch_one(
            "SELECT * FROM v3_awards WHERE badge_id = ? AND member_id = ?",
            (badge_id, member_id),
        )
        return self.to_model(row) if row is not None else None

    def list_for_member(self, member_id: str) -> list[AchievementAward]:
        """Return every award owned by one member, newest first."""
        rows = self.fetch_all(
            "SELECT * FROM v3_awards WHERE member_id = ? ORDER BY awarded_at DESC",
            (member_id,),
        )
        return [self.to_model(row) for row in rows]

    def list_all(self, limit: int | None = None) -> list[AchievementAward]:
        """Return all awards, optionally capped to the newest records."""
        sql = "SELECT * FROM v3_awards ORDER BY awarded_at DESC"
        params: list[Any] = []
        if limit is not None:
            sql += " LIMIT ?"
            params.append(max(0, limit))
        return [self.to_model(row) for row in self.fetch_all(sql, params)]

    def count_for_badge(self, badge_id: str) -> int:
        """Return the number of members who own a badge."""
        return int(
            self.fetch_value("SELECT COUNT(*) FROM v3_awards WHERE badge_id = ?", (badge_id,), 0)
            or 0
        )

    def count_all(self) -> int:
        """Return the total number of awards."""
        return int(self.fetch_value("SELECT COUNT(*) FROM v3_awards", (), 0) or 0)

    def distinct_members(self) -> int:
        """Return the number of distinct members with at least one award."""
        return int(self.fetch_value("SELECT COUNT(DISTINCT member_id) FROM v3_awards", (), 0) or 0)

    def total_points(self) -> int:
        """Return the sum of tier-adjusted points across all awards."""
        value = self.fetch_value(
            """
            SELECT COALESCE(SUM(b.points * CASE b.tier
                WHEN 'bronze' THEN 1.0 WHEN 'silver' THEN 1.5 ELSE 2.25 END), 0)
              FROM v3_awards a
              JOIN v3_badges b ON b.id = a.badge_id
            """,
            (),
            0,
        )
        return int(float(value or 0))

    def holders_by_badge(self) -> dict[str, int]:
        """Return a mapping from badge identifier to holder count."""
        rows = self.fetch_all(
            "SELECT badge_id, COUNT(*) AS holders FROM v3_awards GROUP BY badge_id"
        )
        return {str(row["badge_id"]): int(row["holders"]) for row in rows}

    def leaderboard(self) -> list[LeaderboardRow]:
        """Return raw leaderboard rows joined against the member table."""
        rows = self.fetch_all(
            """
            SELECT a.member_id,
                   COALESCE(m.handle, a.member_id) AS handle,
                   COALESCE(m.display_name, '') AS display_name,
                   COUNT(*) AS awards,
                   COALESCE(SUM(b.points * CASE b.tier
                       WHEN 'bronze' THEN 1.0 WHEN 'silver' THEN 1.5 ELSE 2.25 END), 0)
                       AS points
              FROM v3_awards a
              JOIN v3_badges b ON b.id = a.badge_id
              LEFT JOIN members m ON m.id = a.member_id
             GROUP BY a.member_id, handle, display_name
            """
        )
        return [
            LeaderboardRow(
                member_id=str(row["member_id"]),
                handle=str(row["handle"]),
                display_name=str(row["display_name"] or ""),
                awards=int(row["awards"]),
                points=int(float(row["points"])),
            )
            for row in rows
        ]


class ProgressRepository(BaseRepository):
    """Persistence operations for member progress records."""

    table = "v3_progress"

    @staticmethod
    def to_model(row: sqlite3.Row) -> AchievementProgress:
        """Map a database row onto an :class:`AchievementProgress`."""
        data = row_to_dict(row)
        return AchievementProgress(
            member_id=str(data["member_id"]),
            badge_id=str(data["badge_id"]),
            current=max(0, int(data["current"])),
            target=max(1, int(data["target"])),
        )

    def upsert(self, progress: AchievementProgress) -> AchievementProgress:
        """Insert or update one progress record."""
        self.execute(
            """
            INSERT INTO v3_progress (member_id, badge_id, current, target, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(member_id, badge_id) DO UPDATE SET
                current = excluded.current,
                target = excluded.target,
                updated_at = excluded.updated_at
            """,
            (
                progress.member_id,
                progress.badge_id,
                progress.current,
                progress.target,
                format_datetime(utcnow()),
            ),
        )
        return progress

    def upsert_many(self, records: Sequence[AchievementProgress]) -> int:
        """Insert or update a batch of progress records."""
        return int(
            self.execute_many(
                """
                INSERT INTO v3_progress (member_id, badge_id, current, target, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(member_id, badge_id) DO UPDATE SET
                    current = excluded.current,
                    target = excluded.target,
                    updated_at = excluded.updated_at
                """,
                [
                    (
                        record.member_id,
                        record.badge_id,
                        record.current,
                        record.target,
                        format_datetime(utcnow()),
                    )
                    for record in records
                ],
            )
        )

    def get(self, member_id: str, badge_id: str) -> AchievementProgress | None:
        """Return one member's progress for one badge."""
        row = self.fetch_one(
            "SELECT * FROM v3_progress WHERE member_id = ? AND badge_id = ?",
            (member_id, badge_id),
        )
        return self.to_model(row) if row is not None else None

    def list_for_member(self, member_id: str) -> list[AchievementProgress]:
        """Return every progress record belonging to a member."""
        rows = self.fetch_all(
            "SELECT * FROM v3_progress WHERE member_id = ? ORDER BY badge_id",
            (member_id,),
        )
        return [self.to_model(row) for row in rows]

    def clear_member(self, member_id: str) -> int:
        """Remove all progress records for a member."""
        return self.execute("DELETE FROM v3_progress WHERE member_id = ?", (member_id,))


class AchievementStore:
    """Cohesive gateway over the three achievement tables."""

    def __init__(self) -> None:
        self.badges = BadgeRepository()
        self.awards = AwardRepository()
        self.progress = ProgressRepository()

    def badge_ids(self) -> set[str]:
        """Return every badge identifier currently stored."""
        return {badge.id for badge in self.badges.list_all()}
