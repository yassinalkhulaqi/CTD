# v3 Settings & Preferences

## Overview
`dev/v3-13-settings-preferences` adds a vertical slice for user preferences, theme tokens, and workspace layout. The feature is self-contained under `src/ctf_team_dashboard/features/settings_preferences/` and `frontend/src/features/settings-preferences/`.

## Domain Rules
- **Preference schema**: keys are declared in code (`PREFERENCE_SCHEMA`) with type, default, label, description, choices/range. Unknown keys are rejected.
- **Type coercion/validation**: booleans accept bool/strings, integers enforce min/max, enums enforce allowed choices, strings must be non-empty.
- **Defaults merge**: effective preferences are defaults merged with validated overrides.
- **Theme tokens**: hex colors normalized to `#RRGGBB`. Required UI tokens are ensured. Contrast is evaluated for key pairs (`textPrimary/surface`, `textMuted/surface`, `accentText/accent`, `textPrimary/surfaceMuted`) using WCAG relative luminance/contrast ratio. Updates/imports fail if any pair is below AA 4.5:1.
- **Workspace layout**: supports density (`compact|comfortable`), sidebar position (`left|right`), `show_activity`, timezone validation, and supported date formats. Invalid values return validation errors.
- **Reset**: restores default preferences, default layout, and default theme tokens.
- **Import/export**: versioned config (`version=1`) validates preferences/theme/layout before applying.

## API
| Method | Path | Description |
|---|---|---|
| GET | `/api/preferences?user_id=` | Effective preferences, defaults, schema |
| PUT | `/api/preferences` | Validate/coerce and update preference overrides |
| GET | `/api/preferences/theme` | Theme tokens + contrast evaluation |
| PUT | `/api/preferences/theme` | Validate theme tokens and WCAG contrast |
| GET | `/api/preferences/layout?user_id=` | Get workspace layout |
| PUT | `/api/preferences/layout` | Update workspace layout |
| POST | `/api/preferences/reset` | Reset preferences/theme/layout to defaults |
| GET | `/api/preferences/import?user_id=` | Export config |
| POST | `/api/preferences/import` | Validate/import config |

Error behavior uses domain `ValidationError` for bad keys/types/contrast/layout/import payloads.

## Storage
Feature-owned SQLite tables:
- `v3_preferences(id, user_id, key, value_json, updated_at)` unique `(user_id,key)`
- `v3_theme_tokens(name, value)`
- `v3_layouts(user_id, density, sidebar_position, show_activity, timezone, date_format, updated_at)`

## Frontend UX
Route: `/preferences` (plugin id `preferences`, group `Settings`).

Sections:
- **Appearance**: theme/accent controls, theme swatch preview with AA pass/fail.
- **Workspace**: density segmented control, sidebar position, timezone select, date format, activity toggle, autosave/hints.
- **Notifications**: email/desktop toggles and digest frequency.
- **Import/Export**: JSON export download and JSON import.

UX states: loading skeletons, error banner/retry, save bar for unsaved changes, reset defaults, optimistic local draft with explicit save.

## Accessibility
- Form controls have labels/hints via shared UI primitives.
- Save/import status uses `role="status"`/`aria-live`.
- Error banner uses `role="alert"`.
- Segmented controls are keyboard-operable via shared component.
- Contrast preview reports AA status; backend enforces AA for theme updates/imports.

## Tests
Backend (`tests/test_v3_settings_preferences.py`): schema/default/coercion, key/type validation, contrast helpers, service update/reset/theme/layout/import/export, API CRUD/validation/reset/import/export.

Frontend: `logic.test.ts`, `api.test.ts`, `components.test.tsx`, `PreferencesPage.test.tsx` cover pure logic, API adapter calls, component interactions, and page render/save/reset/export flows.
