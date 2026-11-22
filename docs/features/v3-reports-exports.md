# Reports and exports (V3 feature 12)

The report studio turns dashboard data into shareable documents. An author
picks a template, tunes its sections, previews the rendered result and exports
a final report as Markdown, CSV, JSON or standalone HTML. The feature is
self-contained: the backend package is discovered by the platform kernel and
the React module is discovered by the plugin registry, so no shared registry or
router file was changed.

## Scope

| Item | Value |
| --- | --- |
| Backend package | `src/ctf_team_dashboard/features/reports_exports/` |
| API prefix | `/api/reports` |
| Frontend module | `frontend/src/features/reports-exports/` |
| Plugin id / route | `reports` / `/reports` |
| Plugin group | Analysis |
| Tables | `v3_report_templates`, `v3_reports`, `v3_exports` |
| Test modules | `tests/test_v3_reports_exports.py`, colocated Vitest suites |

## Domain model

### ReportTemplate

A template is a named, ordered list of sections plus a default export format
and an audience scope (`team`, `event` or `global`). Sections are stored as a
single JSON document in `sections_json`; parsing is defensive, so malformed or
partial JSON yields an empty or reduced section list instead of a 500.

A section has the following fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Stable key used by the editor and renderer. |
| `title` | string | Heading; may contain placeholders. |
| `kind` | enum | `text`, `table`, `list` or `metrics`. |
| `body` | string | Prose, also placeholder-aware. |
| `source` | string | Key in the data snapshot that supplies records. |
| `columns` | string list | Column order for table sections; inferred when empty. |
| `enabled` | boolean | Disabled sections are skipped during rendering. |
| `order` | integer | Display order; normalised to `0..n-1` on save. |

### Report

A report is created from a template for a concrete `scope_id`. It starts as a
`draft` and can be moved to `final` exactly once. The service captures a data
snapshot at creation time so a finished report stays reproducible even when
the underlying challenge data changes later. When no explicit snapshot is
supplied, the service derives one from the dashboard's teams, challenges,
members and solves.

The snapshot is stored in `data_json`, an additive column on `v3_reports` that
keeps rendering deterministic without a fourth table. Snapshot keys that hold
collections or numbers are surfaced in the generated **summary counts** table.

### ExportJob

Every export is an immutable record of the rendered content together with the
format, status, byte size and timestamp. Jobs are created in the `complete`
state because rendering is synchronous; `pending` and `failed` remain part of
the status vocabulary for future asynchronous delivery.

## Rendering rules

* **Placeholder substitution** — `{{ key }}` resolves a dotted path in the
  snapshot. `{{ key || fallback }}` uses the fallback when the key is missing,
  `null` or empty. Lists become comma-separated strings, mappings become
  compact JSON and booleans render as `yes`/`no`. Unresolved tokens are
  reported as warnings and shown in the preview; they never break rendering.
* **CSV escaping** — a cell is quoted when it contains a comma, quote, CR or
  LF. Embedded quotes are doubled. Exports use `\n` line endings for stable
  tests and predictable diffs.
* **JSON pretty printing** — payloads are emitted with two-space indentation,
  sorted keys and non-ASCII characters preserved.
* **HTML escaping** — all user-derived strings pass through `html.escape` with
  quotes escaped. The generated document is standalone, includes a small
  inline print stylesheet and contains no external assets or scripts.
* **Markdown tables** — pipes and backslashes are escaped, newlines collapse to
  spaces and a delimiter row is always emitted for table sections.
* **Summary counts** — lists, tuples, sets and mappings contribute their
  length; integers and floats contribute their integer value; booleans and
  plain strings are ignored.

The same structured `RenderedReport` feeds both the preview endpoint and the
four writers, so the browser preview and the downloaded artefact cannot drift.

## Workflow rules

1. A template needs a non-empty name and at least one section.
2. A maximum of 40 sections, 96-character names and 8,000-character bodies
   keeps stored templates bounded.
3. Section identifiers must be unique; duplicate values are rejected with a
   domain `ValidationError`.
4. Reports require a title and a scope, and snapshots are capped at 200 keys.
5. Only draft reports accept snapshot updates.
6. Only final reports can be exported; attempting to export a draft raises
   `ConflictError` with HTTP 409.
7. Finalising an already final report is a conflict, not a silent no-op.
8. Missing templates, reports or jobs raise `NotFoundError` with HTTP 404.

All domain errors use the shared dashboard error envelope:

```json
{"error": {"code": "conflict", "message": "Finalise the report before exporting it"}}
```

## API

