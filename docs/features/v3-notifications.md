# V3 Notifications — notification centre, preferences, digests and toasts

## Overview

`dev/v3-10-notifications` adds a complete notification subsystem to the CTF
Team Dashboard. It is a vertical slice: three SQLite tables, an immutable
domain model with the delivery rules, repositories, an orchestration service,
a typed HTTP API, a routed React screen, component-level CSS modules, tests and
this document.

The feature follows the V3 branch contract. It only adds files under:

* `src/ctf_team_dashboard/features/notifications/`
* `tests/test_v3_notifications.py`
* `docs/features/v3-notifications.md`
* `frontend/src/features/notifications/`

The platform kernel discovers the backend package through `pkgutil` and the
frontend plugin through `import.meta.glob`; no shared registry is edited.

The user-facing goals are:

1. A single inbox that surfaces urgent events first and supports fast triage.
2. Per-channel, per-kind delivery preferences with quiet hours.
3. Digest previews that group events by kind and severity.
4. A toast queue for immediate feedback without blocking the workflow.

## Domain model

All domain values are frozen slotted dataclasses in `models.py`. Calculations
are pure functions, which keeps them cheap to test and independent of SQLite.

### `Notification`

| Field | Meaning |
| --- | --- |
| `id` | Stable identifier, generated as `ntf-<uuid4 hex>`. |
| `recipient_id` | Identifier of the team member or system account. |
| `channel` | `in_app`, `email` or `webhook`. |
| `kind` | `solve`, `challenge`, `team`, `system`, `security`, `*` (wildcard). |
| `title`, `body` | Rendered message content. |
| `severity` | `info`, `warning` or `critical`. |
| `read_at` | Acknowledgement timestamp, `None` while unread. |
| `created_at` | Creation timestamp as an aware UTC datetime. |
| `action_url` | Optional deep link rendered as an "Open" affordance. |

Derived properties: `is_read`, `is_unread`, `age_seconds`, `label`. `mark_read()`
returns a new instance rather than mutating the original. `sort_key()` orders by
descending severity rank, then descending creation time, then identifier;
`NotificationQuery.apply()` uses the same rule so the API and pure helpers
agree.

### `NotificationPreference`

The primary key is `(recipient_id, channel, kind)`. `enabled` gates delivery;
`quiet_start_hour` and `quiet_end_hour` describe an hour-of-day window in UTC.
Hours must be integers between 0 and 23; invalid values raise `ValidationError`.
`QuietHours.contains()` supports windows that wrap past midnight, and
`QuietHours.next_open_hour()` reports when delivery resumes. Equal start and
end hours mean the window is disabled.

`lookup_preference()` resolves the most specific rule:

1. An exact `(channel, kind)` row.
2. A channel-wide row stored with `kind = "*"`.
3. An implicit enabled default with no quiet hours.

`effective_preferences()` expands the stored rows into the complete 3 × 5
channel/kind matrix used by the preference panel. Wildcard rules are expanded
into concrete rows so the UI never has to reason about wildcards.

### `Severity` and urgency

Severities are ordered `info (0)`, `warning (1)`, `critical (2)`. The rank
drives both inbox ordering and digest grouping. `critical` receives two
additional guarantees: it is never held back by quiet hours and its delivery
decision is reported as `critical_override`.

### `Digest`, `DigestEntry` and `DigestGroup`

A digest stores its entries as a compact JSON array in `entries_json`.
`DigestEntry` survives a JSON round trip through `to_dict()` / `from_dict()`;
corrupt payloads decode to an empty tuple rather than raising.
`group_digest_entries()` buckets by `(kind, severity)` and orders groups by
severity rank (most urgent first), then kind name. `Digest.render_markdown()`
produces a readable body with one heading per group.

`DigestPeriod` defines `hourly`, `daily` and `weekly` windows. `build_digest()`
selects notifications created within `now - period.window`, orders them by the
shared severity rule and serialises the entries.

### `RetentionPolicy`

`max_age_days` (default 30) and `keep_unread` (default `True`) define the
retention rule. `prune()` returns `(kept, removed)` and never removes unread
messages unless `keep_unread` is explicitly disabled. `stale_count()` previews
the impact before a destructive operation.

### `DeliveryDecision` and `CreateResult`

