# V3 — Flag submission pipeline

The submission pipeline is the operational surface for trying flags against
seeded CTF challenges. It accepts a flag from a member, normalises and
validates it, deduplicates repeated attempts, queues it for deterministic
acceptance checks and exposes retries with exponential backoff. The React
screen at `/submissions` presents the same state machine as a live console.

## Scope and files

| Layer | Location |
| --- | --- |
| Domain | `src/ctf_team_dashboard/features/submission_pipeline/models.py` |
| Persistence | `src/ctf_team_dashboard/features/submission_pipeline/store.py` |
| Service | `src/ctf_team_dashboard/features/submission_pipeline/service.py` |
| Schemas | `src/ctf_team_dashboard/features/submission_pipeline/schemas.py` |
| Router | `src/ctf_team_dashboard/features/submission_pipeline/router.py` |
| Tables | `v3_submissions`, `v3_validation_rules` |
| Page | `frontend/src/features/submission-pipeline/SubmissionsPage.tsx` |
| Tests | `tests/test_v3_submission_pipeline.py`, colocated `*.test.ts(x)` |

The package exports `SCHEMA_SQL` and `register(app)`; the platform kernel
discovers it automatically, so no shared registry is modified.

## Domain rules

### Submission entity

A `Submission` is a frozen, slotted dataclass carrying:

* `id`, `challenge_id`, `member_id`
* `flag_cipher` — a partially masked representation of the flag. Plaintext
  flags are never persisted into the live log.
* `status` — one of `queued`, `validating`, `accepted`, `rejected`, `retrying`
* `attempts`, `created_at`, `completed_at`, `error`
* `flag_digest` — SHA-256 of the normalised flag plus the challenge identifier
* `next_attempt_at` — the timestamp after which a retry may be processed
* `accepted` — the deterministic acceptance decision recorded at submit time

Derived properties (`is_pending`, `is_retryable`, `stage_index`, `can_retry`,
`is_due`, `elapsed_seconds`) keep the state machine readable at call sites.

### Normalisation

`normalize_flag` trims surrounding whitespace, lower-cases the value, removes
matching quote or backtick wrappers and collapses internal whitespace runs into
underscores. The canonical value is used for validation, digesting and
acceptance, so `  FLAG{NONCE_REUSE}  ` and `flag{nonce_reuse}` are equivalent.

### Format validation

`ValidationRule` is a frozen dataclass with an `id`, `name`, `pattern`,
`description`, `enabled` flag, `priority` and `kind`. Patterns are compiled on
construction; invalid expressions raise `ValidationError`. Two rules are
seeded automatically into `v3_validation_rules`: a `flag{...}` wrapper rule and
a length rule (8–256 characters). Rules are evaluated in priority order and the
first failing rule supplies the hint shown in the console.

### Deduplication

The digest is `sha256(lowercase(challenge_id) + "\x00" + normalised_flag)`. A
unique constraint on `(challenge_id, flag_digest)` plus an explicit lookup in
`submit` prevents the same flag from being queued twice for one challenge. A
duplicate raises `ConflictError` with the existing submission identifier in the
error details. Supplying a *corrected* flag through the retry endpoint changes
the digest and is therefore allowed.

### Status transitions

```
queued ──► validating ──► accepted
   │            │
   │            └──────► rejected ──► retrying ──► validating
   └────────────────────► rejected
```

`ALLOWED_TRANSITIONS` is the single source of truth. `can_transition` and
`assert_transition` are pure helpers; illegal transitions raise
`ValidationError` with the attempted transition in the error details.
`Submission.with_status` refuses to build an invalid next state.

### Deterministic acceptance

Seeded challenges derive their answer from the challenge title:
`expected_flag(title)` slugifies the title and wraps it as `flag{token}`. A
submission is accepted when its normalised flag equals that value. The decision
is computed at submission time and stored, so queue processing is reproducible
and does not need to retain plaintext flags.

### Retry policy

`RetryPolicy(max_attempts=3, backoff_seconds=2.0, max_backoff_seconds=60.0)`
provides `can_retry(attempts)`, `delay_for(attempts) = min(cap, base * 2^(n-1))`
and `schedule_after(attempts, now)`. A rejected submission can be retried only
while attempts remain. Retrying sets `status=retrying` and `next_attempt_at`;
the queue skips the submission until that time. An optional replacement flag
is validated and re-digested before the retry is persisted.

