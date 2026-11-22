# V3 Activity Timeline

The activity timeline turns the scattered events of a CTF session into a single
chronological narrative. It records solves, challenge changes, member and team
updates, notes, hints, submissions, achievements and system messages, then
presents them as a filterable live feed with relative timestamps, grouped date
headers and at-a-glance statistics.

The feature is a self-contained V3 slice:

* backend package `src/ctf_team_dashboard/features/activity_timeline/`
* frontend directory `frontend/src/features/activity-timeline/`
* backend tests `tests/test_v3_activity_timeline.py`
* this document

Neither the shared feature registries nor any foundation file is modified. The
backend package exports `SCHEMA_SQL` and `register(app)` and is discovered at
runtime; the frontend exports `plugin` from `plugin.ts` and is discovered with
`import.meta.glob`.

## Domain model

### `TimelineEvent`

An immutable, slotted dataclass with the fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | `str` | Stable identifier, generated as `evt-<hex>` by the service. |
| `team_id` | `str` | Owning team; the main tenancy filter. |
| `kind` | `str` | One of the nine `TimelineKind` values. |
| `actor_id` | `str` | Member or system identifier that caused the event. |
| `actor_name` | `str` | Denormalised display name for the actor. |
| `summary` | `str` | One-line description, whitespace normalised. |
| `payload_json` | `str` | Compact JSON object with structured details. |
| `importance` | `str` | `low`, `normal`, `high` or `critical`. |
| `occurred_at` | `datetime` | Timezone-aware UTC timestamp. |

Derived properties expose the parsed `timeline_kind`, `importance_level`,
`payload`, `date_key`, `hour_key`, `hour_of_day`, `importance_rank`,
`is_critical`, `actor_initials`, a relative time label and the age in seconds.
Unknown enum values are parsed with a safe default so legacy rows can still be
displayed.

### `TimelineKind` and `Importance`

`TimelineKind` covers `solve`, `challenge`, `member`, `team`, `note`, `hint`,
`submission`, `achievement` and `system`. Each value carries a display label,
an icon name, an accent colour and an `is_high_signal` flag used to emphasise
milestones.

`Importance` is an ordered four-tier scale (`low=0`, `normal=1`, `high=2`,
`critical=3`). It supplies a badge tone, a label and `from_rank`/`is_urgent`
helpers. Ranking is used for sorting and for choosing the representative event
when a burst of activity is collapsed.

### `TimelineFilter` and `TimelinePage`

`TimelineFilter` carries `kinds`, `actors`, `importance`, `team_id`, `from_at`
and `to_at` (exposed as `from`/`to` in the HTTP API), plus `limit` and `offset`.
It can test a single event with `matches`, report whether any selection filter
is active and produce a copy with a different offset.

`TimelinePage` holds deduplicated `EventCluster` items, the unfiltered match
count and pagination metadata (`has_more`, `next_offset`, `page_number`). The
offset advances over raw stored events so a page always represents a stable
slice of the underlying table.

### Buckets, actors and statistics

* `EventCluster` wraps a representative event with a repeat count, the newest
  and oldest timestamps of the group and convenience labels.
* `TimelineBucket` has a `key`, `label`, `level` (`day` or `hour`), direct
  `events` and nested `children`. Day buckets contain hour buckets; counts,
  critical counts and peak importance roll up through the hierarchy.
* `ActorSummary` aggregates event count, critical count, last-seen time and the
  distinct kinds associated with an actor.
* `TimelineStats` aggregates totals, counts by kind/hour/importance, unique
  actors, critical ratio, busiest kind/hour, average per active hour and a
  ranked list of top kinds.
* `PruneResult` records the cutoff, deleted/retained counts and the age limit.

## Behaviour rules

### Relative time and grouping

