# V3 — Offline queue and sync

The offline sync feature lets a dashboard client keep working while its network
connection is unavailable. Every local edit is captured as a **pending
mutation**, replayed in first-in-first-out order when connectivity returns, and
paused for a human decision when the server has moved ahead of the version the
client edited. A dedicated **Offline & Sync** screen makes the queue, conflict
ledger and sync health inspectable instead of treating background reconciliation
as a black box.

## Scope

| Concern | Detail |
| --- | --- |
| Backend package | `src/ctf_team_dashboard/features/offline_sync/` |
| Frontend package | `frontend/src/features/offline-sync/` |
| Backend tests | `tests/test_v3_offline_sync.py` |
| Plugin | `offline` — *Offline & Sync*, group *Operations*, route `/offline` |
| API prefix | `/api/sync` |
| Owned tables | `v3_pending_mutations`, `v3_sync_snapshots`, `v3_conflict_resolutions` |

The feature follows the V3 branch contract: it is discovered dynamically by the
platform kernel and touches no shared registry, app factory, database engine or
design-system file.

## Domain model

### PendingMutation

A queued change carries an identifier, the client that produced it, a logical
entity name, an operation (`create`, `update` or `delete`), a JSON payload, and
the **base version** the client observed before editing. Lifecycle status is
`pending`, `synced` or `conflict`. An `attempts` counter records how many push
tries have been made, and `last_error` explains the most recent failure.

Useful derived behaviour:

* `payload` decodes `payload_json` defensively.
* `is_pending`, `is_synced`, `is_conflicted` and `is_retryable` are pure
  predicates; a mutation stops retrying after five attempts.
* `next_retry_delay` returns deterministic exponential backoff
  (`2s, 4s, 8s …` capped at `60s`).
* `queue_key` is `(created_at, id)`, which is what makes FIFO ordering stable
  even when two clients enqueue in the same millisecond.
* Transitions (`mark_attempt`, `mark_synced`, `mark_conflict`, `requeue`,
  `with_payload`) return new frozen instances rather than mutating in place.

### SyncSnapshot

Each processing batch writes an immutable snapshot: identifier, client,
`synced_at`, the highest version observed, and counts of applied and conflicted
mutations. `is_fresh(max_age_seconds)` and `success_rate` power the status card
and the staleness warning.

### ConflictResolution

When a conflict is settled, a resolution record stores the conflicting
mutation, the chosen strategy (`local_wins`, `remote_wins` or `merge`), the
local and remote versions, a JSON list of per-field decisions and an optional
note. `field_changes` decodes the decisions into `FieldChange` objects whose
`summary` and `contested` flags drive the resolution dialog.

## Conflict rules

Version comparison is deliberately simple and auditable:

```
relation = compare_versions(base_version, current_version)
conflict = relation is not VersionRelation.CURRENT
```

A `create` normally uses base version `0`; if the entity already exists at a
higher version, the mutation conflicts. An `update` or `delete` conflicts
whenever the server version differs from the base version the client saw.
When the caller supplies no version for an entity, the service assumes the
mutation's base version is still current, so offline work can be replayed
against entities the server has never seen.

Batch processing stores the supplied `current_versions` as a **point-in-time
snapshot**: every mutation in one batch is compared against that snapshot and a
successful push advances the snapshot's recorded version by one. FIFO order is
guaranteed by sorting on `queue_key`; only `pending` mutations are examined.
Attempts are incremented before each push, conflicts pause the mutation with a
human readable reason, and exhausted retry budgets are reported as failures.

### Field level merge

`merge_payloads(base, local, remote, strategy)` produces a payload and one
decision per touched field:

* **local_wins** — start from the remote payload and overlay every local field.
* **remote_wins** — start from the local payload and overlay every remote field;
  server edits win while local-only fields are retained.
* **merge** — a three-way merge against `base`:
  * equal local and remote values are kept;
  * a field changed by only one side keeps that side's value;
  * a field changed differently by both sides keeps the local value and is
    flagged `contested`, so the UI can call attention to it.

The resolution endpoint accepts optional `base_payload` and `remote_payload`
objects. When omitted they default to empty objects, which is sufficient for
the common case where the client only wants to force a side to win.

## Queue lifecycle

```
enqueue ──> pending ──> process batch ──> synced ──> clear synced
                 └──────── conflict ──> resolve ──> synced
                              └──────> retry ──> pending
```

`clear_synced` removes synchronised mutations and their resolution rows while
leaving pending and conflicted work untouched, so a cleanup cannot silently
discard outstanding edits.

## API surface

All routes are mounted under `/api/sync` and use typed Pydantic bodies and
responses. Domain failures use the shared `{ "error": { "code", "message",
"details" } }` envelope.

| Method | Path | Purpose | Request | Response |
| --- | --- | --- | --- | --- |
| `POST` | `/mutations` | Enqueue a mutation | `MutationCreate` | `MutationRead` (201) |
| `GET` | `/queue` | Inspect FIFO queue | `client_id`, `status`, `entity`, `limit` | `QueueResponse` |
| `POST` | `/process` | Process one batch | `ProcessRequest` | `ProcessResponse` |
| `POST` | `/conflicts/{id}/resolve` | Resolve a conflicted mutation | `ConflictResolveRequest` | `ConflictResolutionRead` |
| `GET` | `/status` | Read queue and snapshot health | `client_id` | `SyncStatusRead` |
| `DELETE` | `/queue` | Clear synchronised entries | `client_id` | `ClearResponse` |

