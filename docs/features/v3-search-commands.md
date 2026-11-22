# V3 feature: unified search and command palette

## Overview

The search feature adds one index for the whole dashboard and a keyboard-first
command palette. Everything is additive: the backend feature package installs
its own tables and router through the V3 discovery hooks, and the frontend
plugin contributes a `/search` route through the dynamic plugin registry. No
shared file is changed.

The feature has four layers:

1. A pure domain layer (tokenisation, weighted scoring, snippets, query filters
   and fuzzy command matching) with no I/O.
2. A repository-backed store for `v3_search_documents` and `v3_commands`.
3. A service that ingests existing challenges, teams and members through their
   read-only repositories, adds custom documents, answers queries and executes
   commands.
4. A React workspace with a global `Cmd/Ctrl+K` palette and a result list.

## Domain rules

### Documents

`SearchDocument` is a frozen, slotted dataclass with `id`, `kind`, `title`,
`body`, `tags`, `path` and `updated_at`. Kinds are `challenge`, `team`, `member`
and `custom`. The composite key `<kind>:<id>` is used by the UI to identify a
hit without colliding with another kind.

Ingestion converts entities without mutating them:

| Source | Title | Body | Tags |
| --- | --- | --- | --- |
| Challenge | challenge title | description | challenge tags, category, difficulty, status |
| Team | team name | description | slug |
| Member | display name | handle and role | handle, role |

Custom documents may be indexed directly. The service rejects empty ids or
titles, bodies longer than 20,000 characters and paths that do not start with
`/`. All writes are parameterised upserts, so reindexing is idempotent.

### Query parsing

`parse_filters` removes `kind:<value>` and `tag:<value>` tokens from the raw
text. Filters are deduplicated and normalised. The service rejects unknown
kinds with a typed `ValidationError`, and validates that `limit` is between 1
and 100. Empty filter values are ignored. The parsed query retains the
remaining text, normalised tokens, filters and limit.

Tokenisation folds accents and case, replaces punctuation with spaces and
drops common stopwords. If every token is a stopword, the original tokens are
kept so that a query such as `the` still returns results.

### Scoring and ranking

Each query token is scored independently against three fields:

| Field | Weight |
| --- | ---: |
| Title | 5 |
| Tags | 3 |
| Body | 1 |

A token that is a prefix of a field token (minimum length two) receives the
field weight multiplied by a prefix bonus of `0.5`. A coverage bonus of `0.5`
is awarded in proportion to the number of query tokens matched. Contiguous
phrases matching two or more tokens add `4` in the title and `1.5` in the body.
Scores are rounded to three decimals.

Results are sorted by descending score and then by document id, which makes
the ordering stable even for equally scored documents. The first query token
that appears in a body determines the snippet window: the body is collapsed to
single spaces, a bounded excerpt is cut on word boundaries and highlight spans
are returned as offsets relative to that excerpt, including the leading
ellipsis. Title matches are returned as separate `title` highlights.

### Commands

A command has an id, name, description, group, shortcut and keywords. The
built-in catalogue contains navigation commands, search filters and a reindex
action; it is installed lazily when the registry is empty. Registration
rejects duplicate ids with `ConflictError`.

Fuzzy matching scores exact names at 12, name substrings at 8 (9 at the start),
initial or acronym matches at 6, exact keywords at 5, keyword substrings at 3
and description substrings at 1.5. Ties are broken by command id. Execution
returns a descriptor with the command id, name, action (`navigate` or
`action`), target route, message and arguments. The target is derived from the
route mentioned in the description.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/search` | Search with `q`, repeated/comma separated `kind` and `tag`, and `limit`. |
| `POST` | `/api/search/index` | Bulk upsert custom documents, optionally reindex repositories and optionally clear the index. |
| `GET` | `/api/search/commands` | List commands, optionally filtered by `q` and `group`. |
| `POST` | `/api/search/commands` | Register a command. |
| `POST` | `/api/search/commands/{id}/execute` | Execute a command and return its descriptor. |
| `POST` | `/api/search/commands/bootstrap` | Ensure the built-in catalogue is present. |
| `GET` | `/api/search/stats` | Return index and command counters. |
| `DELETE` | `/api/search/documents/{id}` | Remove one indexed document. |

Every request and response uses a Pydantic schema in `schemas.py`. Domain
errors are mapped by the application's shared error handler: validation errors
return 422, missing resources 404 and duplicate commands 409, all with the
standard `error.code` envelope.

Example response for `GET /api/search?q=kind:challenge%20shell`:

```json
{
  "query": {
    "text": "shell",
    "kinds": ["challenge"],
    "tags": [],
    "limit": 20,
    "tokens": ["shell"],
    "has_filters": true
  },
  "results": [
    {
      "document_id": "challenge-c1",
      "kind": "challenge",
      "title": "Web Shell",
      "snippet": "Bypass the shell filter",
      "score": 5.5,
      "highlights": [
        { "start": 12, "end": 17, "text": "shell", "field": "body" }
      ],
      "path": "/challenges/c1",
      "relevance": "strong"
    }
  ],
  "total_indexed": 1,
  "returned": 1
}
```

## UI walkthrough

`SearchPage` is mounted at `/search` and labelled "Search" in the Workspace
group. It provides:

* a search field with inline `kind:` and `tag:` filters and a debounced API
  request;
* result-kind chips with per-kind counters and a result limit selector;
* recent query chips persisted in local storage;
* ranked result rows with highlighted title and snippet text, entity kind,
  path, match count and a relevance score;
* loading skeletons, an empty state, an error state with retry and a rebuild
  action that reindexes the repositories;
* a command palette opened from the header button or from the global
  `Cmd/Ctrl+K` shortcut registered by the plugin component in a `useEffect`.

The palette is a portalled dialog. Commands are grouped, fuzzy filtered and
navigated with arrow keys; `Enter` executes the selected command and `Escape`
closes the dialog. A navigation descriptor moves the SPA to the returned route,
while other commands surface their message in a status region. The palette
shows keyboard hints and the number of matching commands.

Components are split into `CommandPalette`, `SearchResults`, `ResultRow`,
`Highlight`, `SearchFilters` and `ShortcutBadge`, each with a local CSS module.
The palette uses overlay tokens from the shared theme; no global stylesheet is
modified.

## Tests

Backend (`tests/test_v3_search_commands.py`) covers tokenisation and filters,
field weights, prefix and phrase bonuses, stable ranking, snippet offsets,
command fuzzy matching, parsed-query validation, store upserts and scans,
read-only repository indexing, custom indexing, registration conflicts, command
execution, router success paths, router error envelopes and index deletion.

Frontend tests cover pure query parsing and ranking helpers, the typed API
adapter with mocked request helpers, palette keyboard interaction and click
execution, highlight rendering, filter controls and plugin metadata. API
mocking verifies that filters are serialised and that ranked results are
ordered by the shared helper.

## Accessibility

The search field has an explicit label and a `role="search"` form. Filter chips
expose `aria-pressed`; the palette is a labelled `aria-modal` dialog with an
option list, `aria-selected` on the active command and a focusable input. All
controls are reachable by keyboard, active commands communicate their state,
and status messages use `role="status"`. Focus rings use the shared focus
shadow, responsive rules collapse the layout below 640px, and all animations
are disabled under `prefers-reduced-motion`.
