# V3 — Tiered hint engine

The hint engine adds a progressive disclosure economy to the CTF dashboard. A
challenge can carry up to three hints; each hint is harder to obtain than the
last, and every reveal is debited from a finite team budget. The feature ships
as a self-contained backend package (`features/hint_engine`) and a routed React
plugin (`features/hint-engine`) with no edits to shared registries.

## Goals

* Let authors describe a three-step hint ladder with a predictable price curve.
* Give teams a transparent way to spend a shared allowance without overspending.
* Never leak locked hint content through the API, the DOM or the browser cache.
* Make every reveal auditable through a per-team ledger.

## Domain model

### `Hint`

`id`, `challenge_id`, `tier` (1–3), `title`, `content`, `cost`, `base_cost`,
`multiplier`, `reveal_after_seconds`, `is_active`, `created_at`, `updated_at`.
A unique constraint on `(challenge_id, tier)` keeps the ladder well formed.
Pure helpers derive the tier price, the teaser and the previous tier.

### `HintUnlock`

`id`, `hint_id`, `member_id`, `team_id`, `cost_paid`, `unlocked_at`. The append
only ledger has a unique constraint on `(hint_id, team_id)`: a team reveals a
hint once, no matter how many members try.

### `HintBudget`

`team_id`, `total`, `spent`, `reset_at`, `created_at`. `remaining` is clamped at
zero, `utilization` is clamped to `[0, 1]`, and `can_afford(cost)` expresses the
single affordability rule used by both the service and the UI.

Supporting records (`CostPoint`, `TierSpend`, `TeamSpendSummary`, `LedgerEntry`,
`HintView`, `ChallengeHintView`, `Eligibility`) are immutable dataclasses used
to move data between the store, the service and the HTTP serialisation layer.

## Rules

### Cost curve

For tier `t`:

```
cost(t) = round_half_up(base_cost * multiplier^(t - 1))
```

The default ladder is `base_cost = 25`, `multiplier = 2.0`, giving prices
`25 / 50 / 100` and a cumulative spend of `25 / 75 / 175`. Rounding is
performed with `Decimal` and `ROUND_HALF_UP` on the backend; the frontend mirrors
the rule with `Math.round` for its SVG chart and confirmation copy. `reveal_after_seconds`
is measured from `challenge.starts_at` (falling back to `created_at`).

### Eligibility states

| State | Meaning |
| --- | --- |
| `locked` | Inactive hint, missing previous tier, or the timer has not elapsed. |
| `eligible` | Prerequisites and timer are satisfied and the budget covers the price. |
| `unlocked` | The team already paid for this hint; full content is returned. |
| `exhausted` | Prerequisites are met but the remaining allowance is too small. |

`evaluate_eligibility` is a pure function so the rules can be tested without a
database. The service adds identity checks: the challenge, team and member must
exist and agree, and a revealed hint cannot be deleted or repriced.

### Atomic unlock

`HintStore.atomic_unlock` opens one `BEGIN IMMEDIATE` transaction and repeats
the duplicate and affordability checks inside it before updating the budget and
inserting the ledger row. This prevents two simultaneous requests from spending
the same credits or producing duplicate ledger entries. Failure maps to the
shared error envelope: `409 conflict` for duplicate/prerequisite violations and
`422 validation_error` for timing or budget failures.

### Masking

Locked hints never leave the service in clear text. `mask_content` keeps the
first 28 characters and replaces each remaining character with an asterisk. The
React `HintReveal` component additionally blurs the text via CSS and hides it
from assistive technology with `aria-hidden`, while the reason is exposed in a
live region.

### Budget reset

`POST /api/hints/budget/{team_id}/reset` clears `spent`, optionally replaces
`total`, and moves `reset_at`. The ledger is never rewritten, so historical
prices remain intact after a reset.

## Persistence