| Method | Path | Purpose | Success |
| --- | --- | --- | --- |
| `GET` | `/api/reports/templates` | List templates, newest first. | 200 |
| `POST` | `/api/reports/templates` | Create a template from sections. | 201 |
| `GET` | `/api/reports` | List reports; filters `status`, `limit`. | 200 |
| `POST` | `/api/reports` | Create a draft report and capture data. | 201 |
| `GET` | `/api/reports/{id}` | Read one report and its snapshot. | 200 |
| `PATCH` | `/api/reports/{id}/data` | Replace the snapshot of a draft. | 200 |
| `POST` | `/api/reports/{id}/finalise` | Finalise a draft report. | 200 |
| `POST` | `/api/reports/{id}/export` | Export with `{"format": "csv"}`. | 201 |
| `GET` | `/api/reports/{id}/preview` | Render without persisting; optional `format`. | 200 |
| `GET` | `/api/reports/exports` | List recent export jobs. | 200 |
| `GET` | `/api/reports/stats` | Studio counters and format breakdown. | 200 |

Static routes (`templates`, `exports`, `stats`) are declared before the
`/{report_id}` route so they are never captured as identifiers. Query limits
are validated between 1 and 500; invalid enum values produce HTTP 422.

Example request:

```bash
curl -X POST http://localhost:8000/api/reports \
  -H 'Content-Type: application/json' \
  -d '{"template_id":"tpl_123","title":"Round 12","scope_id":"redscribe","data":{"score":900}}'
```

## Frontend walkthrough

The `/reports` page is available from the **Analysis** group in the module
launcher. Its layout is a two-column studio:

1. **TemplatePicker** — select a saved template. Changing the selection loads
   its sections into the builder and resets the live report title to the
   template name. An empty state explains how to create the first template via
   the API or a seeded installation.
2. **ReportBuilder** — edit the report title and scope, then toggle sections,
   move them up or down, rename them, change their kind, edit their body and
   choose the data source. Add buttons create `text`, `table`, `list` and
   `metrics` sections with sensible defaults.
3. **ReportPreview** — renders the current draft with the selected format.
   Tables are real DOM tables, lists are semantic lists, metrics are labelled
   pairs and summary counts appear above the sections. Warnings for unresolved
   placeholders are visible inline.
4. **ExportMenu** — a popover with Markdown, CSV, JSON and HTML entries. It is
   disabled until a report is selected and finalised, and exposes the MIME type
   and file extension for each format.
5. **ReportList** — a compact table of existing reports with status badges,
   template names, scopes and creation dates. Selecting a row loads that
   report and its snapshot back into the studio.

The page shows loading skeletons while the catalogue is fetched, a retryable
error state when the API fails, an empty state when no templates exist and a
success banner after a finalisation or export. Format switching is instant and
does not create an export job; only the export menu writes to the server.

A dedicated `ReportsPage.print.module.css` module hides the studio chrome and
tightens the preview typography under `@media print`, so the browser print
dialog produces a clean document in addition to the HTML export.

## Accessibility

* Every editor control is a labelled native input, select or checkbox from the
  shared design system; icon buttons carry explicit accessible labels.
* Section reordering is keyboard operable via focusable buttons rather than a
  drag-only interaction.
* The export menu follows the popover pattern: it closes on Escape and outside
  clicks, and each entry is a real menu item.
* Format tabs use the shared segmented control with an accessible group label.
* Warnings use `role="status"`/`role="alert"` semantics from the feedback
  primitives and are announced without stealing focus.
* Focus-visible rings, hover states and reduced-motion rules are defined in the
  feature's own CSS modules; theme colours come from shared custom properties.
* Print styles keep headings with their following content and avoid splitting
  table rows across pages.

## Testing notes

Backend coverage (41 tests) is grouped into domain helpers, escaping and export
writers, repository round trips, service workflow and HTTP integration. The
HTTP tests exercise every route, the 201/200/404/409/422 status codes, the
error envelope, filter combinations and the static-before-dynamic route order.
The suite uses the shared `settings`, `database`, `seeded` and `client`
fixtures; no shared fixture was modified.

Frontend coverage lives beside the feature in `reportModel.test.ts`,
`api.test.ts` and component interaction suites. Pure model tests cover
reordering, placeholder resolution and validation; adapter tests assert every
URL and payload; rendered tests exercise section toggles, export selection,
template choice, report selection and the full page flow with mocked hooks.

## Design trade-offs

* The snapshot is captured per report rather than derived at render time so an
  export is reproducible and a final report cannot silently change.
* Rendering is synchronous and stores the full content. This trades storage for
  a simple audit trail: previous exports can be listed and inspected.
* Section configuration is stored as JSON instead of a normalized table. A
  report template is always edited as one unit, so a single document avoids
  expensive joins and keeps ordering explicit.
* HTML is escaped at the writer boundary rather than trusted from the editor,
  so a malicious snapshot cannot inject markup into exported documents.
