# V3 Advanced Data Visualisations

## Overview

The data visualisation vertical slice adds persisted chart specifications, observation ingestion,
server-computed SVG geometry and a responsive gallery UI to the CTF Team Dashboard. It supports five
chart types: bar, line, radar, Sankey and sparkline. Geometry is computed once on the backend from a
pure model layer, returned as a typed payload, and rendered by small React components with no
charting dependency.

## Scope

All feature code is isolated to these paths:

- `src/ctf_team_dashboard/features/data_visualization/`
- `tests/test_v3_data_visualization.py`
- `docs/features/v3-data-visualization.md`
- `frontend/src/features/data-visualization/`

No shared application files, route tables, schemas, package manifests or global CSS were modified.
The backend self-registers through `SCHEMA_SQL` and `register(app)`. The frontend exports a
`FeaturePlugin` that the existing `import.meta.glob("./*/plugin.ts")` loader discovers at runtime.

## Backend architecture

### Data model

`SCHEMA_SQL` creates two tables with idempotent statements and supporting indexes:

- `v3_charts`: `id`, `team_id`, `title`, `chart_type`, `series_json`, `options_json`, `palette`,
  `created_at`, `updated_at`.
- `v3_chart_data`: `id`, `chart_id`, `label`, `value`, `category`, `position`; rows cascade when a
  chart is deleted.

`series_json` stores the canonical inline series payload. `options_json` stores canonical chart
options such as scale, sort, direction, tick count and dimensions. Ingested observations live in
`v3_chart_data` so they can be replaced atomically without rewriting the specification.

### Layers

- `models.py`: enums, defaults, palette catalogue, domain dataclasses, `ChartPayload` parsing,
  `ChartOptions` parsing, `GeometryBuilder` and pure maths for aggregation, sorting, limiting,
  radar projection and Sankey layout.
- `store.py`: `ChartSpecRepository`, `ChartDataRepository` and `VisualizationStore`. All SQL uses
  `BaseRepository` helpers, parameter binding and explicit ordering.
- `service.py`: `VisualizationService` validates text, payloads, options, palettes, identifiers and
  point batches. It raises `ValidationError`, `NotFoundError` or `ConflictError` with structured
  details.
- `schemas.py`: typed Pydantic request/response models plus `geometry_overrides` for query
  parameter validation.
- `router.py`: `APIRouter(prefix="/api/visualizations", tags=["visualizations"])`.
- `__init__.py`: schema SQL and `register(app)`.

### Geometry pipeline

`VisualizationService.geometry(chart_id, overrides)` merges stored options with request overrides,
loads inline and ingested observations, applies sorting and limiting, then builds a `ChartGeometry`
payload. The payload contains ticks, positioned bars, projected line series, radar axes and shapes,
normalised Sankey nodes and flows, sparkline paths, legend entries, table rows and mark counts.
`padding` is part of the geometry so the UI and API agree on the SVG viewport.

`aggregate_by_category` supports `sum`, `avg`, `max`, `min` and `count`, with deterministic sorting
by value then category and palette-derived colours.

### HTTP API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/visualizations` | List specifications with `team_id`, `chart_type`, `limit`, `offset` filters. |
| `POST` | `/api/visualizations` | Create a specification. |
| `GET` | `/api/visualizations/palettes` | List categorical palettes with light and dark colours. |
| `GET` | `/api/visualizations/{chart_id}` | Read one specification with point count. |
| `PUT` | `/api/visualizations/{chart_id}` | Update mutable specification fields. |
| `POST` | `/api/visualizations/{chart_id}/data` | Ingest or replace a batch of observations. |
| `GET` | `/api/visualizations/{chart_id}/data` | Read stored observations. |
| `GET` | `/api/visualizations/{chart_id}/geometry` | Compute SVG geometry with query overrides. |
| `GET` | `/api/visualizations/{chart_id}/aggregate` | Reduce observations by category. |

