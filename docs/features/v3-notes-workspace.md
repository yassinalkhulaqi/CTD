# Notes workspace (V3 feature 01)

The notes workspace gives the team a durable place to record what it learns
while working a challenge. Notes are versioned, searchable, taggable and
rendered through a distraction-free split-screen editor with a live preview.
Templates seed common report shapes and a revision timeline makes every body
change inspectable.

The branch is additive: the backend package is discovered by the dynamic
feature registry and the frontend page is discovered by the plugin registry.
No shared application file is modified.

## Domain model

### `NoteEntry`

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | `str` | Stable identifier, generated as `note-<12 hex chars>`. |
| `challenge_id` | `str` | The challenge the note belongs to. |
| `member_id` | `str` | The author who created the note. |
| `title` | `str` | Required, trimmed, at most 200 characters. |
| `body` | `str` | Required, trimmed, at most 20,000 characters. |
| `format` | `NoteFormat` | `markdown`, `plain` or `code`. |
| `tags` | `tuple[str, ...]` | Canonical tags, at most 12. |
| `pinned` | `bool` | Pinned notes sort first in every list. |
| `version` | `int` | Starts at 1; increments when the body changes. |
| `created_at` / `updated_at` | `datetime` | Timezone-aware UTC timestamps. |

Computed properties:

* `word_count` counts `[\w'-]+` tokens in the body.
* `reading_time_minutes` divides the word count by 200 and rounds to one decimal.
* `excerpt` collapses whitespace, strips Markdown punctuation and truncates to
  160 characters with an ellipsis.
* `headings` returns ATX headings from Markdown bodies. Fenced code blocks are
  skipped so a `#` inside a snippet is not treated as a heading.
* `tag_count`, `is_pinned`, `age_days`, `matches(query)` and `has_tag(tag)` power
  list rendering and local filtering. `has_tag` normalises both operands, so
  legacy mixed-case tags still match.

### `NoteTemplate`

Templates carry an `id`, `name`, `category` (`general`, `checklist`, `web`,
`crypto`, `pwn`, `reverse`, `forensics`, `osint`) and a `body` containing zero or
more `{{variable}}` placeholders. `variables` returns the distinct names in
first-appearance order; `variable_count` and `line_count` are display helpers.

### `NoteRevision`

An immutable snapshot of `body` at a `version`, with `author_id` and
`created_at`. `summary_against(previous)` uses a word-level `SequenceMatcher`
diff and returns a `ChangeSummary` of inserted and deleted words. The first
revision is treated as an insertion of every word.

`RevisionDescriptor` decorates a revision with its `ChangeSummary` and an
`is_latest` flag for the timeline UI.

### Aggregates

`ChallengeNoteSummary` records note, pinned, revision and word counts plus
unique authors and the five most frequent tags for a challenge.
`NotesWorkspaceSummary` adds workspace-wide totals, the union of all tags and a
generation timestamp. `average_words` and `pinned_ratio` are derived and never
stored.

## Domain rules

1. **Validation.** Title and body must be non-blank after trimming, and within
   their length bounds. Identifiers must be non-blank and at most 120
   characters. Invalid input raises `ValidationError` (HTTP 422).
2. **Tag normalisation.** Tags are trimmed, lower-cased, spaces become hyphens,
   unsupported characters are dropped, length is capped at 32, and duplicates
   are removed in first-appearance order. A maximum of 12 tags is kept.
3. **Revision creation.** Creating a note also writes revision 1. Updating a
   note writes a new revision only when the body actually changed; title,
   format, tag and pin edits do not create a snapshot. The version number only
   advances with a body change.
4. **Stale-version conflicts.** `PATCH` accepts an optional `expected_version`.
   When it does not equal the persisted version, the service raises
   `ConflictError` (HTTP 409) with both versions in the error details.
