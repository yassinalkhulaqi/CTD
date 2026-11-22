# Writeups library (V3 branch 02)

The writeups library turns solved challenges into reusable team knowledge. It
provides a publication workflow, a peer-review loop, community ratings,
bookmarks and a magazine-style reading experience. The feature is a vertical
slice: a self-contained Python package, a routed React plugin, colocated tests
and these notes.

## Scope and files

| Layer | Location |
| --- | --- |
| Domain models and pure calculations | `src/ctf_team_dashboard/features/writeups_library/models.py` |
| Domain errors | `src/ctf_team_dashboard/features/writeups_library/errors.py` |
| Persistence | `src/ctf_team_dashboard/features/writeups_library/store.py` |
| Business rules | `src/ctf_team_dashboard/features/writeups_library/service.py` |
| Schemas and API | `schemas.py`, `router.py` |
| Frontend feature | `frontend/src/features/writeups-library/` |
| Backend tests | `tests/test_v3_writeups_library.py` |

The backend package exports `SCHEMA_SQL` and `register(app)`. The foundation
discovers it through `pkgutil` and mounts `/api/writeups`; no shared registry is
edited. The frontend exposes `plugin` with id `writeups`, path `/writeups` and
group `Knowledge`; the module launcher discovers it through `import.meta.glob`.

## Domain model

### `Writeup`

A writeup belongs to one author and one challenge. The service rejects a second
writeup for the same `(author_id, challenge_id)` pair with `409 duplicate_writeup`;
changing the challenge on an existing writeup re-checks the same invariant.

Fields: `id`, `challenge_id`, `author_id`, `title`, `summary`, `body`, `category`,
`difficulty`, `tags`, `status`, `rating_sum`, `rating_count`, `views`,
`created_at`, `published_at` and the per-member rating map.

Derived behaviour is pure and lives on the frozen dataclass:

* `slug` — lowercase hyphenated title, falling back to `writeup`.
* `word_count` / `reading_minutes` — words are counted with a regex that keeps
  contractions; reading time is a one-minute-floor estimate at 200 wpm.
* `excerpt` — strips markdown emphasis, links and headings, collapses
  whitespace and truncates on a word boundary with an ellipsis.
* `average_rating` — arithmetic mean; zero when unrated.
* `bayesian_score` — weighted blend of observed ratings with a prior of 3.5
  and weight 4, clamped to `[1, 5]`. A single five-star vote becomes 3.8, so a
  lone enthusiastic rating cannot top the leaderboard.
* `toc` / `sections` — ATX headings from `h2` to `h4` become unique slugged
  anchors; duplicate headings receive `-1`, `-2` suffixes.
* `star_distribution` / `rating_by` — inspection helpers for the rating UI.
* `with_status`, `with_ratings` and `with_view` are immutable updates. Moving
  to `published` stamps `published_at`; moving back to `draft` clears it.

Tags are normalised on create and update: hash prefixes removed, lowercased,
non-alphanumeric runs converted to hyphens, de-duplicated and capped at eight.

### Reviews

`WriteupReview` records one verdict per reviewer per writeup. `approve` keeps
the writeup in review until an explicit publish; `request_changes` returns the
writeup to `draft` immediately. Authors cannot review their own work, and a
review outside the `review` stage is rejected with `409 review_not_allowed`.

### Bookmarks

`WriteupBookmark` has a unique `(writeup_id, member_id)` constraint. The toggle
endpoint inserts or deletes the row and returns the resulting state plus a
bookmark count.

### Status transitions

```text
draft ──submit──▶ review ──publish──▶ published
  ▲                 │                    │
  └──request_changes┘──────withdraw───────┘
```

Any other move raises `422 invalid_status_transition`. Publishing additionally
requires at least one approving review (`422 approval_required`). Submitting a
draft requires a title, a summary and at least forty body words
(`422 writeup_incomplete`).

## Persistence

Three tables are created with `CREATE TABLE IF NOT EXISTS` and indexed on the
columns used by filters:

* `v3_writeups` — writeup columns plus `ratings_json`, a compact JSON object
  mapping member identifiers to scores. Individual ratings are updated in
  place so one member has one vote; aggregates are recomputed from the map.
* `v3_writeup_reviews` — unique on `(writeup_id, reviewer_id)`.
* `v3_writeup_bookmarks` — unique on `(writeup_id, member_id)`.

The store uses `BaseRepository` with parameterised SQL throughout. List queries
compose equality filters (status, category, tag, author, challenge) with an
AND-combined term search over title, summary, body and tags. Sorting is
whitelisted to `date`, `rating`, `views`, `title` and `reading`; the rating sort
uses the same Bayesian formula as the domain layer, expressed in SQL.