The static `/palettes` route is declared before `/{chart_id}` so it cannot be captured as an
identifier. Geometry and aggregate query values are constrained with FastAPI `Query` bounds.
Chart identifiers are URL-encoded by the frontend client.

## Frontend architecture

### Files

- `types.ts`: exhaustive types for API payloads, geometry marks, aggregate rows and query objects.
- `geometry.ts`: pure helpers for tick calculation, palette selection, inline series parsing,
  sparkline paths, radar polygons, Sankey curves and optimistic aggregation.
- `api.ts`: typed adapter over the shared `get`, `post`, `put` and `buildQuery` helpers.
- `samples.ts`: deterministic sample series, specifications and switcher metadata.
- `hooks.ts`: `useInterfaceTheme()` observes `data-theme`; `useVisualizations(theme)` loads specs,
  palettes, geometry and aggregates, and exposes `select`, `setViewMode`, `refresh`, `create`,
  `createSamples`, `update` and `ingest`.
- `plugin.ts`: exports the `FeaturePlugin` for `/visualizations`.
- `VisualizationsPage.tsx`: header, gallery, detail card, type switcher, view switcher, ingest
  action, aggregate summary, loading/empty/error states.
- `components/`: `ChartCard`, `ChartTooltip`, `ChartLegend`, `BarChart`, `LineChart`, `RadarChart`,
  `SankeyDiagram` and `Sparkline`, each with a local CSS module.

### Rendering model

Every renderer accepts the same `ChartGeometry` payload. The chart type switcher updates the stored
specification through `PUT`, which triggers a refresh and new geometry. The view switcher toggles
between the SVG renderer and an accessible `Table` fallback built from `geometry.data`. Focusable
marks use `tabIndex=0` and `aria-label`, and reveal a shared tooltip on focus or hover. Legends are
labelled lists with colour swatches.

All colours come from palette descriptors and the active interface theme. Layout uses CSS custom
properties from the global theme tokens, with a two-column gallery/detail layout that collapses to
a single column at 960px and stacks actions at 600px. `prefers-reduced-motion` disables smooth
gallery scrolling.

### Accessibility

- Chart SVGs expose `role="img"` and descriptive `aria-label` values.
- Bars, line points and Sankey flows are keyboard focusable and expose value tooltips.
- Legend swatches are `aria-hidden` so they do not pollute accessible names.
- Empty, loading and error states use existing design-system primitives with explicit retry
  actions.
- The data table provides a non-visual alternative with labelled columns and right-aligned values.

## Testing

Backend (`tests/test_v3_data_visualization.py`) covers domain parsing and geometry maths, palettes,
aggregations, repository CRUD and replacement semantics, service validation and errors, and every
HTTP endpoint including query validation.

Frontend tests cover:

- exact sparkline, radar and Sankey SVG path generation (`geometry.test.ts`);
- tick generation, palette cycling, series parsing and aggregation (`geometry.test.ts`);
- typed API paths, URL encoding and query serialisation (`api.test.ts`);
- renderer output, focusable marks and tooltips (`components.test.tsx`);
- page loading, empty, error, gallery, type switching, ingest and table fallback states
  (`VisualizationsPage.test.tsx`).

## Verification

From the worktree root:

```bash
python3 -m ruff check .
python3 -m ruff format --check .
python3 -m mypy
PYTHONPATH=src python3 -m pytest -q
cd frontend && npm run lint && npm run format:check && npm run typecheck && npm test && npm run build
cd .. && python3 scripts/loc_gate.py 448fe50 HEAD --min 2000
```

The LOC gate compares the committed branch against the `448fe50` baseline, so it must be run after
the feature commit.

## Notes

- Geometry is deterministic for a given specification, options set, palette, theme and request
  override set.
- Inline series are read from `series_json`; ingested observations are read from `v3_chart_data`;
  the service merges both sources before projection.
- Sankey charts additionally read `links` from the inline payload; the sample specification seeds
  four deterministic links.
- No secrets, raw SQL strings outside the repository layer, or untyped public interfaces are
  introduced by this feature.