Every creation returns the stored notification plus a decision with a stable
reason code:

| Reason | Meaning |
| --- | --- |
| `delivered` | The preference allowed immediate delivery. |
| `channel_disabled` | The channel/kind pair is switched off. |
| `quiet_hours` | Delivery is deferred until `suppressed_until_hour`. |
| `critical_override` | A critical alert bypassed quiet hours. |

Suppressed notifications are still persisted so the inbox remains an honest
record of what happened.

### Templating

`render_template()` replaces `{{ name }}` placeholders. Dotted paths traverse
nested mappings, booleans render as `yes`/`no`, and `None` renders as an empty
string. Unknown placeholders are preserved verbatim, making missing variables
visible instead of silently dropping text. `template_variables()` returns the
distinct placeholder names, which is useful for template validation.

## Persistence

Three repositories extend `BaseRepository` and use parameterised SQL only.

| Repository | Table | Highlights |
| --- | --- | --- |
| `NotificationRepository` | `v3_notifications` | CRUD, filtered listing with a `CASE` severity sort, unread counts, bulk mark-read, older-than scan, bulk delete. |
| `PreferenceRepository` | `v3_notification_preferences` | Composite-key lookup, `ON CONFLICT` upsert, list by recipient, delete. |
| `DigestRepository` | `v3_digests` | CRUD, sent timestamp update, unsent queue, list by recipient. |

Indexes cover `(recipient_id, created_at DESC)`, unread lookups, preference
lookups and digest lookups. `SCHEMA_SQL` is exported from `__init__.py` and
executed by `Database.migrate()` together with every other feature schema.

## Service rules

`NotificationService` composes the repositories with the pure rules:

* `create()` validates content, renders the body, resolves preferences,
  evaluates delivery and stores the message.
* `get()`, `list_notifications()` and `total_matching()` provide read paths;
  missing identifiers raise `NotFoundError`.
* `mark_read()` is idempotent; `mark_all_read()` returns the number of rows
  changed; both update the unread counters used by the UI.
* `list_preferences()`, `effective_preferences()`, `lookup_preference()`,
  `upsert_preference()` and `delete_preference()` manage delivery settings.
* `preview_digest()` computes an unsaved digest; `build_digest()` persists one;
  `send_digest()` marks it dispatched and raises `ConflictError` on a second
  attempt.
* `prune()` deletes expired notifications and returns the number removed;
  `stats()` aggregates totals per channel, kind and severity.

Domain errors use the shared `DashboardError` family, so the application-level
exception handler renders them with the standard `{ "error": { ... } }`
envelope.

## HTTP API

