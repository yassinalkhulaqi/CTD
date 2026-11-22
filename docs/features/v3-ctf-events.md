# V3 CTF Events

The events module adds a complete competition lifecycle to the CTF Team
Dashboard: authoring events, deriving their live state from the clock,
registering teams with capacity and a waitlist, tracking a preparation
checklist and exposing the figures that drive the operations screen.

Branch: `dev/v3-05-ctf-events` · baseline: `448fe50` · module id: `events`.

## 1. Overview

Events are the calendar spine of the dashboard. Other modules (roster,
submissions, scoreboards) can relate their records to an event, so this module
owns only the lifecycle and registration concerns and keeps its tables and
routes self-contained. The backend lives in
`src/ctf_team_dashboard/features/ctf_events/`; the React screen lives in
`frontend/src/features/ctf-events/`.

The module follows the V3 contract: the backend package exports `SCHEMA_SQL`
and `register(app)`, the frontend directory exports `plugin` from `plugin.ts`,
and the dynamic registries discover both without any shared file edits.

### Deliverables

| Layer | What ships |
| --- | --- |
| Domain | `CtfEvent`, `EventRegistration`, `EventTask`, `EventStats`, `EventOverlap`, enums and pure helpers |
| Store | CRUD and filtered SQL queries over three tables with atomic slot reservation and promotion |
| Service | Validation, lifecycle queries, capacity rules, overlap checks, aggregation |
| API | Sixteen typed endpoints under `/api/events` |
| UI | `/events` page with cards, countdown rings, dialog, drawer, filters and stats strip |
| Tests | 19 backend tests, 23 frontend tests |
| Docs | This document |

## 2. Data model

### `v3_events`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `TEXT PRIMARY KEY` | Generated as `event-<12 hex chars>` |
| `name` | `TEXT NOT NULL` | 3–120 characters after whitespace normalisation |
| `slug` | `TEXT NOT NULL UNIQUE` | Slugified name with `-2`, `-3`… suffixes on collision |
| `description` | `TEXT NOT NULL` | Up to 4,000 characters |
| `format` | `TEXT NOT NULL` | `jeopardy` or `attack_defence` |
| `starts_at`, `ends_at` | `TEXT NOT NULL` | Timezone-aware ISO-8601 strings |
| `status` | `TEXT NOT NULL` | Only `draft`, `upcoming` or `archived` are stored |
| `max_team_size` | `INTEGER NOT NULL` | Confirmed-slot capacity (1–64) |
| `registration_open` | `INTEGER NOT NULL` | Organiser switch |
| `website_url` | `TEXT NOT NULL` | Optional `http(s)` URL |
| `tags` | `TEXT NOT NULL` | Compact JSON array |
| `created_at` | `TEXT NOT NULL` | Creation instant |

Indexes cover the `(starts_at, ends_at)` window, the stored status and the
slug. A partial unique index on `(event_id, team_id)` prevents two active
registrations for the same team while allowing a cancelled team to re-register.

### `v3_event_registrations`

`id`, `event_id`, `team_id`, `status` (`confirmed`, `waitlisted`, `cancelled`),
`registered_at` and an internal `promoted_at` audit timestamp. The audit column
makes the `promotions` statistic real rather than inferred: it is set only when
the waitlist promotion transaction runs.

### `v3_event_tasks`

`id`, `event_id`, `title`, `done` and an optional `due_at`. Tasks are ordered
incomplete-first in the UI, with due date and identifier as tie-breakers.

## 3. Domain rules

### Status derivation

`draft` and `archived` are explicit organiser decisions and are returned
verbatim. Every other event is **upcoming** before `starts_at`, **live** from
`starts_at` (inclusive) to `ends_at` (exclusive) and **archived** from
`ends_at` onward. The pure function `derive_event_status` is used by the model,
the API serialisers and the frontend utility of the same name so every layer
agrees on the effective state.