## HTTP API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/writeups` | Paginated list with `status`, `category`, `tag`, `author_id`, `search`, `sort`, `offset`, `limit` |
| `POST` | `/api/writeups` | Create a draft (201) |
| `GET` | `/api/writeups/stats` | Aggregates by category and status, totals and top rated |
| `GET` | `/api/writeups/mine?author_id=…` | All writeups by one author |
| `GET` | `/api/writeups/top?limit=…` | Highest Bayesian scores among published writeups |
| `GET` | `/api/writeups/bookmarks/{member_id}` | Saved writeups |
| `GET` | `/api/writeups/{id}?track_view=true` | Detail; increments views unless `track_view=false` |
| `PATCH` | `/api/writeups/{id}` | Edit supplied fields only |
| `DELETE` | `/api/writeups/{id}` | Delete with reviews and bookmarks (204) |
| `POST` | `/api/writeups/{id}/submit` | Draft → review |
| `POST` | `/api/writeups/{id}/publish` | Review → published (requires approval) |
| `POST` | `/api/writeups/{id}/withdraw` | Published → draft |
| `POST` | `/api/writeups/{id}/rate` | Set a member's 1–5 score |
| `POST` | `/api/writeups/{id}/bookmark` | Toggle a bookmark |
| `GET` / `POST` | `/api/writeups/{id}/reviews` | Review timeline / add a review |

Static routes are declared before `/{writeup_id}` so `stats`, `mine`, `top` and
`bookmarks` cannot be captured as identifiers. Errors use the shared envelope:
`{"error": {"code": ..., "message": ..., "details": {...}}}`. Feature-specific
codes are `duplicate_writeup`, `invalid_status_transition`,
`writeup_incomplete`, `approval_required`, `review_not_allowed`,
`duplicate_review`, `invalid_rating` and `not_found`.

## Frontend walkthrough

The `/writeups` page opens on published writeups sorted by date. A hero
introduces the library and offers a **Write a writeup** action; a four-card
stat strip summarises published count, review queue, ratings and the top
Bayesian score.

1. **Filter bar** — free-text search, category select, status segmented
   control and sort selector. Tag chips carry occurrence counts and can be
   toggled; **Reset** restores the default filters. Results refetch on every
   filter change and the count is announced politely.
2. **Magazine grid** — responsive cards show category and status badges, a
   title button, excerpt, tags, read-only stars with the Bayesian score,
   author, reading time, views, word count, relative date and a compact
   bookmark toggle. The active card is highlighted.
3. **Reader** — selecting a card opens a long-form layout with a sticky table
   of contents (duplicate-safe anchors), a markdown-rendered article, inline
   code, fences, lists and quotes, an interactive rating control and a
   bookmark action. The renderer builds React nodes only; it never injects
   HTML.
4. **Sidebar** — `PublishBar` draws the three-stage workflow and the next
   action, disabling **Publish** until an approving review exists.
   `ReviewPanel` lists verdicts and lets a reviewer approve or request changes
   with at least eight characters of feedback. A danger-styled ghost button
   deletes the writeup.
5. **Composer** — a two-column form with challenge/author fields, title,
   summary, category, difficulty, tags and a markdown body. Word count and
   reading time update live and the preview renders headings and paragraphs as
   you type. Submitted drafts open immediately in the reading view.

Loading skeletons, an empty state with a clear-filters action, retryable error
state and inline success/error notices cover asynchronous outcomes. Mutations
refresh both the list and the statistics; bookmarks update optimistically and
roll back on failure.

## Tests

`tests/test_v3_writeups_library.py` contains 30 backend tests across pure
domain calculations, store CRUD/filtering, service rules (conflicts,
transitions, review workflow, ratings, bookmarks, aggregates) and HTTP success
and error paths. The environment's editable install points at the main checkout,
so worktree verification uses `PYTHONPATH=src python3 -m pytest -q`; the full
suite reports 233 passing tests.

Colocated frontend tests cover:

* `logic.test.ts` — Bayesian smoothing, TOC anchors, word/reading estimates,
  excerpting, tag normalisation, filtering, sorting and formatting.
* `api.test.ts` — URL construction, identifier encoding, filter omission and
  the correct verb/path/body for each mutation.
* `RatingStars.test.tsx` — roving tabindex, arrow/Home/End navigation,
  Enter/Space/click commits, read-only output and disabled state.
* `WriteupCard.test.tsx` — content, keyboard activation and bookmark state.
* `WriteupsPage.test.tsx` — hero/grid rendering, search refetch, opening the
  reader and revealing the live-preview composer.

## Accessibility notes

* The rating control is a `radiogroup` with five named radio options, roving
  tabindex and high-contrast amber focus rings; it works with arrows, Home,
  End, Enter and Space.
* Bookmarks and status filters expose `aria-pressed`; the publish workflow uses
  `aria-current="step"`; the TOC is a labelled navigation landmark.
* Inputs use the design-system `Field` primitives with associated labels,
  hints and error messages. Review verdicts are real radio inputs inside a
  fieldset.
* All interactive elements have visible focus styling using the design tokens.
* Focus outlines use 3px high-contrast rings in addition to the global
  `:focus-visible` rule, and every local animation is disabled under
  `prefers-reduced-motion`.
* Responsive breakpoints collapse the reader sidebar at 1200px, the grid at
  760px and the composer preview at 1000px.
