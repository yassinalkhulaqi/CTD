"""Tests for v3 settings preferences feature."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.db.engine import Database
from ctf_team_dashboard.errors import ValidationError
from ctf_team_dashboard.features.settings_preferences.models import (
    contrast_ratio,
    default_preferences,
    merge_preferences,
    normalize_hex_color,
)
from ctf_team_dashboard.features.settings_preferences.service import (
    SettingsPreferencesService,
)


def test_preference_defaults_and_coercion() -> None:
    defaults = default_preferences()
    assert defaults["notifications.email"] is True
    assert defaults["appearance.theme"] == "system"
    merged = merge_preferences(
        {
            "notifications.email": "false",
            "workspace.autoSaveSeconds": "45",
            "appearance.theme": "dark",
        }
    )
    assert merged["notifications.email"] is False
    assert merged["workspace.autoSaveSeconds"] == 45
    assert merged["appearance.theme"] == "dark"


def test_preference_key_validation_and_type_errors() -> None:
    with pytest.raises(ValueError):
        merge_preferences({"unknown.key": True})
    with pytest.raises(ValueError):
        merge_preferences({"workspace.autoSaveSeconds": 1})
    with pytest.raises(ValueError):
        merge_preferences({"appearance.theme": "blue"})


def test_theme_contrast_helpers() -> None:
    assert normalize_hex_color("#fff") == "#FFFFFF"
    ratio = contrast_ratio("#000000", "#FFFFFF")
    assert ratio == 21.0
    with pytest.raises(ValueError):
        normalize_hex_color("nope")


def test_service_preference_update_and_reset(database: Database) -> None:
    _ = database
    service = SettingsPreferencesService()
    values = service.update_preferences(
        "u1",
        {"notifications.desktop": True, "notifications.digest": "weekly"},
    )
    assert values["notifications.desktop"] is True
    assert values["notifications.digest"] == "weekly"
    reset = service.reset_preferences("u1")
    assert reset["preferences"] == default_preferences()
    assert reset["layout"]["user_id"] == "u1"


def test_service_theme_validation_and_layout(database: Database) -> None:
    _ = database
    service = SettingsPreferencesService()
    theme = service.update_theme(
        {
            "surface": "#FFFFFF",
            "surfaceMuted": "#F8FAFC",
            "textPrimary": "#0F172A",
            "textMuted": "#334155",
            "accent": "#4F46E5",
            "accentText": "#FFFFFF",
            "danger": "#B91C1C",
        }
    )
    assert theme["passes"] is True
    with pytest.raises(ValidationError):
        service.update_theme(
            {
                "surface": "#FFFFFF",
                "surfaceMuted": "#FFFFFF",
                "textPrimary": "#F8FAFC",
                "textMuted": "#F1F5F9",
                "accent": "#FFFFFF",
                "accentText": "#F8FAFC",
                "danger": "#FFFFFF",
            }
        )

    layout = service.update_layout(
        "u1",
        {
            "density": "compact",
            "sidebar_position": "right",
            "show_activity": False,
            "timezone": "UTC",
            "date_format": "DD/MM/YYYY",
        },
    )
    assert layout["density"] == "compact"
    assert layout["sidebar_position"] == "right"
    assert layout["show_activity"] is False
    with pytest.raises(ValidationError):
        service.update_layout("u1", {"density": "dense"})


def test_service_export_import_validation(database: Database) -> None:
    _ = database
    service = SettingsPreferencesService()
    service.update_preferences("u1", {"appearance.theme": "dark"})
    service.update_layout("u1", {"density": "compact", "timezone": "UTC"})
    exported = service.export_config("u1")
    assert exported["version"] == 1
    assert exported["preferences"]["appearance.theme"] == "dark"

    imported = service.import_config(
        "u2",
        {
            "version": 1,
            "preferences": {"appearance.accent": "teal"},
            "theme": exported["theme"],
            "layout": {
                "density": "comfortable",
                "timezone": "UTC",
                "date_format": "YYYY-MM-DD",
                "sidebar_position": "left",
                "show_activity": True,
            },
        },
    )
    assert imported["user_id"] == "u2"
    assert imported["preferences"]["appearance.accent"] == "teal"
    with pytest.raises(ValidationError):
        service.import_config("u2", {"version": 2})
    with pytest.raises(ValidationError):
        service.import_config("u2", {"version": 1, "preferences": {"bad.key": 1}})


def test_preferences_api_crud_and_validation(client: TestClient) -> None:
    res = client.get("/api/preferences", params={"user_id": "alice"})
    assert res.status_code == 200
    body = res.json()
    assert body["user_id"] == "alice"
    assert body["values"]["appearance.theme"] == "system"
    assert any(f["key"] == "notifications.email" for f in body["schema_fields"])

    update = client.put(
        "/api/preferences",
        json={
            "user_id": "alice",
            "values": {"appearance.theme": "dark", "workspace.autoSaveSeconds": 60},
        },
    )
    assert update.status_code == 200
    assert update.json()["values"]["appearance.theme"] == "dark"

    bad = client.put(
        "/api/preferences",
        json={"user_id": "alice", "values": {"appearance.theme": "neon"}},
    )
    assert bad.status_code == 422


def test_theme_layout_reset_import_api(client: TestClient) -> None:
    theme = client.get("/api/preferences/theme")
    assert theme.status_code == 200
    assert theme.json()["passes"] is True

    bad_theme = client.put(
        "/api/preferences/theme",
        json={
            "tokens": {
                "surface": "#FFFFFF",
                "surfaceMuted": "#FFFFFF",
                "textPrimary": "#FFFFFF",
                "textMuted": "#FFFFFF",
                "accent": "#FFFFFF",
                "accentText": "#FFFFFF",
                "danger": "#FFFFFF",
            }
        },
    )
    assert bad_theme.status_code == 422

    layout = client.put(
        "/api/preferences/layout",
        json={
            "user_id": "alice",
            "density": "compact",
            "sidebar_position": "right",
            "timezone": "UTC",
            "date_format": "MM/DD/YYYY",
            "show_activity": False,
        },
    )
    assert layout.status_code == 200
    assert layout.json()["density"] == "compact"

    exported = client.get("/api/preferences/import", params={"user_id": "alice"})
    assert exported.status_code == 200
    config = exported.json()
    assert config["layout"]["sidebar_position"] == "right"

    imported = client.post(
        "/api/preferences/import",
        json={"user_id": "bob", "config": config},
    )
    assert imported.status_code == 200
    assert imported.json()["user_id"] == "bob"
    assert imported.json()["layout"]["density"] == "compact"

    reset = client.post("/api/preferences/reset", json={"user_id": "bob"})
    assert reset.status_code == 200
    assert reset.json()["preferences"]["appearance.theme"] == "system"
    assert reset.json()["layout"]["density"] == "comfortable"
