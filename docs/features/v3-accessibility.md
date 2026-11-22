# V3 Accessibility Toolkit

The accessibility feature adds a self-contained workspace for finding, recording and
rehearsing interface accessibility work. It lives entirely under
`src/ctf_team_dashboard/features/accessibility/` on the backend and under
`frontend/src/features/accessibility/` on the frontend. Both sides are discovered
dynamically, so no shared registry files are changed.

## Goals

- Provide deterministic WCAG colour-contrast calculations that can be reused by the UI.
- Store accessibility issues, keyboard shortcuts and focus orders in dedicated tables.
- Detect shortcut collisions before they are persisted.
- Model focus traversal as a wrapping state machine with a single active stop.
- Expose a page-scoped accessibility workspace without changing the global theme.
- Offer pure helpers that are easy to unit test in both Python and TypeScript.

## Backend

### Package layout

| File | Responsibility |
| --- | --- |
| `__init__.py` | Declares `SCHEMA_SQL` and the FastAPI `register(app)` entry point. |
| `models.py` | Enums, dataclasses and pure domain algorithms. |
| `store.py` | Repository classes over the three `v3_a11y_*` tables. |
| `service.py` | Orchestration, validation and cross-entity queries. |
| `schemas.py` | Pydantic request and response models. |
| `router.py` | HTTP routes mounted at `/api/accessibility`. |
| `py.typed` | Marks the package as typed for downstream consumers. |

### Persistence

`SCHEMA_SQL` creates three tables:

- `v3_a11y_issues`: one row per issue, including severity, path, rule, description,
  suggestion and resolution timestamps.
- `v3_shortcuts`: one row per key binding, with canonical keys, display keys, action,
  scope and derived flags.
- `v3_focus_orders`: one row per focus stop, with label, order and suggested ARIA label.

Every statement in `store.py` is parameterised. Repositories derive their table names
from constants and use the shared `BaseRepository` helpers, so no raw string
interpolation of user input reaches SQLite.

### Domain behaviour

`models.py` keeps calculations separate from persistence:

- `parse_color` accepts hex colours, `rgb()` expressions and a small set of named
  colours, returning an `(r, g, b)` tuple.
- `relative_luminance` applies the WCAG linearisation curve.
- `contrast_ratio` returns a ratio rounded to two decimal places.
- `classify_contrast` applies `4.5:1` / `7:1` thresholds to body text and `3:1` /
  `4.5:1` to large text.
- `suggest_contrast_fix` explains how to repair a failing pair.
- `parse_shortcut` canonicalises modifier order and supports two-step chords.
- `find_shortcut_conflicts` treats identical bindings as conflicts when either scope
  is global or when both scopes match exactly.
- `create_focus_trap`, `move_focus` and `focus_at` implement a wrapping focus model.
- `suggest_aria_label` upgrades generic labels such as "Submit" into descriptive text.

### Service layer

`AccessibilityService` owns the workflow:

- `record_issue`, `list_issues`, `get_issue` and `resolve_issue`.
- `audit_contrast` evaluates one or more pairs and optionally records failures.
- `register_shortcut`, `list_shortcuts`, `delete_shortcut` and `shortcut_conflicts`.
- `add_focus_entry`, `list_focus_entries`, `delete_focus_entry`, `reorder_focus_entries`
  and `focus_trap`.
- `aria_suggestion` and `stats`.

The service returns dataclass snapshots, which `schemas.py` converts into stable JSON
objects. Unknown identifiers raise lookup errors that the router maps to `404`.

