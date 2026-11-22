"""Persistence for the onboarding tour feature.

All queries are parameterised and routed through :class:`BaseRepository`. The
tables themselves are created by the schema script exported from the package,
which the shared database migration applies automatically.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Sequence
from typing import Any

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.features.onboarding_tour.models import (
    OnboardingProgress,
    OnboardingStep,
    SetupChecklist,
    StepKind,
    parse_checklist_items,
)
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    format_datetime,
    parse_datetime,
    row_to_dict,
)


class OnboardingStepRepository(BaseRepository):
    """Persistence operations for the onboarding step catalogue."""

    table = "v3_onboarding_steps"

    @staticmethod
    def to_model(row: sqlite3.Row) -> OnboardingStep:
        """Map a database row onto an :class:`OnboardingStep`."""
        data = row_to_dict(row)
        created = parse_datetime(str(data["created_at"]))
        return OnboardingStep(
            id=str(data["id"]),
            slug=str(data["slug"]),
            title=str(data["title"]),
            description=str(data["description"]),
            target=str(data["target"]),
            order=int(data["step_order"]),
            completion_key=str(data["completion_key"]),
            kind=StepKind(str(data.get("kind", StepKind.GUIDE.value))),
            estimated_seconds=int(data.get("estimated_seconds", 60)),
            required=bool(data.get("required", 1)),
            hint=str(data.get("hint", "")),
            icon=str(data.get("icon", "compass")),
            created_at=created if created is not None else utcnow(),
        )

    def all_ordered(self) -> list[OnboardingStep]:
        """Return every catalogue step in display order."""
        rows = self.fetch_all("SELECT * FROM v3_onboarding_steps ORDER BY step_order ASC, slug ASC")
        return [self.to_model(row) for row in rows]

    def get(self, step_id: str) -> OnboardingStep | None:
        """Return a step by identifier, when present."""
        row = self.fetch_one("SELECT * FROM v3_onboarding_steps WHERE id = ?", (step_id,))
        return self.to_model(row) if row is not None else None

    def get_by_slug(self, slug: str) -> OnboardingStep | None:
        """Return a step by its human readable slug."""
        row = self.fetch_one("SELECT * FROM v3_onboarding_steps WHERE slug = ?", (slug,))
        return self.to_model(row) if row is not None else None

    def get_by_key(self, completion_key: str) -> OnboardingStep | None:
        """Return a step by its completion key."""
        row = self.fetch_one(
            "SELECT * FROM v3_onboarding_steps WHERE completion_key = ?",
            (completion_key,),
        )
        return self.to_model(row) if row is not None else None

    def find(self, reference: str) -> OnboardingStep | None:
        """Resolve a step from an identifier, slug or completion key."""
        return self.get(reference) or self.get_by_slug(reference) or self.get_by_key(reference)

    def seed(self, steps: Iterable[OnboardingStep]) -> int:
        """Insert catalogue steps that are not stored yet.

        The operation is idempotent: existing identifiers are left untouched so
        a restart never resets a user's journey.

        Args:
            steps: The catalogue to insert.

        Returns:
            The number of rows that were newly inserted.
        """
        rows: list[tuple[Any, ...]] = [
            (
                step.id,
                step.slug,
                step.title,
                step.description,
                step.target,
                step.order,
                step.completion_key,
                step.kind.value,
                step.estimated_seconds,
                int(step.required),
                step.hint,
                step.icon,
                format_datetime(step.created_at),
            )
            for step in steps
        ]
        if not rows:
            return 0
        return self.execute_many(
            """
            INSERT OR IGNORE INTO v3_onboarding_steps (
                id, slug, title, description, target, step_order,
                completion_key, kind, estimated_seconds, required, hint,
                icon, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    def count(self, where: str = "", params: Sequence[Any] = ()) -> int:
        """Return the number of catalogue rows, optionally filtered."""
        return super().count(where, params)


class OnboardingProgressRepository(BaseRepository):
    """Persistence operations for per-user step progress."""

    table = "v3_onboarding_progress"

    @staticmethod
    def to_model(row: sqlite3.Row) -> OnboardingProgress:
        """Map a database row onto an :class:`OnboardingProgress`."""
        data = row_to_dict(row)
        completed = parse_datetime(str(data["completed_at"]))
        return OnboardingProgress(
            user_id=str(data["user_id"]),
            step_id=str(data["step_id"]),
            completed_at=completed if completed is not None else utcnow(),
            skipped=bool(data.get("skipped", 0)),
        )

    def list_for_user(self, user_id: str) -> list[OnboardingProgress]:
        """Return every progress record of a user, oldest first."""
        rows = self.fetch_all(
            """
            SELECT * FROM v3_onboarding_progress
            WHERE user_id = ? ORDER BY completed_at ASC, step_id ASC
            """,
            (user_id,),
        )
        return [self.to_model(row) for row in rows]

    def get(self, user_id: str, step_id: str) -> OnboardingProgress | None:
        """Return one progress record, when present."""
        row = self.fetch_one(
            """
            SELECT * FROM v3_onboarding_progress
            WHERE user_id = ? AND step_id = ?
            """,
            (user_id, step_id),
        )
        return self.to_model(row) if row is not None else None

    def upsert(self, record: OnboardingProgress) -> OnboardingProgress:
        """Insert or replace a progress record."""
        self.execute(
            """
            INSERT INTO v3_onboarding_progress (user_id, step_id, completed_at, skipped)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, step_id) DO UPDATE SET
                completed_at = excluded.completed_at,
                skipped = excluded.skipped
            """,
            (
                record.user_id,
                record.step_id,
                format_datetime(record.completed_at),
                int(record.skipped),
            ),
        )
        return record

    def delete(self, user_id: str, step_id: str) -> bool:
        """Remove a single progress record and report whether one existed."""
        return (
            self.execute(
                """
                DELETE FROM v3_onboarding_progress
                WHERE user_id = ? AND step_id = ?
                """,
                (user_id, step_id),
            )
            > 0
        )

    def delete_for_user(self, user_id: str) -> int:
        """Remove every progress record of a user and return the row count."""
        return self.execute("DELETE FROM v3_onboarding_progress WHERE user_id = ?", (user_id,))

    def latest_for_user(self, user_id: str) -> OnboardingProgress | None:
        """Return the most recent progress record of a user."""
        row = self.fetch_one(
            """
            SELECT * FROM v3_onboarding_progress
            WHERE user_id = ? ORDER BY completed_at DESC LIMIT 1
            """,
            (user_id,),
        )
        return self.to_model(row) if row is not None else None

    def count_for_user(self, user_id: str, *, skipped: bool | None = None) -> int:
        """Count the records of a user, optionally filtering skipped ones."""
        if skipped is None:
            return self.count("user_id = ?", (user_id,))
        return self.count("user_id = ? AND skipped = ?", (user_id, int(skipped)))


class ChecklistRepository(BaseRepository):
    """Persistence operations for the setup checklist."""

    table = "v3_checklists"

    @staticmethod
    def to_model(row: sqlite3.Row) -> SetupChecklist:
        """Map a database row onto a :class:`SetupChecklist`."""
        data = row_to_dict(row)
        updated = parse_datetime(str(data["updated_at"]))
        return SetupChecklist(
            user_id=str(data["user_id"]),
            items_json=str(data["items_json"]),
            updated_at=updated if updated is not None else utcnow(),
        )

    def get(self, user_id: str) -> SetupChecklist | None:
        """Return the checklist of a user, when one has been saved."""
        row = self.fetch_one("SELECT * FROM v3_checklists WHERE user_id = ?", (user_id,))
        return self.to_model(row) if row is not None else None

    def save(self, checklist: SetupChecklist) -> SetupChecklist:
        """Insert or replace the checklist of a user."""
        self.execute(
            """
            INSERT INTO v3_checklists (user_id, items_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                items_json = excluded.items_json,
                updated_at = excluded.updated_at
            """,
            (
                checklist.user_id,
                checklist.items_json,
                format_datetime(checklist.updated_at),
            ),
        )
        return checklist

    def delete(self, user_id: str) -> bool:
        """Delete the checklist of a user and report whether one existed."""
        return self.execute("DELETE FROM v3_checklists WHERE user_id = ?", (user_id,)) > 0

    def item_ids(self, user_id: str) -> tuple[str, ...]:
        """Return the identifiers stored on a user's checklist."""
        checklist = self.get(user_id)
        if checklist is None:
            return ()
        return tuple(item.id for item in parse_checklist_items(checklist.items_json))