Clients cannot set `status=live`; both the Pydantic schema and the service
reject it. To finish an event early an organiser patches it to `archived`.

### Slugs

`slugify` transliterates accents to ASCII, lowercases the value, collapses
runs of non-alphanumeric characters into a single hyphen and falls back to
`event` for an empty result. `EventService.unique_slug` checks existing slugs
and appends a numeric suffix. Renaming an event regenerates the slug unless an
explicit one is supplied.

### Countdowns

`CtfEvent.countdown_seconds(now)` returns seconds until the start for upcoming
events, seconds until the end for live events and zero otherwise.
`format_countdown` renders days/hours, hours/minutes or minutes/seconds. The
frontend mirrors both calculations in `utils.ts` so the ring can tick locally
between API reads, while the API also returns the derived values for clients
that do not need a per-second update.

### Capacity, waitlist and promotion

`RegistrationStore.reserve_slot` counts confirmed rows and inserts the new
registration inside a single `BEGIN IMMEDIATE` transaction. Fewer confirmed
teams than capacity means `confirmed`; otherwise the team is `waitlisted`.
Cancelling a confirmed registration marks it `cancelled` and calls
`promote_next`, which atomically selects the oldest waitlisted row (by
`registered_at`, then `id`), confirms it and stamps `promoted_at`. Cancelling a
waitlist place never promotes anybody. A team may re-register after cancelling
because the partial unique index ignores cancelled rows.

### Overlap detection

`intervals_overlap` treats intervals as half-open: an event ending at 12:00 and
another starting at 12:00 do not clash. When a team registers, the service
walks its confirmed registrations and raises `ConflictError` if any live event
shares competition time with the target event. `GET /api/events/overlaps`
reports the same clashes for a team as a list of pairs with the overlap length
in seconds.

### Statistics

`EventStats` reports `confirmed`, `waitlisted`, `cancelled`, `capacity`,
`promotions`, `available_slots`, `is_full`, `capacity_ratio`,
`fill_percentage` (clamped to 100) and `waitlist_pressure`. The aggregate strip
on the page sums confirmed and waitlisted teams and computes the overall fill
rate across the events in view.

## 4. API

