# V3 feature: Internationalisation and locales

The `i18n_locales` feature adds a complete localisation layer to the CTF Team
Dashboard. It covers the whole path from registering a language, through
storing catalogued messages, to rendering a translated string with fallback,
plural selection and placeholder interpolation. A companion React screen at
`/languages` exposes the catalogue and a set of live formatting tools.

The feature is self-contained. On the backend it contributes the
`src/ctf_team_dashboard/features/i18n_locales/` package, which is discovered
automatically by the dynamic feature registry. On the frontend it contributes
`frontend/src/features/i18n-locales/plugin.ts`, which is discovered by
`import.meta.glob`. No shared registry, router table or stylesheet is edited.

## Domain model

### `Locale`

A locale is a registered language variant. Its fields are:

| Field | Type | Purpose |
| --- | --- | --- |
| `code` | `str` | BCP-47 style identifier such as `en`, `fr-CA` or `zh-Hant-TW`. |
| `name` | `str` | English display name shown in the language switcher. |
| `direction` | `TextDirection` | `ltr` or `rtl`; detected from the language when omitted. |
| `plural_rules` | `PluralRule` | `none`, `simple`, `slavic` or `arabic`. |
| `created_at` | `datetime` | Timezone-aware UTC creation timestamp. |

Derived properties expose the base language, canonical code, RTL flag and the
fallback chain. `category_for(count)` returns the plural category of a number
under the locale's rule family.

Locale codes accept two or three letter language subtags followed by an
optional four-letter script, two-letter region or three-digit region. Parsing
is strict: malformed codes are rejected with a validation error before any
database work happens. The canonical form title-cases the script and
uppercases two-letter regions.

### `Message`

A message is the value of one key in one namespace for one locale:

| Field | Type | Purpose |
| --- | --- | --- |
| `id` | `str` | Deterministic primary key derived from locale, namespace and key. |
| `locale` | `str` | The locale the value belongs to. |
| `namespace` | `str` | Logical catalogue group such as `ui` or `emails`. |
| `key` | `str` | Message identifier, with plural variants as `key.one` and so on. |
| `value` | `str` | The translated template. |
| `updated_at` | `datetime` | Timezone-aware UTC update timestamp. |

A message knows its qualified `namespace:key` name, extracts the placeholders
used by its value, reports whether it is empty and can render itself with a
dictionary of values.

### `FormatRule`

A format rule carries the number and date patterns of a locale. Number
patterns use a `#,##0.00` mini-language: `#` marks optional digits, `0` marks
mandatory digits, a comma enables grouping and the fractional zeros determine
decimal precision. Rounding is half away from zero so results are stable
across platforms. Date patterns support `YYYY`, `YY`, `MMMM`, `MMM`, `MM` and
`DD` tokens with arbitrary literal separators, and month names are localised
for English, French and German with an English fallback.

### Reporting types

`TranslationResult` records the requested locale, the locale that actually
supplied the value, the matched variant, the translation source, the rendered
value and the applied/missing placeholders. `CompletenessStat` records the
number of reference keys and how many were translated in a locale.
`MissingKey` describes a reference string without a local value and the
fallback locale that currently supplies it. `CatalogSnapshot` aggregates
locales, messages, RTL codes and namespaces.

## Behavioural rules

### Fallback chain

A lookup tries the requested locale first, then its base language, then the
configurable default locale (`en`). Entries are de-duplicated case
insensitively while preserving order, so `fr-CA` becomes
`("fr-CA", "fr", "en")` and `en-US` becomes `("en-US", "en")`. An empty
message never satisfies a lookup, so translators can deliberately fall back
by clearing a value.

### Translation and plural selection

When a count is supplied, the service selects a plural category from the
locale's rule family and tries `key.<category>` before the unqualified key at
each step of the fallback chain. The first non-empty match wins. The source is
reported as `exact`, `plural`, `base`, `default` or `missing`, which lets the
UI explain why a particular string was shown.

Plural families:

- `simple` — `one` for 1, otherwise `other`.
- `none` — always `other`.
- `slavic` — `one` for 1, `few` for 2–4 (excluding teens), otherwise `many`.
- `arabic` — `zero`, `one`, `two`, `few` (3–10), `many` (11–99) and `other`,
  evaluated modulo 100 so 101 is again `one`.

### Interpolation

Templates may contain `{name}` placeholders and `{{`/`}}` escapes. Supplied
values are stringified and substituted; unknown names are left in place and
reported as missing. `TranslationResult.interpolated` and `.complete` expose
the substitution status to callers.

### Missing-key reporting

`missing_keys(locale, namespace)` compares a target locale against the
default reference catalogue, skips empty reference strings and records which
fallback locale currently supplies each absent key. `completeness(reference)`
groups the same comparison by namespace and computes a percentage rounded to
one decimal place.

### RTL detection

`direction_for(code)` checks the primary language subtag against a set of RTL
languages (Arabic, Hebrew, Persian, Urdu, Pashto, Yiddish and related
variants). Registration uses this detection unless a direction is explicitly
provided. The frontend mirror uses the same language set for instant previews.

## Storage

Three tables are created by `SCHEMA_SQL` through `Database.migrate()`:

```sql
v3_locales(code PK, name, direction, plural_rules, created_at)
v3_messages(id PK, locale, namespace, key, value, updated_at,
            UNIQUE(locale, namespace, key))
v3_format_rules(locale PK, number_pattern, date_pattern, updated_at)
```