5. **Template rendering.** Placeholders match `{{\s*name\s*}}`. Every required
   variable must be supplied or the service raises `ValidationError` listing
   the missing names. Supplied values are substituted; unused keys and unknown
   placeholders are reported instead of being silently discarded.
6. **Deletion.** Deleting a note also removes all of its revisions.
7. **Uniqueness.** Template names are case-insensitively unique; a duplicate
   raises `ConflictError`.

## Persistence

Three tables are created by `SCHEMA_SQL` through `Database.migrate()`:

| Table | Purpose |
| --- | --- |
| `v3_notes` | Note fields, tags as compact JSON, `pinned` and `version` integers, ISO timestamps. |
| `v3_note_templates` | Template name, category and body. |
| `v3_note_revisions` | Append-only snapshots with a `UNIQUE(note_id, version)` constraint. |

Indexes cover `challenge_id`, `member_id`, `updated_at`, template `category` and
revision `note_id`. All statements use parameter binding. The repositories
subclass `BaseRepository` and reuse `parse_tags`, `dump_tags`, `parse_datetime`
and `format_datetime` from the shared module.

Search combines optional `LIKE` predicates for text, exact JSON-encoded tag
tokens, challenge, author and pinned state. Results sort by `pinned DESC`,
`updated_at DESC` and `id`.

## API reference

All error responses use the shared envelope
`{"error": {"code": ..., "message": ..., "details": {...}}}`.

| Method | Path | Purpose | Success |
| --- | --- | --- | --- |
| `GET` | `/api/notes` | List/search notes (`challenge_id`, `member_id`, `tag`, `q`, `pinned`). | `200` list |
| `POST` | `/api/notes` | Create a note and revision 1. | `201` note |
| `GET` | `/api/notes/summary` | Per-challenge and workspace aggregation (`challenge_id`). | `200` summary |
| `GET` | `/api/notes/{id}` | Read one note. | `200` note |
| `PATCH` | `/api/notes/{id}` | Edit fields, optionally with `expected_version`. | `200` note |
| `DELETE` | `/api/notes/{id}` | Delete the note and its revisions. | `204` |
| `POST` | `/api/notes/{id}/pin` | Set or toggle `pinned`. | `200` note |
| `GET` | `/api/notes/{id}/revisions` | Revision timeline with diff summaries. | `200` list |
| `GET` | `/api/note-templates` | List templates (`category`). | `200` list |
| `POST` | `/api/note-templates` | Create a template. | `201` template |
| `POST` | `/api/note-templates/render` | Render `{{variable}}` placeholders. | `200` result |

Notes whose title is whitespace pass the Pydantic minimum-length check but fail
service validation, producing a `validation_error` envelope. Missing notes
produce `not_found` (404), stale writes produce `conflict` (409) and duplicate
template names produce `conflict`.

`GET /api/notes/summary` is registered before `GET /api/notes/{id}` so the
literal path is never captured as an identifier.

## Frontend architecture

* `plugin.ts` registers `id: "notes"`, label `Notes`, group `Workspace` and path
  `/notes`.
* `types.ts` mirrors the API payloads and adds view models (`NoteDraft`,
  `SaveState`).
* `logic.ts` holds pure helpers: metrics, tag normalisation, template
  substitution, filtering, validation and the safe preview renderer.
* `api.ts` wraps `get`, `post`, `patch` and `del` from `../../api/client`, adding
  identifier encoding and query construction.
* `hooks.ts` owns loading, local editing, filtering, autosave and CRUD actions.
* `NotesPage.tsx` composes the routed screen from seven focused components.

### Safe preview

`renderMarkdownish` applies `escapeHtml` to every line **before** it emits any
Markdown-like markup. Only tags produced by the renderer itself (`h1`–`h6`,
`p`, `strong`, `em`, `code`, `pre`, `blockquote`, `li`, `a`) reach the DOM.
Link targets must start with `http://`, `https://`, `#` or `/`; anything else is
rendered as plain text. The preview is mounted with `dangerouslySetInnerHTML`
only because its HTML has been produced by that escaping pipeline.