Notes on the contract:

* The `{id}` in the resolve route is the **mutation id**. The queue inspector
  exposes exactly that identifier for rows whose status is `conflict`.
* `GET /queue` accepts `status=pending|synced|conflict`; `total` reflects the
  filtered result while `pending`/`conflicts` come from the unfiltered summary.
* `POST /process` validates `1 <= limit <= 500` and rejects negative server
  versions. An empty queue still produces a snapshot with zero counts.
* `GET /status` combines `SyncStats` with snapshot freshness and the number of
  recorded resolutions; `health_label` is `idle`, `syncing`, `attention` or
  `healthy`.
* `DELETE /queue` reports how many rows were deleted and how many remain.

### Example

```http
POST /api/sync/mutations
Content-Type: application/json

{
  "client_id": "laptop-7",
  "entity": "note",
  "operation": "update",
  "payload": {"title": "Nonce reuse", "body": "IV repeats"},
  "base_version": 3,
  "mutation_id": "note-3-edit"
}
```

```http
POST /api/sync/process
Content-Type: application/json

{
  "client_id": "laptop-7",
  "limit": 25,
  "current_versions": {"note": 4}
}
```

The second call returns a `conflict` outcome because the client based its edit
on version 3 while the server is at version 4. The UI then opens the conflict
dialog for `note-3-edit`.

## Frontend walkthrough

The `offline` plugin registers `/offline` and appears under **Operations** in
the module launcher. The page is composed from six focused components:

* **ConnectivityBanner** — listens to `navigator.onLine` plus the `online` and
  `offline` window events. It shows a reassuring green state when connected and
  an amber warning when disconnected, with a live-region announcement for
  screen readers.
* **OfflineBadge** — a compact status pill reused in the header and on mutation
  rows. It distinguishes offline, syncing, conflicted and up-to-date states.
* **QueueInspector** — a filterable list of mutations with status, entity,
  operation, base version, attempts and age. Selecting a conflicted row opens
  the resolution dialog; a manual refresh re-reads the queue.
* **MutationRow** — a keyboard-operable list row with an operation icon, a
  payload preview, retry count and a status badge. Long payloads are truncated
  with an accessible title attribute.
* **ConflictDialog** — a modal with three radio buttons (`Local wins`,
  `Remote wins`, `Merge fields`), an optional note field and a live preview of
  the merge result. Submitting posts the chosen strategy to the resolve route.
* **SyncStatus** — cards for pending, synced and conflicted counts, a
  completion progress bar, last snapshot version and a **Sync now** button that
  triggers a manual batch.

The page keeps loading, empty, error and success states distinct. When the
browser goes offline the manual sync button is disabled, the banner explains
that edits will be queued locally, and previously loaded data remains visible.
Mutations are stored server-side by this feature; the browser adapter only
reads and drives the queue, so a reload never loses queued work.

Pure view helpers (`sync.ts`) own status tones, relative time formatting,
queue grouping, merge previews and connectivity copy. Keeping them free of
React lets the test suite validate the rules directly.

## Data flow

1. `OfflinePage` loads `GET /status` and `GET /queue` through `hooks.ts`.
2. `ConnectivityBanner` tracks browser connectivity; going online triggers a
   refresh of both resources.
3. **Sync now** calls `POST /process` with the current server versions, then
   refreshes status and queue.
4. A conflicted row opens `ConflictDialog`; the chosen strategy is posted to
   `/conflicts/{id}/resolve` and the queue is refreshed again.
5. After a successful batch, synchronised rows can be removed with
   `DELETE /queue`, which leaves pending and conflicted work intact.

## Testing notes

Backend (`tests/test_v3_offline_sync.py`, 34 tests) covers:

* enum serialisation, version classification and conflict detection;
* all three merge strategies including contested fields and field decisions;
* deterministic backoff, FIFO ordering and derived status properties;
* schema creation, enqueue validation, duplicate detection and filtering;
* batch application, conflict detection, retry exhaustion and snapshots;
* conflict resolution, requeue and selective cleanup;
* every HTTP route including 201, 422, 404 and 409 error envelopes.

Frontend tests cover pure sync helpers, the typed API adapter, connectivity
event handling and a rendered page interaction. All network calls are mocked,
so the suite remains deterministic and offline.

## Accessibility notes

* The connectivity banner uses `role="status"` with `aria-live="polite"` so
  connection changes are announced without stealing focus.
* Conflict strategies are native radio inputs inside a labelled `fieldset`; the
  dialog uses `role="dialog"` with `aria-modal` and returns focus to the
  triggering row when closed.
* Mutation rows are buttons with explicit accessible names, visible focus rings
  and `aria-label` attributes describing the operation and entity.
* Status cards expose numbers as text rather than colour alone; tones are
  complemented by labels and icons.
* Progress bars expose `role="progressbar"` with `aria-valuenow`,
  `aria-valuemin` and `aria-valuemax`.
* CSS honours `prefers-reduced-motion` and uses high-contrast design tokens for
  status colours. Every interactive control is reachable with the keyboard.