### Queue processing

`process_queue` selects pending submissions whose backoff has elapsed, moves
each to `validating` (incrementing `attempts`), decides the outcome, writes the
terminal status with `completed_at` and returns a `QueueSummary` containing
`processed`, `accepted`, `rejected`, `skipped`, `remaining` and `success_rate`.

### Aggregation

`aggregate()` returns `SubmissionStats` with counts by status, per-member
`MemberSubmissionStats`, totals, acceptance rate, average attempts and retry
counts. All figures come from grouped SQL queries over the two feature tables.

## HTTP API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/submissions` | Validate and enqueue a flag |
| `GET` | `/api/submissions` | Filter by `status`, `challenge_id`, `member_id`, with `limit`/`offset`/`order` |
| `GET` | `/api/submissions/{id}` | Return one submission |
| `POST` | `/api/submissions/{id}/retry` | Schedule a retry, optionally with a corrected flag |
| `POST` | `/api/submissions/process` | Process due submissions |
| `GET` | `/api/submissions/stats` | Return aggregate statistics |
| `GET` | `/api/submissions/rules` | List validation rules |
| `POST` | `/api/submissions/rules` | Create a validation rule |

All request and response bodies are typed Pydantic models. Domain errors use
the shared envelope: `ValidationError` → 422, `ConflictError` → 409,
`NotFoundError` → 404. Validation failures include a `code` and `rule_id` in
the error details so the console can show precise hints.

## Frontend walkthrough

The plugin registers `{ id: "submissions", label: "Submissions", path:
"/submissions", group: "Operations" }` and is discovered by the dynamic plugin
registry.

1. **Statistics row** — six cards show total, accepted, rejected, pending,
   acceptance percentage and average attempts. A banner reports the last queue
   pass.
2. **Submission console** — challenge and member selectors are populated from
   the existing APIs; selecting a challenge narrows members to that team. The
   flag input accepts the raw value, the client normalises and validates it
   with the same rules as the backend, and `ValidationHint` lists the active
   checks. Errors are announced with `role="alert"`.
3. **Pipeline state** — the most recent submission is shown as
   `Queued → Validating → Accepted` (or a danger-toned final node for a
   rejection). The active node pulses; the animation is disabled under
   `prefers-reduced-motion`.
4. **Live log** — a filterable table shows the masked flag, challenge, member,
   compact pipeline, badge, attempt count, relative timestamp and a retry
   button. Retry affordances are disabled with an explanatory `title` when the
   status or attempt budget forbids a retry. The list refreshes every ten
   seconds and after each mutation.

Components: `SubmissionForm`, `StatusPipeline`, `SubmissionLog`, `RetryButton`,
`SubmissionStats`, `ValidationHint`. Each owns a CSS module using the shared
design tokens, responsive breakpoints, focus/hover states and reduced-motion
rules.

## Testing notes

Backend tests (`tests/test_v3_submission_pipeline.py`) cover normalisation,
digests and masking, deterministic seeded answers, format rules, transition
legality, retry backoff and budgets, service submit/process/retry flows,
filtering, aggregation, rule CRUD and the full router success/error matrix.

Frontend tests cover:

* pure logic (normalisation, validation, stage mapping, retry gating,
  formatting and label resolution);
* the API adapter (query construction, endpoint paths and request bodies);
* a rendered form interaction (preselection, invalid submission hint,
  normalised submission and API error alert);
* the rendered status pipeline for accepted, rejected and compact states;
* the routed page composing the console, statistics and live log and wiring
  retry/submission handlers.

## Accessibility notes

* Every form control has a visible, programmatically associated label; filter
  selects use visually hidden labels.
* Validation failures and API errors use `role="alert"`; success and queue
  summaries use `role="status"`.
* The pipeline is a labelled `role="group"` with `aria-current="step"` on the
  active stage.
* Retry buttons expose an explicit `aria-label` and a `title` explaining why
  they are disabled.
* Status colour is always paired with a text label; layouts reflow to a single
  column on narrow screens and all motion is suppressed for reduced-motion
  users.