All routes are mounted under `/api/notifications` with the `notifications`
tag. Request and response models live in `schemas.py`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/notifications` | Filtered, paginated listing plus `total` and `unread`. Supports `recipient_id`, `channel`, `kind`, `severity`, `unread_only`, `search`, `limit`, `offset`. |
| `POST` | `/api/notifications` | Emit a notification; returns `notification`, `decision` and `delivered`. |
| `POST` | `/api/notifications/{id}/read` | Acknowledge one notification. |
| `POST` | `/api/notifications/read-all` | Acknowledge every unread notification of a recipient. |
| `GET` | `/api/notifications/preferences` | Effective preference matrix for `recipient_id`. |
| `PUT` | `/api/notifications/preferences` | Upsert one preference row. |
| `GET` | `/api/notifications/digest` | Unsaved digest preview for `recipient_id` and `period`. |
| `POST` | `/api/notifications/digest` | Generate and persist a digest. |
| `POST` | `/api/notifications/digest/send` | Mark a stored digest as sent. |
| `GET` | `/api/notifications/stats` | Aggregated counters, optionally for one recipient. |
| `POST` | `/api/notifications/prune` | Remove notifications older than the retention window. |

Representative request:

```json
{
  "recipient_id": "member-1",
  "channel": "email",
  "kind": "solve",
  "title": "Flag captured",
  "body": "Solved {{ challenge }} for {{ points }} points",
  "variables": { "challenge": "Warmup", "points": 250 },
  "severity": "warning"
}
```

Representative delivery decision:

```json
{
  "channel": "email",
  "delivered": false,
  "reason": "quiet_hours",
  "suppressed_until_hour": 8
}
```

Errors follow the shared envelope with codes `not_found`, `validation_error`
and `conflict`; malformed payloads are rejected by Pydantic with HTTP 422.

## Frontend

`plugin.ts` registers the feature with id `notifications`, label
`Notifications`, path `/notifications`, group `Workspace` and the
`NotificationsPage` root component. The kernel mounts the route and adds a
module launcher link automatically.

### Screen walkthrough

1. The header shows the page title, a recipient selector, a refresh action and
   a "Send test" button. Sending a test notification demonstrates the full
   path: API creation → delivery decision → toast.
2. Four statistic cards summarise total, unread, critical unread and read rate.
3. The left column is the inbox. Filters cover kind, severity, unread-only and
   free-text search. "Mark all read" performs a bulk update. Each row offers a
   per-item mark-read control and an optional deep link. Urgent rows carry a
   coloured rail and a severity badge.
4. The right column holds the preference panel and digest preview. Preferences
   are grouped by channel with a switch per event kind and numeric quiet-hour
   inputs. The digest panel offers hourly/daily/weekly periods, grouped
   entries, a markdown preview and a send action.
5. Toasts appear in a fixed bottom-right queue. They auto-dismiss, can be
   dismissed individually or cleared together, and use an assertive live region
   for critical messages.

### Component inventory

| Component | Responsibility |
| --- | --- |
| `NotificationList` | Filters, loading/empty/error states, bulk action. |
| `NotificationItem` | One row with metadata, severity styling and actions. |
| `PreferencePanel` | Channel/kind switches and quiet-hour inputs. |
| `DigestPreview` | Period controls, grouped entries and markdown disclosure. |
| `ToastQueue` | Accessible viewport with dismiss affordances. |
| `SeverityBadge` | Shared severity pill. |

`hooks.ts` contains `useNotificationCentre()` (data loading, optimistic
mark-read and preference updates) and `useToastQueue()` (bounded queue with an
interval-driven expiry check). `logic.ts` holds the pure filter, preference,
hour and toast helpers. `api.ts` wraps `get`, `post` and `put` from the shared
client with typed request/response shapes and query construction.

### Styling

Every component ships a local `*.module.css` file. Severity colours map to the
existing design tokens (`--info-base`, `--warning-base`, `--danger-base`).
Layouts collapse from two columns to one at 1100px, filters reflow at 900px and
560px, and the toast queue narrows on small screens. Focus-visible rings and
hover states follow the shared design system. All transitions are disabled
inside `prefers-reduced-motion: reduce`.

## Testing notes

Backend: `tests/test_v3_notifications.py` contains 29 tests covering severity
ordering, quiet windows (including midnight wrap), template substitution,
preference precedence and validation, digest grouping and JSON round trips,
retention pruning, stats, repository CRUD, service orchestration, error paths
and every router endpoint. Router tests use the shared `client`, `database`
and `settings` fixtures, so no shared test configuration is modified.

Frontend: five colocated suites cover pure logic, the typed API adapter, a
rendered mark-read interaction, preference switches and the toast queue
(including bounded pushes and automatic expiry). Tests use Vitest and React
Testing Library with the existing setup file.

Quality gates run from the worktree root:

```bash
python3 -m ruff check . && python3 -m ruff format --check .
python3 -m mypy
PYTHONPATH=src python3 -m pytest -q
cd frontend && npm run lint && npm run format:check && npm run typecheck && npm test && npm run build
python3 scripts/loc_gate.py 448fe50 HEAD --min 2000
```

## Accessibility notes

* Inbox sections use `aria-labelledby`; the list and toast viewport expose
  explicit accessible names.
* Preference switches are native checkboxes with `role="switch"` and
  descriptive labels; quiet-hour inputs are numeric and labelled per channel.
* Digest periods use `aria-pressed` so the active window is announced.
* Toast messages use `role="status"` for informational/warning messages and
  `role="alert"` with an assertive live region for critical messages.
* Icon-only dismiss controls carry `aria-label` values; the severity rail is
  decorative and hidden from assistive technology.
* Keyboard users can reach every control in DOM order, and visible focus
  styling is inherited from the global `:focus-visible` rule.
* Relative timestamps use semantic `<time dateTime>` elements, and markdown
  output is exposed through a native `<details>` disclosure.