An index on `v3_messages(locale, namespace, key)` accelerates fallback
lookups. All access goes through `BaseRepository` with parameterised SQL, so
no user input is interpolated into a statement.

## HTTP API

All routes are mounted under `/api/i18n` and tagged `i18n`. Domain errors use
the shared error envelope: validation failures return 422, unknown resources
404 and duplicate locale registration 409.

| Method | Path | Purpose | Key parameters / body |
| --- | --- | --- | --- |
| `GET` | `/api/i18n/locales` | List registered locales. | — |
| `POST` | `/api/i18n/locales` | Register a locale. | `code`, `name`, optional `direction`, `plural_rules` |
| `GET` | `/api/i18n/messages` | List messages. | `locale`, `namespace` filters |
| `PUT` | `/api/i18n/messages` | Upsert a message batch. | `locale`, `namespace`, `messages` map |
| `GET` | `/api/i18n/translate` | Resolve one key. | `locale`, `namespace`, `key`, `count`, `values` JSON |
| `GET` | `/api/i18n/format` | Format a number or date. | `locale`, `kind`, `value`, optional `pattern` |
| `GET` | `/api/i18n/completeness` | Completeness report. | `reference` (default `en`) |
| `GET` | `/api/i18n/missing-keys` | Untranslated reference keys. | `locale`, optional `namespace` |
| `GET` | `/api/i18n/direction` | Direction and fallback chain. | `locale` |
| `GET` | `/api/i18n/parse` | Parse a locale identifier. | `locale` |
| `GET` | `/api/i18n/format-rules` | List stored format rules. | — |
| `PUT` | `/api/i18n/format-rules` | Store format rules. | `locale`, `number_pattern`, `date_pattern` |
| `GET` | `/api/i18n/catalog` | Catalogue overview. | — |

Responses are typed Pydantic models declared in `schemas.py`. Enums are
serialised as their string values, so the frontend can consume them without
extra translation.

Example translation request:

```text
GET /api/i18n/translate?locale=fr-CA&namespace=ui&key=greeting&values={"name":"Ada"}
```

Because `fr-CA` has no message of its own, the response reports source `base`,
resolved locale `fr` and the interpolated value `Bonjour, Ada !`.

## Frontend

The plugin is registered as:

```ts
{
  id: "languages",
  label: "Languages",
  path: "/languages",
  group: "Settings",
}
```

The `LanguagesPage` composes six focused presentational components:

- `LocaleSwitcher` — an accessible select with a live fallback-chain summary.
- `LocalePreview` — a sample interface rendered with `dir` and `lang`
  attributes so RTL locales mirror alignment and ordering.
- `FormatPlayground` — number/date mode toggles, editable patterns, quick
  presets, an instant preview and a save action for the locale rule.
- `CompletenessTable` — a table with per-namespace progress bars, percentages
  and semantic status badges; locale buttons select the active language.
- `MessageEditor` — a controlled editor with placeholder detection, key
  normalisation, validation and save feedback.
- `MissingKeyList` — untranslated keys with their reference value and the
  fallback locale that currently covers them.

`DirectionBadge` is a shared helper used by the switcher and preview.

The page has three tabs. **Overview** shows locale statistics, the direction
preview, a compact locale registration form and the completeness table.
**Messages** pairs the editor with the stored messages and the missing-key
list. **Formatting** hosts the playground. Data is loaded with the shared
`useQuery` hook through `hooks.ts`, and mutations invalidate every `i18n`
cache key so the views stay consistent.

`format.ts` mirrors the backend rules in pure TypeScript. This gives the
playground instant feedback and keeps the maths testable without a server.
The adapter in `api.ts` is the only module that talks to `/api/i18n`.

### UX and accessibility

- Loading, empty, error and success states are rendered explicitly; errors
  offer a retry action.
- The language selector is a labelled native control with associated options.
- The playground's live result is an `aria-live="polite"` status region.
- The completeness table uses column headers, progress bars with
  `aria-valuenow` and buttons for locale selection, so every action is
  keyboard operable.
- The direction preview sets `dir` and `lang` on the sample surface, which
  lets assistive technology pronounce the right language and honours RTL
  reading order.
- Placeholder and missing-key lists use semantic lists and text badges rather
  than colour alone.
- All styling is local CSS modules built on the shared design tokens, with
  responsive breakpoints, hover/focus states and reduced-motion handling.

## Testing notes

Backend tests live in `tests/test_v3_i18n_locales.py` and cover:

- locale code parsing, canonicalisation, fallback chains and RTL detection;
- all plural rule families including Arabic modulo-100 behaviour;
- placeholder extraction, interpolation, escapes and missing values;
- number rounding and date pattern tokens with localised months;
- repository upserts and deterministic message identifiers;
- service registration, validation, conflict and not-found paths;
- translation resolution for exact, plural, base, default and missing cases;
- completeness and missing-key aggregation;
- every API endpoint plus 404, 409 and 422 error paths.

Frontend tests are colocated with the feature and cover pure formatting
logic, the typed API adapter, the locale switcher, the formatting playground,
the completeness table, the message editor and the missing-key list. Rendered
tests use React Testing Library and assert accessible names and roles.

## Extension points

Adding a language only requires registering a locale and uploading a message
batch; the fallback chain means a partial catalogue is immediately usable.
Additional plural families can be introduced by extending `PluralRule` and
`plural_category` in both the Python and TypeScript modules. New formatting
tokens are added to the pattern validators and substitution tables in the
same two files.