`relative_time` formats events as `just now`, `Nm ago`, `Nh ago`,
`yesterday`, `Nd ago` or an absolute `Mon 05` label after a week. Day and hour
keys are UTC based (`YYYY-MM-DD` and `YYYY-MM-DDTHH:00`) so grouping is stable
across browser timezones. `build_timeline_groups` produces day buckets ordered
newest first, each with hour children ordered newest first and events sorted by
timestamp then importance.

### Importance ranking

`rank_events` orders events by importance descending, then recency, then id.
When several events are merged, the most important one becomes the cluster
representative so a critical event inside a burst is never hidden by a normal
neighbour.

### Consecutive-event deduplication

`deduplicate_events` merges neighbouring events that share kind, actor and
summary and fall within a 120-second window by default. The merged cluster
reports `count`, `count_label` (`×3`) and `is_merged`. The frontend mirrors
this rule in `clusterEvents`, allowing a quick client-side re-cluster when data
is merged from several pages.

### Filtering, pagination, aggregation and pruning

The store translates filters into parameterised SQL with `IN` lists for kinds,
actors and importance, range predicates for the time window and an
`ORDER BY occurred_at DESC, id DESC` display order. The service validates the
page size (1–200), rejects negative offsets and reversed time windows, and
raises `ValidationError` with a stable error code for each violation.

Statistics ignore pagination so the counters always describe the whole
matching set. Pruning deletes rows older than a cutoff derived from the
configured age in days; `prune_for_team` offers a non-destructive preview by
counting the stale rows for one team.

## Storage

`SCHEMA_SQL` creates `v3_timeline_events` with one row per event:

```sql
CREATE TABLE IF NOT EXISTS v3_timeline_events (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    actor_name TEXT NOT NULL,
    summary TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    importance TEXT NOT NULL DEFAULT 'normal',
    occurred_at TEXT NOT NULL
);
```

Indexes cover team, occurrence time, kind, actor, importance and the composite
`(team_id, occurred_at DESC)` used by the main feed. Timestamps are stored with
`format_datetime` as aware ISO-8601 strings; payloads are encoded with sorted
keys and no whitespace by `encode_payload` and limited to 4 KiB.

`TimelineEventRepository` extends the shared `BaseRepository` and exposes
`get`, `insert`, `matching`, `count_matching`, `recent`, `list_since`,
`count_since`, `delete`, `delete_before`, `actor_summaries`, `distinct_kinds`
and `payload_fields`. All statements are parameterised.

## Service rules

`TimelineService` is the only writer of validated data:

* `record_event` validates identifiers, kind, actor name, summary length,
  importance and payload shape, then inserts the event.
* `record_many` applies the same rules to a batch of mappings.
* `query` validates the filter, reads a page, deduplicates it and returns a
  `TimelinePage`.
* `list_clusters`, `groups`, `list_recent`, `stats`, `list_actors` and
  `list_kinds` provide the projections consumed by the API.
* `get_event`, `delete_event`, `prune` and `prune_for_team` complete the
  lifecycle; missing events raise `NotFoundError`.

Invalid values raise the shared `ValidationError`, `NotFoundError` or
`ConflictError` classes, which the application factory maps to the standard
JSON error envelope.

## HTTP API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/timeline` | Filtered, deduplicated, paginated event page. |
| `POST` | `/api/timeline` | Record a new event; returns `201` and the event. |
| `GET` | `/api/timeline/groups` | Day buckets with nested hour buckets. |
| `GET` | `/api/timeline/stats` | Counts by kind, hour and importance. |
| `GET` | `/api/timeline/actors` | Actors ordered by activity. |
| `GET` | `/api/timeline/kinds` | Distinct kinds currently stored. |
| `POST` | `/api/timeline/prune?max_age_days=30` | Delete stale events. |
| `GET` | `/api/timeline/{id}` | Fetch one event. |
| `DELETE` | `/api/timeline/{id}` | Remove one event. |

