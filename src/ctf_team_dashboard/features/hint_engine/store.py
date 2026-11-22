"""SQLite persistence for the hint engine.

Three repositories own the hint catalogue, the reveal ledger and the team
budgets. :class:`HintStore` groups them and exposes the single atomic unlock
transaction so the service layer never has to coordinate two writes by hand.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from typing import Any

from ctf_team_dashboard.db.engine import Database, get_database
from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.errors import ConflictError, ValidationError
from ctf_team_dashboard.features.hint_engine.models import (
    Hint,
    HintBudget,
    HintUnlock,
    LedgerEntry,
    TierSpend,
)
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    format_datetime,
    parse_datetime,
    row_to_dict,
)

HINT_COLUMNS = (
    "id, challenge_id, tier, title, content, cost, base_cost, multiplier, "
    "reveal_after_seconds, is_active, created_at, updated_at"
)
UNLOCK_COLUMNS = "id, hint_id, member_id, team_id, cost_paid, unlocked_at"


def _timestamp(value: object, fallback: Any = None) -> Any:
    """Parse a stored ISO timestamp, falling back to ``fallback``."""
    parsed = parse_datetime(str(value) if value is not None else None)
    return parsed if parsed is not None else (fallback or utcnow())


class HintRepository(BaseRepository):
    """Persistence operations for the hint catalogue."""

    table = "v3_hints"

    @staticmethod
    def to_model(row: sqlite3.Row) -> Hint:
        """Map a catalogue row onto its domain model."""
        data = row_to_dict(row)
        return Hint(
            id=str(data["id"]),
            challenge_id=str(data["challenge_id"]),
            tier=int(data["tier"]),
            title=str(data["title"]),
            content=str(data["content"]),
            cost=int(data["cost"]),
            base_cost=int(data["base_cost"]),
            multiplier=float(data["multiplier"]),
            reveal_after_seconds=int(data["reveal_after_seconds"]),
            is_active=bool(data["is_active"]),
            created_at=_timestamp(data["created_at"]),
            updated_at=_timestamp(data["updated_at"]),
        )

    def list_all(
        self,
        *,
        challenge_id: str | None = None,
        team_id: str | None = None,
    ) -> list[Hint]:
        """Return hints, optionally filtered by challenge and owning team."""
        sql = f"SELECT {HINT_COLUMNS} FROM v3_hints"
        params: list[Any] = []
        if team_id is not None:
            sql += " WHERE challenge_id IN (SELECT id FROM challenges WHERE team_id = ?)"
            params.append(team_id)
            if challenge_id is not None:
                sql += " AND challenge_id = ?"
                params.append(challenge_id)
        elif challenge_id is not None:
            sql += " WHERE challenge_id = ?"
            params.append(challenge_id)
        rows = self.fetch_all(f"{sql} ORDER BY tier ASC, created_at ASC", params)
        return [self.to_model(row) for row in rows]

    def get(self, hint_id: str) -> Hint | None:
        """Return one hint by identifier."""
        row = self.fetch_one(f"SELECT {HINT_COLUMNS} FROM v3_hints WHERE id = ?", (hint_id,))
        return self.to_model(row) if row is not None else None

    def find_tier(self, challenge_id: str, tier: int) -> Hint | None:
        """Return the hint occupying a tier of a challenge ladder."""
        row = self.fetch_one(
            f"SELECT {HINT_COLUMNS} FROM v3_hints WHERE challenge_id = ? AND tier = ?",
            (challenge_id, tier),
        )
        return self.to_model(row) if row is not None else None

    def create(self, hint: Hint) -> Hint:
        """Insert a hint and return the stored copy."""
        self.execute(
            """
            INSERT INTO v3_hints
                (id, challenge_id, tier, title, content, cost, base_cost,
                 multiplier, reveal_after_seconds, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                hint.id,
                hint.challenge_id,
                hint.tier,
                hint.title,
                hint.content,
                hint.cost,
                hint.base_cost,
                hint.multiplier,
                hint.reveal_after_seconds,
                int(hint.is_active),
                format_datetime(hint.created_at),
                format_datetime(hint.updated_at),
            ),
        )
        return hint

    def update(self, hint: Hint) -> Hint:
        """Replace the mutable fields of a hint."""
        self.execute(
            """
            UPDATE v3_hints
            SET title = ?, content = ?, cost = ?, base_cost = ?, multiplier = ?,
                reveal_after_seconds = ?, is_active = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                hint.title,
                hint.content,
                hint.cost,
                hint.base_cost,
                hint.multiplier,
                hint.reveal_after_seconds,
                int(hint.is_active),
                format_datetime(hint.updated_at),
                hint.id,
            ),
        )
        return hint

    def delete(self, hint_id: str) -> bool:
        """Delete a hint, returning whether a row was removed."""
        return self.execute("DELETE FROM v3_hints WHERE id = ?", (hint_id,)) > 0


class HintUnlockRepository(BaseRepository):
    """Persistence operations for the append-only reveal ledger."""

    table = "v3_hint_unlocks"

    @staticmethod
    def to_model(row: sqlite3.Row) -> HintUnlock:
        """Map a ledger row onto its domain model."""
        data = row_to_dict(row)
        return HintUnlock(
            id=str(data["id"]),
            hint_id=str(data["hint_id"]),
            member_id=str(data["member_id"]),
            team_id=str(data["team_id"]),
            cost_paid=int(data["cost_paid"]),
            unlocked_at=_timestamp(data["unlocked_at"]),
        )

    def find(self, hint_id: str, team_id: str) -> HintUnlock | None:
        """Return the team's unlock record for a hint, if it exists."""
        row = self.fetch_one(
            f"SELECT {UNLOCK_COLUMNS} FROM v3_hint_unlocks WHERE hint_id = ? AND team_id = ?",
            (hint_id, team_id),
        )
        return self.to_model(row) if row is not None else None

    def list_for_team(self, team_id: str) -> list[HintUnlock]:
        """Return every reveal recorded by a team, newest first."""
        rows = self.fetch_all(
            f"SELECT {UNLOCK_COLUMNS} FROM v3_hint_unlocks "
            "WHERE team_id = ? ORDER BY unlocked_at DESC",
            (team_id,),
        )
        return [self.to_model(row) for row in rows]

    def unlocked_tiers(self, challenge_id: str, team_id: str) -> frozenset[int]:
        """Return the set of tiers already revealed for a challenge."""
        rows = self.fetch_all(
            """
            SELECT h.tier FROM v3_hint_unlocks AS u
            JOIN v3_hints AS h ON h.id = u.hint_id
            WHERE u.team_id = ? AND h.challenge_id = ?
            """,
            (team_id, challenge_id),
        )
        return frozenset(int(row["tier"]) for row in rows)

    def count_for_team(self, team_id: str) -> int:
        """Return the number of hints revealed by a team."""
        return int(
            self.fetch_value(
                "SELECT COUNT(*) FROM v3_hint_unlocks WHERE team_id = ?", (team_id,), 0
            )
            or 0
        )

    def spend_by_tier(self, team_id: str) -> tuple[TierSpend, ...]:
        """Return per-tier unlock counts and spending for a team."""
        rows = self.fetch_all(
            """
            SELECT h.tier AS tier, COUNT(*) AS unlocks, COALESCE(SUM(u.cost_paid), 0) AS spent
            FROM v3_hint_unlocks AS u
            JOIN v3_hints AS h ON h.id = u.hint_id
            WHERE u.team_id = ?
            GROUP BY h.tier ORDER BY h.tier ASC
            """,
            (team_id,),
        )
        return tuple(
            TierSpend(
                tier=int(row["tier"]),
                unlocks=int(row["unlocks"]),
                spent=int(row["spent"]),
            )
            for row in rows
        )

    def ledger(self, team_id: str) -> list[LedgerEntry]:
        """Return the joined, display-ready ledger of a team."""
        rows = self.fetch_all(
            """
            SELECT u.id, u.hint_id, u.team_id, u.cost_paid, u.unlocked_at,
                   h.title AS hint_title, h.tier AS tier,
                   COALESCE(m.handle, 'unknown') AS member_handle, u.member_id
            FROM v3_hint_unlocks AS u
            JOIN v3_hints AS h ON h.id = u.hint_id
            LEFT JOIN members AS m ON m.id = u.member_id
            WHERE u.team_id = ?
            ORDER BY u.unlocked_at DESC, u.id DESC
            """,
            (team_id,),
        )
        return [
            LedgerEntry(
                id=str(row["id"]),
                hint_id=str(row["hint_id"]),
                hint_title=str(row["hint_title"]),
                tier=int(row["tier"]),
                member_id=str(row["member_id"]),
                member_handle=str(row["member_handle"]),
                team_id=str(row["team_id"]),
                cost_paid=int(row["cost_paid"]),
                unlocked_at=_timestamp(row["unlocked_at"]),
            )
            for row in rows
        ]


class HintBudgetRepository(BaseRepository):
    """Persistence operations for team hint budgets."""

    table = "v3_hint_budgets"

    @staticmethod
    def to_model(row: sqlite3.Row) -> HintBudget:
        """Map a budget row onto its domain model."""
        data = row_to_dict(row)
        return HintBudget(
            team_id=str(data["team_id"]),
            total=int(data["total"]),
            spent=int(data["spent"]),
            reset_at=_timestamp(data["reset_at"]),
            created_at=_timestamp(data["created_at"]),
        )

    def get(self, team_id: str) -> HintBudget | None:
        """Return a team's budget, when one has been provisioned."""
        row = self.fetch_one("SELECT * FROM v3_hint_budgets WHERE team_id = ?", (team_id,))
        return self.to_model(row) if row is not None else None

    def upsert(self, budget: HintBudget) -> HintBudget:
        """Insert or update a budget by team identifier."""
        self.execute(
            """
            INSERT INTO v3_hint_budgets (team_id, total, spent, reset_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(team_id) DO UPDATE SET
                total = excluded.total,
                spent = excluded.spent,
                reset_at = excluded.reset_at
            """,
            (
                budget.team_id,
                budget.total,
                budget.spent,
                format_datetime(budget.reset_at),
                format_datetime(budget.created_at),
            ),
        )
        return budget

    def reset(self, team_id: str, total: int, reset_at: Any) -> HintBudget:
        """Clear spending and set the next reset instant."""
        row = self.fetch_one("SELECT created_at FROM v3_hint_budgets WHERE team_id = ?", (team_id,))
        created = _timestamp(row["created_at"]) if row is not None else utcnow()
        if row is None:
            self.upsert(
                HintBudget(
                    team_id=team_id,
                    total=total,
                    spent=0,
                    reset_at=reset_at,
                    created_at=created,
                )
            )
        else:
            self.execute(
                "UPDATE v3_hint_budgets SET total = ?, spent = 0, reset_at = ? WHERE team_id = ?",
                (total, format_datetime(reset_at), team_id),
            )
        return HintBudget(
            team_id=team_id,
            total=total,
            spent=0,
            reset_at=reset_at,
            created_at=created,
        )


class HintStore:
    """Aggregate of the repositories owned by the hint engine."""

    def __init__(self, database: Database | None = None) -> None:
        gateway = database or get_database()
        self.hints = HintRepository(gateway)
        self.unlocks = HintUnlockRepository(gateway)
        self.budgets = HintBudgetRepository(gateway)

    @property
    def database(self) -> Database:
        """Return the database gateway shared by the repositories."""
        return self.hints.database

    def atomic_unlock(self, unlock: HintUnlock, hint: Hint) -> HintUnlock:
        """Insert a ledger row and debit the budget in one transaction.

        Both the duplicate check and the affordability check are repeated
        inside the write transaction so concurrent unlock attempts cannot
        overspend the allowance or reveal the same hint twice.

        Args:
            unlock: The ledger row to insert.
            hint: The hint being purchased.

        Returns:
            The persisted unlock.

        Raises:
            ConflictError: When the team already unlocked this hint.
            ValidationError: When the remaining allowance is insufficient.
        """
        with self.database.transaction() as connection:
            duplicate = connection.execute(
                "SELECT 1 FROM v3_hint_unlocks WHERE hint_id = ? AND team_id = ?",
                (unlock.hint_id, unlock.team_id),
            ).fetchone()
            if duplicate is not None:
                raise ConflictError(
                    "This hint has already been unlocked by the team",
                    details={"hint_id": unlock.hint_id, "team_id": unlock.team_id},
                )
            row = connection.execute(
                "SELECT total, spent FROM v3_hint_budgets WHERE team_id = ?",
                (unlock.team_id,),
            ).fetchone()
            if row is None:
                raise ValidationError(
                    "No hint budget is provisioned for this team",
                    details={"team_id": unlock.team_id},
                )
            remaining = int(row["total"]) - int(row["spent"])
            if hint.cost > remaining:
                raise ValidationError(
                    "The team does not have enough hint budget",
                    details={"cost": hint.cost, "remaining": remaining},
                )
            connection.execute(
                "UPDATE v3_hint_budgets SET spent = spent + ? WHERE team_id = ?",
                (hint.cost, unlock.team_id),
            )
            connection.execute(
                """
                INSERT INTO v3_hint_unlocks
                    (id, hint_id, member_id, team_id, cost_paid, unlocked_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    unlock.id,
                    unlock.hint_id,
                    unlock.member_id,
                    unlock.team_id,
                    hint.cost,
                    format_datetime(unlock.unlocked_at),
                ),
            )
        return unlock

    def ensure_budget(self, team_id: str, total: int, reset_at: Any) -> HintBudget:
        """Return an existing budget or provision a default one."""
        existing = self.budgets.get(team_id)
        if existing is not None:
            return existing
        return self.budgets.upsert(
            HintBudget(
                team_id=team_id,
                total=total,
                spent=0,
                reset_at=reset_at,
            )
        )

    def fetch_value(self, sql: str, params: Sequence[Any] = (), default: Any = None) -> Any:
        """Delegate a scalar query to the ledger repository."""
        return self.unlocks.fetch_value(sql, params, default)