All routes are registered with `APIRouter(prefix="/api/events", tags=["events"])`.
Static routes are declared before `/{event_id}` so `upcoming` is never parsed
as an identifier.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/events` | Filtered catalogue (`status`, `format`, `tag`, `search`, `registration_open`, `window`, `limit`) |
| `POST` | `/api/events` | Create an event; returns 201 |
| `GET` | `/api/events/upcoming` | Events whose window has not opened |
| `GET` | `/api/events/live` | Events currently in progress |
| `GET` | `/api/events/stats` | Statistics for every event |
| `GET` | `/api/events/overlaps?team_id=…` | Live clashes for a team |
| `GET` | `/api/events/{id}` | One event with derived countdown fields |
| `PATCH` | `/api/events/{id}` | Partial edit, including archiving |
| `DELETE` | `/api/events/{id}` | Remove the event and its registrations/tasks |
| `POST` | `/api/events/{id}/register` | Register `{team_id}`; 201 with confirmed or waitlisted state |
| `POST` | `/api/events/{id}/cancel` | Cancel `{team_id}`; response includes the promoted team |
| `GET` | `/api/events/{id}/registrations` | Registration ledger and headline counts |
| `GET` | `/api/events/{id}/stats` | Registration figures for one event |
| `GET` | `/api/events/{id}/tasks` | Checklist items |
| `POST` | `/api/events/{id}/tasks` | Add a checklist item; returns 201 |
| `POST` | `/api/events/{id}/tasks/{task_id}/toggle` | Flip a checklist item |

Errors use the dashboard envelope: `ValidationError` maps to 422 (empty name,
end before start, forced `live`, bad URL), `NotFoundError` to 404 and
`ConflictError` to 409 (duplicate registration, closed registration, live
overlap, already cancelled).

### Example registration flow

```json
POST /api/events/event-abc/register
{ "team_id": "team-1" }
```

```json
{
  "id": "reg-9f2c1ad4e810",
  "event_id": "event-abc",
  "team_id": "team-1",
  "status": "waitlisted",
  "registered_at": "2026-06-01T10:00:00+00:00",
  "is_confirmed": false,
  "is_waitlisted": true
}
```

## 5. Frontend walkthrough

The plugin declares `{ id: "events", label: "Events", path: "/events",
group: "Operations" }`. The launcher picks it up automatically.

1. The page header offers a manual refresh. A `useNow(1000)` hook drives every
   countdown ring so all cards advance in sync without re-rendering the API
   data.
2. The statistics strip shows events, confirmed teams, waitlisted teams and
   the aggregate fill rate.
3. The filter bar has status windows (All, Upcoming, Live, Archived) with
   counts, a search field and a format selector. Any change refetches the
   catalogue with an abortable request.
4. Event cards show a status pill, format, description, tags, a capacity bar
   and a gradient countdown ring. The Register button is disabled when
   registration is closed or the event has archived.
5. Choosing **Register** opens an accessible modal with a team selector. The
   confirmation posts to the API; success produces a polite status message and
   refreshes the catalogue. Errors appear inside the dialog.
6. **Details** opens a right-hand drawer with the competition window, capacity,
   website, tags, a task checklist and the registration ledger. Checklist
   updates are optimistic and revert on failure.

Loading uses skeleton cards, the empty state offers a filter reset and API
failures expose a retry action.

### Components

| Component | Responsibility |
| --- | --- |
| `EventCard` | Present one event and its primary actions |
| `CountdownRing` | SVG gradient arc with a ticking, accessible timer |
| `RegistrationDialog` | Team selection and registration submission |
| `EventDetail` | Drawer with checklist, ledger and metadata |
| `EventFilters` | Status, search and format controls |
| `EventStatsView` | Aggregate statistics strip |

## 6. Styling and accessibility

Each component has a colocated CSS module. Gradient accents use the existing
design tokens, the card grid is responsive via `auto-fill` and collapses to a
single column on narrow screens, and every transition is disabled under
`prefers-reduced-motion: reduce`.

The dialog and drawer use the shared overlay primitives, which provide a focus
trap, Escape handling, backdrop dismissal and focus restoration. Inputs are
labelled (visually hidden where the design calls for it), filter buttons expose
`aria-pressed`, the timer exposes `role="timer"` with a text label, checkboxes
use their task title as the label, and status messages use `role="status"`
while failures use `role="alert"`.

## 7. Testing notes

Backend (`tests/test_v3_ctf_events.py`, 19 tests) covers pure calculations
(status derivation, slug and tag normalisation, countdown formatting, overlap
helpers), service validation, slug collisions, store filtering, capacity and
waitlist behaviour, cancellation promotion, live overlap conflicts, statistics
and the checklist, plus router success and error paths.

Frontend tests are colocated:

* `utils.test.ts` — status derivation, countdown formatting, ring progress and
  aggregates (9 tests).
* `api.test.ts` — query encoding, typed parsing, request bodies and endpoints
  (7 tests).
* `EventsPage.test.tsx` — rendered card, registration interaction, filter
  control and detail drawer (4 tests).
* `components/CountdownRing.test.tsx` — accessible timer, tick updates and the
  live variant (3 tests).

Both suites use isolated databases and mocked HTTP adapters; no test depends
on wall-clock time or a live server.

## 8. Verification

```bash
python3 -m ruff check . && python3 -m ruff format --check .
python3 -m mypy
python3 -m pytest -q
(cd frontend && npm run lint && npm run format:check && npm run typecheck && npm test && npm run build)
python3 scripts/loc_gate.py 448fe50 HEAD --min 2000
```

The LOC gate compares the branch against the integration baseline and ignores
generated output, dependency trees and caches.
