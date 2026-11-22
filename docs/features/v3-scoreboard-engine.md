# V3 feature: configurable scoreboard engine

| Item | Value |
| --- | --- |
| Branch | `dev/v3-04-scoreboard-engine` |
| Slug | `scoreboard_engine` |
| Frontend route | `/scoreboard` |
| Plugin id / label / group | `scoreboard` / `Scoreboard` / `Analysis` |
| Backend prefix | `/api/scoreboard` |
| Tables | `v3_score_rules`, `v3_score_snapshots` |

## 1. Overview

The scoreboard engine turns raw challenge and solve records into an explainable,
configurable competition ranking. Other V3 branches own the data that feeds the
scoreboard; this branch only *reads* teams, challenges and solves through the
existing repositories and writes its own rules and snapshots.

Three questions drive the design:

1. **How much is a solve worth?** A team-specific `ScoreRule` combines a base
   award, a difficulty weight, a multiplier, first blood bonuses, hint penalties
   and a decay curve.
2. **Who is ahead?** The live ranking sorts teams by points, then solves, then
   earliest last solve, and derives movement against the last stored snapshot.
3. **How did we get here?** Every snapshot persists the totals, the rank and a
   JSON detail payload containing the rule fingerprint, category shares and the
   top five solve formulas.

The backend and frontend share the same arithmetic rules: `models.py` owns the
authoritative Python calculation, while `scoring.ts` mirrors it so the rule
editor can show a live preview. Both clamp results to non-negative integers.

## 2. Domain model

### 2.1 `ScoreRule`

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | `str` | Stable row identity, preserved across upserts. |
| `team_id` | `str` | Owning team; one rule per team. |
| `name` | `str` | Human readable policy name. |
| `base_points` | `int` | Points before weighting. |
| `difficulty_multiplier` | `float` | Global multiplier, range `0.1–10`. |
| `first_blood_bonus` | `int` | Flat bonus for the earliest solve of a challenge. |
| `hint_penalty` | `int` | Points subtracted per hint used. |
| `decay_factor` | `float` | Per-solve decay coefficient, range `0.05–1`. |
| `decay_enabled` | `bool` | Turns the decay curve on or off. |
| `updated_at` | `datetime` | Timezone-aware UTC timestamp. |

Derived behaviour: `is_decaying`, `decay_for(index)`, `summary` and a stable
`fingerprint()` used in snapshot details. The default "Balanced" policy uses
100 base points, multiplier 1.0, a 50 point first blood bonus, a 10 point hint
penalty and a decay factor of 0.9.

### 2.2 `ScoreSnapshot`

An immutable record of `id`, `team_id`, `recorded_at`, `points`, `solves`,
`rank` and `details_json`. The `details` property decodes the JSON payload and
tolerates corrupt data by returning an empty mapping. `label`, `is_podium` and
`rule_name` are presentation helpers.

The details payload contains:

```json
{
  "rule_name": "Balanced",
  "rule_id": "rule-team-0001",
  "rule_fingerprint": "1a2b3c4d",
  "team_name": "RedScribe",
  "first_bloods": 3,
  "hint_penalties": 20,
  "decay_loss": 118.42,
  "average_points": 162.5,
  "challenges": 12,
  "categories": [ ... ],
  "top_solves": [ ... ]
}
```

### 2.3 `RankingEntry` and movement

`RankingEntry` carries `team_id`, `team_name`, `points`, `solves`, `rank`,
`previous_rank`, `movement` and `last_solve_at`. `RankMovement` is a string
enum with `up`, `down`, `stable` and `new`. `movement_label` renders `↑2`, `↓1`,
`—` or `NEW`; `movementDescription` in the frontend produces the equivalent
assistive-technology sentence.

### 2.4 Supporting objects

* `SolveScore` itemises every component of one award, including the formula
  string and the base/decayed values used by the detail chart.
* `CategoryScoreBreakdown` aggregates points, solves and challenge counts per
  `ChallengeCategory`, with `share(total)` and `solve_rate`.
* `ScoreBreakdown` bundles a rule, all solve scores, category breakdowns and
  the challenge count, and serialises itself into snapshot details.

## 3. Scoring algorithm

For solve `i` (zero based, chronological order within a team):

```text
weighted = base_points
         × difficulty.weight          (trivial 0.5 … insane 5.0)
         × difficulty_multiplier
         × (decay_factor ^ i)         (when decay is enabled)

points  = clamp(round(weighted + first_blood_bonus − hint_penalty × hints),
                0, 1_000_000)
```

First blood is the earliest solve of a given challenge across all solves being
scored. Solves whose challenge no longer exists are skipped. Hint counts are an
optional mapping on the pure helper, keeping the engine ready to consume the
hint engine branch without introducing a write dependency.

Ranking tie-breaks, in order:

1. Higher points.
2. Higher solve count.
3. Earlier last solve timestamp.
4. Team name (casefolded) for deterministic ordering.

Movement compares the new rank to the rank in the team's latest snapshot. A
team without a prior snapshot is `new`; equal ranks are `stable`.

## 4. Persistence and service layer

`SCHEMA_SQL` creates both tables with `CREATE TABLE IF NOT EXISTS` and an index
on `(team_id, recorded_at DESC)`. The feature registry executes it during
`Database.migrate()`, so the shared fixtures see the tables automatically.

`ScoreStore` extends `BaseRepository` and uses parameterised SQL exclusively:

