# V3 administration console

The administration console gives moderators and administrators one place to
triage reports, govern account access, review the audit trail and inspect
platform health. The backend is self-contained in
`src/ctf_team_dashboard/features/admin_console/` and the UI is discovered
automatically through `frontend/src/features/admin-console/plugin.ts`.

No shared router, registry, engine, package manifest or stylesheet was edited.
The backend package exports `SCHEMA_SQL` and `register(app)`; the frontend
exports a `FeaturePlugin` mounted at `/admin` in the `Settings` group.

## Domain model

### Moderation cases

A case captures a report with a target, reporter, type, priority and SLA. It is
a frozen slotted dataclass with derived properties for overdue state, terminal
state and SLA hours. Transitions are intentionally narrow:

| Current state | Allowed next states |
| --- | --- |
| `open` | `in_review`, `resolved`, `dismissed` |
| `in_review` | `resolved`, `dismissed` |
| `resolved` | none |
| `dismissed` | none |

Priority maps to a response deadline measured from creation:

| Priority | SLA |
| --- | --- |
| `low` | 72 hours |
| `normal` | 24 hours |
| `high` | 8 hours |
| `critical` | 2 hours |

Assignment moves an open case into `in_review` and writes an audit event.
Resolution and dismissal require non-empty text, close the case and store that
text on the case as well as in the immutable audit trail.

### Account controls

An account control pairs a user with a status, role, free-form flags and an
audit-friendly reason history. The service refuses to suspend the acting
operator or any account whose role is `admin`, including when the caller
attempts to pass a different actor in the request body; the actor always comes
from `require_role("admin")`. Activation removes the `suspended` flag while
preserving the remaining flags.

### Platform health

Each health snapshot records database availability, API latency, cache hit
ratio and queue depth. The score is a weighted percentage:

- database availability: 40%
- API latency: 25%, with 2000 ms scoring zero
- cache hit ratio: 20%
- queue depth: 15%, with 500 items scoring zero

The state is `healthy` at 85 or above, `degraded` from 60 to 84.9, and
`critical` below 60 or whenever the database is offline. The bottleneck is the
lowest-scoring component and is shown in the health card.

### Audit trail

Every case, account and health mutation appends an immutable action row with
actor, target type, target id, action kind, reason and timestamp. The audit API
supports filtering by actor, target type, target id, action, time window and
free text.

## Persistence

`SCHEMA_SQL` creates four tables with indexes:

| Table | Purpose |
| --- | --- |
| `v3_moderation_cases` | Case lifecycle, SLA, assignee and resolution |
| `v3_admin_actions` | Immutable audit events |
| `v3_account_controls` | Account status, role and flags |
| `v3_health_checks` | Health snapshots and computed scores |

All reads and writes use `BaseRepository` with parameterised SQL. Filters are
composed from typed dataclasses rather than accepting raw SQL fragments.

## HTTP API

All routes require the `admin` role. When authentication is disabled, the
shared dependency supplies the synthetic `anonymous` admin principal used by
the integration tests.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/admin/cases` | Filtered, sorted and paginated moderation queue |
| `POST` | `/api/admin/cases` | Open a case with an automatic SLA |
| `POST` | `/api/admin/cases/{id}/assign` | Assign a case and move it to review |
| `POST` | `/api/admin/cases/{id}/resolve` | Close a case with a resolution |
| `POST` | `/api/admin/cases/{id}/dismiss` | Close a case with a dismissal reason |
| `GET` | `/api/admin/account-controls` | List account controls |
| `POST` | `/api/admin/account-controls` | Suspend or activate an account |
| `GET` | `/api/admin/actions` | Filtered audit trail |
| `GET` | `/api/admin/health` | Recent health snapshots and latest value |
| `POST` | `/api/admin/health` | Record a health snapshot |
| `GET` | `/api/admin/stats` | Aggregated overview metrics |

Validation failures return `ValidationError` responses, missing entities return
`NotFoundError`, and illegal lifecycle transitions or protected suspension
attempts return `ConflictError`.

## UI walkthrough

The `/admin` page is composed of focused components:

- `AdminStats` renders six tiles for open reports, SLA breaches, resolution
  rate, suspensions, recent actions and health score.
- `ModerationQueue` provides status, priority, report type, sort, search,
  overdue and unassigned filters plus a case creation dialog.
- `CaseDetail` shows the selected case, SLA, assignee and resolution, and
  exposes assign, resolve and dismiss actions. Resolve and dismiss require a
  written explanation.
- `HealthGauge` renders the current score as an SVG ring, lists the four
  component metrics, previews a new score and records snapshots.
- `AuditTable` filters the action history and presents it in a sticky table.
- `AccountControls` summarises posture and allows reversible suspension with a
  required reason. Protected accounts are visibly disabled.

Case filters are sent to the backend. Audit filters are applied locally to the
loaded action page so changing the audit view never resets the moderation
queue. Mutations update local state immediately and refresh all server-backed
overview data while preserving the active case filter.

## Testing notes

Backend coverage in `tests/test_v3_admin_console.py` includes domain rules,
repository filtering, service guards, aggregation, HTTP success paths and HTTP
error paths using the shared `client`, `database` and `settings` fixtures.

Frontend coverage includes:

- pure logic for scoring, SLA formatting, case/action filters and account guards
- API adapter query mapping and route/payload construction
- rendered component interactions for queue filters, case resolution,
  protected suspension and health recording
- page-level rendering and case assignment

## Accessibility notes

- Every panel is a labelled `section`, and the data tables use sticky headers
  with column scopes.
- Icon-only affordances are paired with text or accessible labels.
- Case rows are real buttons with `aria-pressed`, so keyboard selection works.
- Form fields use the design system's label, hint and error wiring; error text
  is announced with `role="alert"`.
- Modals trap focus, close on Escape, restore prior focus and expose their
  title and description through the dialog.
- Loading skeletons set `aria-busy`, and empty states are exposed as status
  regions.
- Hover effects are suppressed and transitions removed under
  `prefers-reduced-motion`.