### HTTP API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/accessibility/issues` | List issues with optional filters. |
| `POST` | `/api/accessibility/issues` | Record a new issue. |
| `POST` | `/api/accessibility/issues/{id}/resolve` | Mark an issue resolved. |
| `GET` | `/api/accessibility/shortcuts` | List shortcut bindings. |
| `POST` | `/api/accessibility/shortcuts` | Register a binding after conflict checks. |
| `DELETE` | `/api/accessibility/shortcuts/{id}` | Remove a binding. |
| `GET` | `/api/accessibility/shortcuts/conflicts` | List existing conflicts. |
| `POST` | `/api/accessibility/contrast` | Audit one contrast pair. |
| `GET` | `/api/accessibility/focus-orders` | List focus stops. |
| `POST` | `/api/accessibility/focus-orders` | Add a focus stop. |
| `POST` | `/api/accessibility/focus-orders/reorder` | Persist a new focus sequence. |
| `GET` | `/api/accessibility/focus-trap` | Snapshot the trap at an index. |
| `POST` | `/api/accessibility/aria-suggestions` | Suggest an accessible label. |
| `GET` | `/api/accessibility/stats` | Summarise counts, rates and risk. |

## Frontend

### Discovery

`plugin.ts` exports a `FeaturePlugin` with:

- `id: "accessibility"`
- `label: "Accessibility"`
- `path: "/accessibility"`
- `group: "Settings"`
- `component: AccessibilityPage`

The shared `import.meta.glob("./*/plugin.ts", { eager: true })` discovery in
`frontend/src/features/plugins.ts` mounts the route and adds the module to the launcher
automatically.

### File responsibilities

| File | Responsibility |
| --- | --- |
| `types.ts` | Wire types, payloads, filters and shared constants. |
| `a11y.ts` | Pure TypeScript mirrors of the contrast, shortcut and focus algorithms. |
| `api.ts` | Typed wrapper around the shared API client. |
| `hooks.ts` | Snapshot loading and issue filter state. |
| `plugin.ts` | Feature plugin declaration. |
| `AccessibilityPage.tsx` | Page composition and action handlers. |
| `components/ContrastChecker.tsx` | Live preview, evaluation and audit submission. |
| `components/ShortcutEditor.tsx` | Binding form, conflict preview and removal. |
| `components/IssueList.tsx` | Severity filtering, search and resolution. |
| `components/FocusOrderMap.tsx` | Roving tabindex visualisation and reorder controls. |
| `components/MotionControls.tsx` | Page-scoped reduced-motion and high-contrast toggles. |
| `components/SkipLinkDemo.tsx` | Focusable skip link that targets the main region. |

Every component has a co-located CSS module. The page root sets
`data-reduced-motion` and `data-high-contrast` attributes; CSS selectors under
`.page[data-reduced-motion="true"]` and `.page[data-high-contrast="true"]` scope all
visual changes to this route. The application theme is never mutated.

### Interaction notes

- The skip link is visually hidden until focused and points at
  `#a11y-main-content`, a `tabIndex={-1}` main landmark.
- The contrast checker evaluates input locally before any network request.
- The shortcut editor computes a draft binding and blocks submission when a
  conflict is detected.
- The focus map exposes only the active stop in the tab order, matching the roving
  tabindex pattern, and announces the current stop through `aria-live`.
- The issue list sorts critical items first and can include resolved items on demand.

## Testing

Backend coverage lives in `tests/test_v3_accessibility.py`. It exercises pure helpers,
repository behaviour, service orchestration, conflict detection, focus traversal and
every API route.

Frontend coverage lives beside the feature:

- `a11y.test.ts` checks colour parsing, WCAG thresholds, shortcut canonicalisation,
  conflicts, sorting, filtering and label suggestions.
- `accessibility.test.tsx` checks the contrast form, conflict blocking, issue
  filtering and resolution, focus wrapping and preference toggles.
- `plugin.test.ts` verifies plugin metadata and dynamic discovery.

## Verification

```bash
python3 -m ruff check .
python3 -m ruff format --check .
python3 -m mypy
PYTHONPATH=src python3 -m pytest -q

cd frontend
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
cd ..

python3 scripts/loc_gate.py 448fe50 HEAD --min 2000
```

The feature must not edit shared registry, configuration or engine files. All changes
are confined to the two feature directories, the backend test file and this document.
