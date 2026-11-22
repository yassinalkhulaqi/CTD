"""Pydantic schemas for settings preferences API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PreferenceSchemaField(BaseModel):
    """Describes a preference schema field."""

    model_config = ConfigDict(extra="forbid")

    key: str
    value_type: str
    default: Any
    label: str
    description: str
    choices: list[str] = Field(default_factory=list)
    min_value: int | None = None
    max_value: int | None = None


class PreferencesResponse(BaseModel):
    """Effective preferences response."""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    values: dict[str, Any]
    defaults: dict[str, Any]
    schema_fields: list[PreferenceSchemaField]


class PreferencesUpdateRequest(BaseModel):
    """Request to update preference overrides."""

    model_config = ConfigDict(extra="forbid")

    user_id: str = "default"
    values: dict[str, Any]


class ThemeContrastRead(BaseModel):
    """Contrast evaluation for a token pair."""

    model_config = ConfigDict(extra="forbid")

    foreground: str
    background: str
    ratio: float
    passes_aa: bool


class ThemeResponse(BaseModel):
    """Theme token response."""

    model_config = ConfigDict(extra="forbid")

    tokens: dict[str, str]
    contrast: list[ThemeContrastRead]
    passes: bool


class ThemeUpdateRequest(BaseModel):
    """Request to update theme tokens."""

    model_config = ConfigDict(extra="forbid")

    tokens: dict[str, str]


class LayoutResponse(BaseModel):
    """Workspace layout response."""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    density: str
    sidebar_position: str
    show_activity: bool
    timezone: str
    date_format: str
    updated_at: str


class LayoutUpdateRequest(BaseModel):
    """Request to update layout."""

    model_config = ConfigDict(extra="forbid")

    user_id: str = "default"
    density: str | None = None
    sidebar_position: str | None = None
    show_activity: bool | None = None
    timezone: str | None = None
    date_format: str | None = None


class ResetRequest(BaseModel):
    """Request to reset preferences/layout/theme."""

    model_config = ConfigDict(extra="forbid")

    user_id: str = "default"


class ResetResponse(BaseModel):
    """Response after reset."""

    model_config = ConfigDict(extra="forbid")

    preferences: dict[str, Any]
    layout: LayoutResponse
    theme: ThemeResponse


class ImportExportResponse(BaseModel):
    """Config export/import payload."""

    model_config = ConfigDict(extra="forbid")

    version: int
    user_id: str
    preferences: dict[str, Any]
    theme: dict[str, str]
    layout: LayoutResponse


class ImportRequest(BaseModel):
    """Request to import config."""

    model_config = ConfigDict(extra="forbid")

    user_id: str = "default"
    config: dict[str, Any]