Repeated query parameters are used for multi-value filters, for example
`/api/timeline?kinds=solve&kinds=note&importance=critical`. The lower and upper
time bounds use the aliases `from` and `to` and accept ISO-8601 datetimes.
Every response is described by a Pydantic schema in `schemas.py`, including
the derived fields needed by the UI (`kind_label`, `kind_icon`, `kind_color`,
`importance_tone`, `actor_initials`, `relative_label`, `date_key`, `hour_key`).

Example request:

```json
{
  "team_id": "team-0001",
  "kind": "solve",
  "actor_id": "member-0001",
  "actor_name": "Ada Lovelace",
  "summary": "Solved the RSA challenge",
  "payload": { "challenge_id": "crypto-rsa", "points": 250 },
  "importance": "high",
  "occurred_at": "2026-01-05T12:00:00Z"
}
```

## Frontend walkthrough

The plugin is registered as:

```ts
{ id: "timeline", label: "Timeline", path: "/timeline", group: "Analysis" }
```

`TimelinePage` composes the screen:

1. A header with the event total and a **Refresh** action.
2. `TimelineStatsView`, a strip with four headline metrics and horizontal bars
   for the busiest kinds.
3. `FilterChips` for kinds, importance tiers, actors and (when several teams
   are present) a team select, plus a clear-all control showing the number of
   active filter groups.
4. `LiveBanner`, which appears only when a background poll detects new events
   and offers **Show new events** and **Dismiss** actions.
5. `TimelineList`, a scrollable, virtual-style list built from flattened
   buckets. Day headers are sticky at the top, hour headers stick beneath
   them, and a vertical spine with coloured nodes connects the events.
6. Loading skeletons, an explanatory empty state and a retryable error state.

Each `TimelineItem` shows an actor avatar, the kind label with its accent
colour, the summary, a structured payload preview where available, an
importance badge, a repeat indicator for merged events, a relative timestamp
and a dismiss button. The list exposes an **Load older activity** action while
the API reports another page.

`useTimeline` owns loading, filter toggles, team selection, pagination,
optimistic deletion, event recording and the 15-second background poll. The
poll skips hidden tabs and stops after a network failure until the banner is
refreshed, avoiding noisy retry loops.

`logic.ts` contains the client-side mirror of the domain rules: relative time,
day/hour keys and labels, importance ranking, consecutive-event clustering,
bucket construction, row flattening, local filtering, arrival detection and
page merging. `api.ts` wraps the shared HTTP client and encodes repeated
parameters explicitly.

## Accessibility notes

* Filter chips are real buttons with `aria-pressed` and descriptive labels;
  the team selector is a labelled `combobox`.
* The list and its rows expose `role="list"`/`role="listitem"`; day and hour
  headings use `h2`/`h3` so screen-reader users can navigate by heading.
* Timestamps are `<time>` elements with a machine-readable `datetime`
  attribute and a human-readable relative label.
* The live banner uses `role="status"` and `aria-live="polite"` so arrivals are
  announced without interrupting the user.
* Icon-only controls carry accessible names, focus rings use `:focus-visible`
  with the shared focus shadow tokens, and hover-only actions become visible
  on focus or on narrow screens.
* All motion (chip lift, banner slide-in, stat bars) is disabled under
  `prefers-reduced-motion`, and the layout collapses to a single column on
  small viewports.

## Testing notes

Backend tests cover relative time, bucket keys and labels, enum metadata,
derived event properties, deduplication (including importance promotion),
day/hour grouping, aggregation, prune cutoffs, filter matching, store CRUD and
filtering, actor aggregation, service validation and error paths, pagination,
grouping, statistics, pruning and every HTTP endpoint including the error
envelope.

Frontend tests cover the pure logic (relative time, grouping, clustering,
filtering and arrivals), the API adapter (URL construction, repeated filters
and all endpoints), the presentational components (chip toggles, importance
badges, sticky headers, list rows and banner actions) and rendered page states
(loading, error, empty and full interaction).
