"""Business logic for settings and preferences."""

from __future__ import annotations

import uuid
from typing import Any

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.errors import ValidationError
from ctf_team_dashboard.features.settings_preferences.models import (
    DEFAULT_THEME_TOKENS,
    Preference,
    ThemeToken,
    WorkspaceLayout,
    coerce_preference_value,
    default_layout,
    ensure_required_theme_tokens,
    evaluate_theme_tokens,
    layout_from_mapping,
    merge_preferences,
    normalize_theme_tokens,
    theme_tokens_to_map,
    validate_preference_key,
)
from ctf_team_dashboard.features.settings_preferences.store import (
    LayoutRepository,
    PreferenceRepository,
    ThemeTokenRepository,
)


class SettingsPreferencesService:
    """Service orchestrating preferences, theme tokens, and layout."""

    def __init__(
        self,
        preferences: PreferenceRepository | None = None,
        tokens: ThemeTokenRepository | None = None,
        layouts: LayoutRepository | None = None,
    ) -> None:
        self.preferences = preferences or PreferenceRepository()
        self.tokens = tokens or ThemeTokenRepository()
        self.layouts = layouts or LayoutRepository()

    @staticmethod
    def _uid() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def _user(user_id: str | None) -> str:
        cleaned = (user_id or "default").strip()
        if not cleaned:
            raise ValidationError("user_id cannot be empty")
        return cleaned

    def get_preferences(self, user_id: str | None = None) -> dict[str, Any]:
        uid = self._user(user_id)
        overrides = {p.key: p.value for p in self.preferences.list_for_user(uid)}
        try:
            return merge_preferences(overrides)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    def update_preferences(self, user_id: str | None, updates: dict[str, Any]) -> dict[str, Any]:
        uid = self._user(user_id)
        if not isinstance(updates, dict) or not updates:
            raise ValidationError("updates must be a non-empty object")
        now = utcnow()
        records: list[Preference] = []
        for key, value in updates.items():
            try:
                validate_preference_key(key)
                coerced = coerce_preference_value(key, value)
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc
            records.append(
                Preference(
                    id=self._uid(),
                    user_id=uid,
                    key=key,
                    value=coerced,
                    updated_at=now,
                )
            )
        for record in records:
            self.preferences.upsert(record)
        return self.get_preferences(uid)

    def reset_preferences(self, user_id: str | None = None) -> dict[str, Any]:
        uid = self._user(user_id)
        self.preferences.delete_for_user(uid)
        self.layouts.delete_for_user(uid)
        self.tokens.replace_all(list(DEFAULT_THEME_TOKENS))
        return {
            "preferences": self.get_preferences(uid),
            "layout": self.get_layout(uid),
            "theme": self.get_theme(),
        }

    def get_theme(self) -> dict[str, Any]:
        tokens = self.tokens.ensure_defaults()
        token_map = theme_tokens_to_map(tokens)
        evaluations = evaluate_theme_tokens(token_map)
        return {
            "tokens": token_map,
            "contrast": [
                {
                    "foreground": e.foreground,
                    "background": e.background,
                    "ratio": e.ratio,
                    "passes_aa": e.passes_aa,
                }
                for e in evaluations
            ],
            "passes": all(e.passes_aa for e in evaluations),
        }

    def update_theme(self, tokens: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(tokens, dict) or not tokens:
            raise ValidationError("tokens must be a non-empty object")
        try:
            normalized = normalize_theme_tokens({str(k): str(v) for k, v in tokens.items()})
            merged = ensure_required_theme_tokens(normalized)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        evaluations = evaluate_theme_tokens(merged)
        failing = [e for e in evaluations if not e.passes_aa]
        if failing:
            detail = ", ".join(f"{e.foreground}/{e.background}={e.ratio}" for e in failing)
            raise ValidationError(f"Theme contrast fails WCAG AA: {detail}")
        stored = [ThemeToken(name=name, value=value) for name, value in sorted(merged.items())]
        self.tokens.replace_all(stored)
        return self.get_theme()

    def get_layout(self, user_id: str | None = None) -> dict[str, Any]:
        uid = self._user(user_id)
        layout = self.layouts.get(uid) or default_layout(uid)
        return layout.to_dict()

    def update_layout(self, user_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        uid = self._user(user_id)
        if not isinstance(payload, dict) or not payload:
            raise ValidationError("layout payload must be a non-empty object")
        current = self.layouts.get(uid) or default_layout(uid)
        data = current.to_dict()
        data.update(payload)
        try:
            layout = layout_from_mapping(uid, data)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        layout = WorkspaceLayout(
            user_id=layout.user_id,
            density=layout.density,
            sidebar_position=layout.sidebar_position,
            show_activity=layout.show_activity,
            timezone=layout.timezone,
            date_format=layout.date_format,
            updated_at=utcnow(),
        )
        stored = self.layouts.upsert(layout)
        return stored.to_dict()

    def export_config(self, user_id: str | None = None) -> dict[str, Any]:
        uid = self._user(user_id)
        return {
            "version": 1,
            "user_id": uid,
            "preferences": self.get_preferences(uid),
            "theme": self.get_theme()["tokens"],
            "layout": self.get_layout(uid),
        }

    def import_config(self, user_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        uid = self._user(user_id)
        if not isinstance(payload, dict):
            raise ValidationError("import payload must be an object")
        version = payload.get("version", 1)
        if version != 1:
            raise ValidationError("Unsupported config version")
        preferences = payload.get("preferences", {})
        theme = payload.get("theme", {})
        layout = payload.get("layout", {})
        if preferences and not isinstance(preferences, dict):
            raise ValidationError("preferences must be an object")
        if theme and not isinstance(theme, dict):
            raise ValidationError("theme must be an object")
        if layout and not isinstance(layout, dict):
            raise ValidationError("layout must be an object")

        # Validate all before writing
        validated_preferences = None
        if preferences:
            try:
                validated_preferences = merge_preferences(
                    {str(k): v for k, v in preferences.items()}
                )
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc
        validated_theme = None
        if theme:
            try:
                normalized = normalize_theme_tokens({str(k): str(v) for k, v in theme.items()})
                merged_theme = ensure_required_theme_tokens(normalized)
                evals = evaluate_theme_tokens(merged_theme)
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc
            if not all(e.passes_aa for e in evals):
                raise ValidationError("Imported theme fails WCAG AA contrast")
            validated_theme = merged_theme
        validated_layout = None
        if layout:
            try:
                validated_layout = layout_from_mapping(uid, {str(k): v for k, v in layout.items()})
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc

        if validated_preferences is not None:
            self.preferences.delete_for_user(uid)
            now = utcnow()
            for key, value in validated_preferences.items():
                # store only non-default? easier to store all explicit for import fidelity
                self.preferences.upsert(
                    Preference(id=self._uid(), user_id=uid, key=key, value=value, updated_at=now)
                )
        if validated_theme is not None:
            self.tokens.replace_all(
                [ThemeToken(name=n, value=v) for n, v in sorted(validated_theme.items())]
            )
        if validated_layout is not None:
            self.layouts.upsert(
                WorkspaceLayout(
                    user_id=uid,
                    density=validated_layout.density,
                    sidebar_position=validated_layout.sidebar_position,
                    show_activity=validated_layout.show_activity,
                    timezone=validated_layout.timezone,
                    date_format=validated_layout.date_format,
                    updated_at=utcnow(),
                )
            )

        return self.export_config(uid)
