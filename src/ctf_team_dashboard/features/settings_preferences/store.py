"""Persistence for settings preferences feature."""

from __future__ import annotations

import json
from typing import Any

from ctf_team_dashboard.domain.models import ensure_utc
from ctf_team_dashboard.features.settings_preferences.models import (
    DEFAULT_THEME_TOKENS,
    Preference,
    ThemeToken,
    WorkspaceLayout,
    parse_updated_at,
)
from ctf_team_dashboard.repositories.base import BaseRepository


class PreferenceRepository(BaseRepository):
    """CRUD operations for preference overrides."""

    table = "v3_preferences"

    def list_for_user(self, user_id: str) -> list[Preference]:
        rows = self.fetch_all(
            """
            SELECT id, user_id, key, value_json, updated_at
            FROM v3_preferences
            WHERE user_id = ?
            ORDER BY key ASC
            """,
            (user_id,),
        )
        return [self._row_to_preference(row) for row in rows]

    def get(self, user_id: str, key: str) -> Preference | None:
        row = self.fetch_one(
            """
            SELECT id, user_id, key, value_json, updated_at
            FROM v3_preferences
            WHERE user_id = ? AND key = ?
            """,
            (user_id, key),
        )
        return self._row_to_preference(row) if row is not None else None

    def upsert(self, preference: Preference) -> Preference:
        self.execute(
            """
            INSERT INTO v3_preferences (id, user_id, key, value_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, key) DO UPDATE SET
                value_json = excluded.value_json,
                updated_at = excluded.updated_at
            """,
            (
                preference.id,
                preference.user_id,
                preference.key,
                preference.value_json,
                ensure_utc(preference.updated_at).isoformat(),
            ),
        )
        stored = self.get(preference.user_id, preference.key)
        return stored if stored is not None else preference

    def delete_for_user(self, user_id: str) -> int:
        return self.execute("DELETE FROM v3_preferences WHERE user_id = ?", (user_id,))

    def replace_for_user(self, user_id: str, preferences: list[Preference]) -> None:
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM v3_preferences WHERE user_id = ?", (user_id,))
            connection.executemany(
                """
                INSERT INTO v3_preferences (id, user_id, key, value_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        pref.id,
                        pref.user_id,
                        pref.key,
                        pref.value_json,
                        ensure_utc(pref.updated_at).isoformat(),
                    )
                    for pref in preferences
                ],
            )

    @staticmethod
    def _row_to_preference(row: Any) -> Preference:
        raw_value = row["value_json"]
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        return Preference(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            key=str(row["key"]),
            value=value,
            updated_at=parse_updated_at(row["updated_at"]),
        )


class ThemeTokenRepository(BaseRepository):
    """Persistence for theme token map."""

    table = "v3_theme_tokens"

    def list_all(self) -> list[ThemeToken]:
        rows = self.fetch_all("SELECT name, value FROM v3_theme_tokens ORDER BY name ASC")
        return [ThemeToken(name=str(row["name"]), value=str(row["value"])) for row in rows]

    def replace_all(self, tokens: list[ThemeToken]) -> list[ThemeToken]:
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM v3_theme_tokens")
            connection.executemany(
                "INSERT INTO v3_theme_tokens (name, value) VALUES (?, ?)",
                [(token.name, token.value) for token in tokens],
            )
        return self.list_all()

    def ensure_defaults(self) -> list[ThemeToken]:
        existing = self.list_all()
        if existing:
            return existing
        return self.replace_all(list(DEFAULT_THEME_TOKENS))


class LayoutRepository(BaseRepository):
    """Persistence for per-user workspace layout."""

    table = "v3_layouts"

    def get(self, user_id: str) -> WorkspaceLayout | None:
        row = self.fetch_one(
            """
            SELECT
                user_id,
                density,
                sidebar_position,
                show_activity,
                timezone,
                date_format,
                updated_at
            FROM v3_layouts
            WHERE user_id = ?
            """,
            (user_id,),
        )
        if row is None:
            return None
        from ctf_team_dashboard.features.settings_preferences.models import Density, SidebarPosition

        return WorkspaceLayout(
            user_id=str(row["user_id"]),
            density=Density(str(row["density"])),
            sidebar_position=SidebarPosition(str(row["sidebar_position"])),
            show_activity=bool(row["show_activity"]),
            timezone=str(row["timezone"]),
            date_format=str(row["date_format"]),
            updated_at=parse_updated_at(row["updated_at"]),
        )

    def upsert(self, layout: WorkspaceLayout) -> WorkspaceLayout:
        self.execute(
            """
            INSERT INTO v3_layouts (
                user_id, density, sidebar_position, show_activity, timezone, date_format, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                density = excluded.density,
                sidebar_position = excluded.sidebar_position,
                show_activity = excluded.show_activity,
                timezone = excluded.timezone,
                date_format = excluded.date_format,
                updated_at = excluded.updated_at
            """,
            (
                layout.user_id,
                layout.density.value,
                layout.sidebar_position.value,
                1 if layout.show_activity else 0,
                layout.timezone,
                layout.date_format,
                ensure_utc(layout.updated_at).isoformat(),
            ),
        )
        stored = self.get(layout.user_id)
        return stored if stored is not None else layout

    def delete_for_user(self, user_id: str) -> int:
        return self.execute("DELETE FROM v3_layouts WHERE user_id = ?", (user_id,))