* `get_rule`, `upsert_rule`, `list_rules` — the rule upsert uses SQLite's
  `ON CONFLICT(team_id) DO UPDATE`, keeping the original `id`.
* `insert_snapshot`, `list_snapshots`, `latest_snapshot`, `latest_snapshots`,
  `latest_ranks`, `snapshot_count`.

`ScoreboardService` validates drafts, reads existing repositories, computes
breakdowns and rankings, and creates snapshots. Invalid rules raise
`ValidationError` with a `fields` detail map; unknown teams raise
`NotFoundError`. No shared repository is ever written to.

## 5. HTTP API

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| `GET` | `/api/scoreboard/rules/{team_id}` | — | `ScoreRuleRead` |
| `PUT` | `/api/scoreboard/rules/{team_id}` | `ScoreRuleWrite` | `ScoreRuleRead` |
| `POST` | `/api/scoreboard/snapshot/{team_id}` | — | `ScoreSnapshotRead` |
| `GET` | `/api/scoreboard/ranking` | — | `RankingResponse` |
| `GET` | `/api/scoreboard/teams/{team_id}/breakdown` | — | `ScoreBreakdownRead` |
| `GET` | `/api/scoreboard/snapshots/{team_id}?limit=50` | — | `list[ScoreSnapshotRead]` |

All schemas are Pydantic models in `schemas.py`, and the router is mounted by
`register(app)`. Domain errors are rendered by the application's shared
`DashboardError` handler, so validation failures return HTTP 422 with the
standard error envelope:

```json
{"error": {"code": "validation_error", "message": "Invalid scoring rule",
           "details": {"fields": {"base_points": "Base points cannot be negative."}}}}
```

## 6. Frontend walkthrough

The plugin is discovered through `import.meta.glob`, so `/scoreboard` is added
to the router and the module launcher without editing shared files.

1. **Header** — team selector and a *Capture snapshot* action. Snapshot and
   rule saves show inline success/error feedback.
2. **Podium** — the top three teams are displayed in second/first/third order.
   The champion card is taller, carries a crown and a gold accent, and every
   card exposes movement and an *Inspect* action.
3. **Live ranking** — a sortable `RankTable` with rank, team, points, solve
   count and a `MovementBadge`. Rows for podium teams are tinted.
4. **Score breakdown** — an SVG stacked bar of category shares, per-category
   meters and a short list of the highest scoring solves.
5. **Scoring policy** — `RuleEditor` pairs each number input with a slider,
   validates as you type, and previews a four-solve streak.
6. **Snapshot history** — an SVG sparkline of point totals plus the five most
   recent snapshots with rank, points and rule name.

Loading states use skeletons, empty states use `EmptyState`, and failures use
`ErrorState` with a retry action. Selecting a different team refetches its rule,
breakdown and history; the selected team persists across reloads via local
state.

### Component inventory

| Component | Responsibility |
| --- | --- |
| `Podium` | Top-three cards, medals and inspect actions |
| `RankTable` | Sortable ranking rows with movement and solve counts |
| `RuleEditor` | Validated sliders, number inputs and live preview |
| `ScoreBreakdownChart` | SVG category distribution and top solves |
| `MovementBadge` | Accessible movement arrow and description |
| `SnapshotHistory` | Sparkline and snapshot timeline |

Each component has a colocated CSS module using the shared design tokens.
Tables scroll horizontally on narrow screens, grids collapse to one column,
and all motion is disabled under `prefers-reduced-motion: reduce`.

## 7. Accessibility notes

* Podium is an ordered list (`<ol>`) with an accessible name; placeholder slots
  are hidden from assistive technology.
* The ranking table uses semantic `<th scope="col">` headers and `aria-sort`.
  Team names are buttons, so selection is keyboard operable.
* Movement badges expose an `aria-label` such as "Climbed 2 positions" while
  the arrow glyph is hidden from screen readers.
* Rule editor inputs use real `<label>` elements; invalid fields set
  `aria-invalid` and link to a `role="alert"` message through
  `aria-describedby`. The switch is a native checkbox with `role="switch"`.
* The live preview and action feedback use `aria-live="polite"`; validation
  errors use `role="alert"`.
* Charts are `<svg role="img">` with textual summaries, so no information is
  conveyed by colour alone.
* Every interactive element has a visible `:focus-visible` ring, and reduced
  motion is respected in both CSS modules and keyframe animations.

## 8. Testing notes

Backend (`tests/test_v3_scoreboard_engine.py`, 38 tests) covers:

* the scoring formula, difficulty weights, decay, bonuses and penalties;
* integer rounding and clamping at both ends of the range;
* chronological solve scoring, first blood detection and hint counts;
* ranking tie-breaks and movement derivation;
* category aggregation, snapshot detail decoding and rule metadata;
* validation errors for negative values and out-of-range multiplier/decay;
* store upserts, snapshot history and latest-snapshot queries;
* service defaults, rule changes, breakdowns, snapshots and ranking movement;
* all six router endpoints, including 422 and 404 error paths.

Frontend (five colocated test files) covers scoreboard arithmetic and
presentation helpers, the typed API adapter, ranking rendering and sorting,
rule editor interaction and validation, and podium selection.

Verification command set:

```bash
python3 -m ruff check . && python3 -m ruff format --check .
python3 -m mypy
python3 -m pytest -q
cd frontend && npm run lint && npm run format:check && npm run typecheck && npm test && npm run build
python3 scripts/loc_gate.py 448fe50 HEAD --min 2000
```