| Table | Purpose |
| --- | --- |
| `v3_hints` | Hint catalogue with per-challenge tier uniqueness. |
| `v3_hint_unlocks` | Append-only reveal ledger, unique per hint and team. |
| `v3_hint_budgets` | One allowance row per team. |

All three tables are created by `SCHEMA_SQL` and discovered by
`Database.migrate()` through the dynamic feature registry. Queries use bound
parameters and the shared `BaseRepository` helpers.

## HTTP API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/hints` | List hints; optional `challenge_id` and `team_id` filters. |
| `POST` | `/api/hints` | Author a hint and compute its tier price. |
| `PATCH` | `/api/hints/{id}` | Edit a hint; repricing is blocked after the first reveal. |
| `DELETE` | `/api/hints/{id}` | Delete a hint that has never been revealed. |
| `GET` | `/api/hints/challenges/{challenge_id}` | Masked ladder for `team_id` (and optional `member_id`). |
| `POST` | `/api/hints/{id}/unlock` | Spend budget and reveal a hint. |
| `GET` | `/api/hints/budget/{team_id}` | Return or provision a team budget. |
| `POST` | `/api/hints/budget/{team_id}/reset` | Clear spend and start a new window. |
| `GET` | `/api/hints/ledger/{team_id}` | Reveal history plus spend summary. |

Every request and response uses Pydantic models in `schemas.py`. Domain errors
are raised as `NotFoundError`, `ValidationError` or `ConflictError` and rendered
by the application's shared exception handler.

## UI walkthrough

The plugin declares `id: "hints"`, `path: "/hints"`, `label: "Hints"` and
`group: "Workspace"`, so it is discovered automatically by the launcher.

1. The page loads teams, challenges and members through the typed adapter and
   populates three selectors. Changing the team resets the challenge and member
   selections to valid values.
2. `BudgetMeter` draws an SVG progress ring: spent allowance fills the ring and
   the remaining credits appear in its centre. The reset button calls the reset
   endpoint and refreshes both the ladder and the ledger.
3. `CostCurve` renders bars for each tier price and a line for cumulative cost,
   with an HTML legend that repeats every number for screen readers.
4. `HintCard` renders one tier. Locked bodies are masked and blurred, the state
   badge explains why, and the unlock button is only enabled when the pure
   `canUnlock` check passes.
5. Activating unlock opens `UnlockDialog`, which shows the price, the balance
   after payment and any server error. Confirming calls the unlock endpoint and
   optimistically refreshes the workspace once the mutation succeeds.
6. `HintLedgerView` lists every reveal with member, tier, cost and time, plus a
   small per-tier spend breakdown. Empty, loading and error states are explicit.

## Accessibility notes

* The dialog is a real `role="dialog"` with `aria-modal`, labelled title and
  described body; it traps Tab focus, closes on Escape or backdrop click and
  returns focus to the element that opened it.
* The budget ring and cost chart carry `role="img"` with descriptive labels;
  the data is also present as text in the surrounding DOM.
* Blurred hint text is `aria-hidden`, and the reason for each state is exposed
  in a polite live region.
* Controls use the shared design system primitives, so focus rings, disabled
  states and announcements match the rest of the dashboard.
* Every CSS module includes reduced-motion and high-contrast overrides; blur,
  transitions and large background gradients degrade gracefully.

## Tests

Backend (`tests/test_v3_hint_engine.py`) covers cost rounding, curve totals,
content masking, eligibility states, budget properties, catalogue CRUD, tier
prerequisites, duplicate unlocks, foreign members/teams, insufficient budget,
reveal delays, budget reset, masked challenge views, ledger aggregation and
router status/error codes.

Frontend tests cover cost-curve maths and formatting (`hints.test.ts`), endpoint
URLs and payloads (`api.test.ts`), blurred/unlockable hint cards
(`HintCard.test.tsx`), dialog focus/Escape/confirm behaviour
(`UnlockDialog.test.tsx`) and the composed workspace (`HintsPage.test.tsx`).