### Autosave and save states

Editing a persisted note marks it `Unsaved`. A 900 ms debounce calls `PATCH`
with the current `expected_version`, transitioning to `Saving` and then `Saved`.
Validation or server failures surface as `Save failed` with the message in the
editor. Creating a new note uses an explicit `Create note` action instead of
autosave.

### Components

| Component | Responsibility |
| --- | --- |
| `NoteEditor` | Title, format, body and tag editing plus save/pin/delete actions. |
| `NotePreview` | Safe live preview and heading outline. |
| `TemplatePicker` | Template selection and per-variable inputs. |
| `RevisionTimeline` | Version list with diff labels; selecting a version previews it. |
| `NoteMetaBar` | Word count, reading time, version and save-state badge. |
| `TagFilter` | Toggleable tag chips with a clear action. |
| `TagInput` | Add tags with Enter/comma and remove them with accessible buttons. |

All styling lives in per-component CSS modules and uses the shared design
tokens for colour, spacing, radius and motion. The workspace is a four-column
grid on wide screens, collapses the timeline below 1400 px, stacks below 980 px
and tightens padding below 640 px.

## UI walkthrough

1. Open **Notes** from the Workspace group in the launcher. The page loads
   notes, templates and the summary in parallel and shows skeletons meanwhile.
2. Use the top search box and tag chips to narrow the saved-notes rail.
3. Click a note to load it into the editor. The right pane immediately shows a
   formatted preview and the far-right rail shows its revision history.
4. Type in the title or body. The meta badge moves from `Saved` to `Unsaved`
   and then `Saving`; after the response it returns to `Saved`.
5. Add tags with the tag input (Enter or comma) and remove them with the small
   × buttons. Pin or delete a note from the editor toolbar.
6. Choose a template in the picker, fill its `{{variable}}` inputs and press
   **Use template** to seed the title and body.
7. Select an older revision in the timeline to preview that snapshot, then
   press **Back to draft** to return to the current text.
8. Press **New note** to start a blank draft; **Create note** persists it.

Empty, loading and error states are first-class: an empty workspace offers a
creation action, search with no matches explains itself, and load failures
offer a retry button.

## Testing

Backend (`tests/test_v3_notes_workspace.py`) covers:

* pure helpers (word count, reading time, excerpt, tags, headings, templates,
  diffs and derived properties);
* store CRUD, search, pinning, tag enumeration, revision ordering and template
  lookup;
* service validation, first-revision creation, revision-only-on-body-change,
  stale-version conflicts, pin toggling, cascade deletion, template rendering
  rules and summary aggregation;
* router success paths for every endpoint plus 404, 409 and 422 error
  envelopes.

Fixtures used: `client`, `database` and `seeded`. The suite runs against the
same isolated SQLite database as the rest of the project.

Frontend (colocated Vitest tests) covers:

* `logic.test.ts` — metrics, tag/template helpers, safe preview escaping,
  filtering, drafts and display labels;
* `api.test.ts` — paths, query encoding, JSON payloads and return values of the
  typed adapter;
* `components.test.tsx` — editing, tag chips, template variables, revision
  selection and the escaped preview;
* `NotesPage.test.tsx` — loading, error, empty and populated states plus
  search/selection interactions.

## Accessibility notes

* Every form control has a label, including visually hidden labels for the
  search box, template select and tag input.
* Tag chips expose `aria-pressed`; the pin and delete icon buttons have
  explicit `aria-label` values; the save state is wrapped in `aria-live="polite"`.
* New notes, errors and empty states use `role="status"` or `role="alert"` via
  the shared feedback primitives.
* Focus-visible outlines are declared on every interactive control, and the
  global reduced-motion rule is complemented by feature-level media queries
  that disable local transitions.
* The preview outline uses semantic links to heading anchors, so keyboard users
  can jump between sections.
