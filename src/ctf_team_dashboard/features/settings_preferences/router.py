"""HTTP API for settings and preferences."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ctf_team_dashboard.features.settings_preferences.models import (
    PREFERENCE_SCHEMA,
    default_preferences,
)
from ctf_team_dashboard.features.settings_preferences.schemas import (
    ImportExportResponse,
    ImportRequest,
    LayoutResponse,
    LayoutUpdateRequest,
    PreferenceSchemaField,
    PreferencesResponse,
    PreferencesUpdateRequest,
    ResetRequest,
    ResetResponse,
    ThemeResponse,
    ThemeUpdateRequest,
)
from ctf_team_dashboard.features.settings_preferences.service import (
    SettingsPreferencesService,
)

router = APIRouter(prefix="/api/preferences", tags=["settings-preferences"])


def _service() -> SettingsPreferencesService:
    return SettingsPreferencesService()


def _schema_fields() -> list[PreferenceSchemaField]:
    return [
        PreferenceSchemaField(
            key=f.key,
            value_type=f.value_type.value,
            default=f.default,
            label=f.label,
            description=f.description,
            choices=list(f.choices),
            min_value=f.min_value,
            max_value=f.max_value,
        )
        for f in PREFERENCE_SCHEMA
    ]


def _layout_response(data: dict[str, Any]) -> LayoutResponse:
    return LayoutResponse.model_validate(data)


def _theme_response(data: dict[str, Any]) -> ThemeResponse:
    return ThemeResponse.model_validate(data)


@router.get("", response_model=PreferencesResponse)
def get_preferences(user_id: str = Query(default="default")) -> PreferencesResponse:
    """Return effective preferences with defaults and schema."""
    service = _service()
    values = service.get_preferences(user_id)
    return PreferencesResponse(
        user_id=user_id,
        values=values,
        defaults=default_preferences(),
        schema_fields=_schema_fields(),
    )


@router.put("", response_model=PreferencesResponse)
def update_preferences(payload: PreferencesUpdateRequest) -> PreferencesResponse:
    """Validate and update preference overrides."""
    service = _service()
    values = service.update_preferences(payload.user_id, payload.values)
    return PreferencesResponse(
        user_id=payload.user_id,
        values=values,
        defaults=default_preferences(),
        schema_fields=_schema_fields(),
    )


@router.get("/theme", response_model=ThemeResponse)
def get_theme() -> ThemeResponse:
    """Return theme tokens and contrast evaluation."""
    return _theme_response(_service().get_theme())


@router.put("/theme", response_model=ThemeResponse)
def update_theme(payload: ThemeUpdateRequest) -> ThemeResponse:
    """Validate and update theme tokens."""
    return _theme_response(_service().update_theme(payload.tokens))


@router.get("/layout", response_model=LayoutResponse)
def get_layout(user_id: str = Query(default="default")) -> LayoutResponse:
    """Return workspace layout for user."""
    return _layout_response(_service().get_layout(user_id))


@router.put("/layout", response_model=LayoutResponse)
def update_layout(payload: LayoutUpdateRequest) -> LayoutResponse:
    """Update workspace layout."""
    data = payload.model_dump(exclude={"user_id"}, exclude_none=True)
    return _layout_response(_service().update_layout(payload.user_id, data))


@router.post("/reset", response_model=ResetResponse)
def reset_preferences(payload: ResetRequest) -> ResetResponse:
    """Reset preferences, theme, and layout to defaults."""
    result = _service().reset_preferences(payload.user_id)
    return ResetResponse(
        preferences=result["preferences"],
        layout=_layout_response(result["layout"]),
        theme=_theme_response(result["theme"]),
    )


@router.get("/import", response_model=ImportExportResponse)
def export_preferences(user_id: str = Query(default="default")) -> ImportExportResponse:
    """Export config for user."""
    data = _service().export_config(user_id)
    return ImportExportResponse(
        version=int(data["version"]),
        user_id=str(data["user_id"]),
        preferences=dict(data["preferences"]),
        theme=dict(data["theme"]),
        layout=_layout_response(dict(data["layout"])),
    )


@router.post("/import", response_model=ImportExportResponse)
def import_preferences(payload: ImportRequest) -> ImportExportResponse:
    """Import and validate config."""
    config = dict(payload.config)
    config.setdefault("version", 1)
    data = _service().import_config(payload.user_id, config)
    return ImportExportResponse(
        version=int(data["version"]),
        user_id=str(data["user_id"]),
        preferences=dict(data["preferences"]),
        theme=dict(data["theme"]),
        layout=_layout_response(dict(data["layout"])),
    )
