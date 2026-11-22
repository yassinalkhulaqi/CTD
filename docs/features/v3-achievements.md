# Achievements and badge engine

This branch adds a complete achievement programme to the dashboard: a seeded
badge catalogue, a deterministic criteria engine, immutable awards, progress
tracking, leaderboard/statistics reporting, and a routed React gallery.

## Scope

| Layer | Delivered |
| --- | --- |
| Backend | Domain models, catalogue, repositories, service, typed API |
| Frontend | Plugin, routed gallery, filters, progress rings, detail drawer, stats, leaderboard, unlock toast |
| Tests | 33 backend tests and frontend logic/API/component tests |
| Docs | This document |

No shared registry, application factory, database engine, configuration file or
test fixture was edited. The backend package is discovered by the V3 feature
registry; the frontend `plugin.ts` is discovered by `import.meta.glob`.

## Data model

Three tables are created by `SCHEMA_SQL`:

| Table | Purpose |
| --- | --- |
| `v3_badges` | Badge definitions: tier, criterion, target, icon, points, secrecy |
| `v3_awards` | Immutable award records with evidence and observation value |
| `v3_progress` | Latest progress snapshot per member and badge |

The catalogue contains 16 built-in badges across bronze, silver and gold tiers.
Criteria cover four metric families:

- `solves`: number of solved challenges.
- `categories`: number of distinct solved categories.
- `streak`: consecutive active days.
- `hints`: at-most constraint on hints used.

Award identifiers are deterministic, so replaying an evaluation cannot create
duplicate awards. Secret badges remain masked in display fields until the
viewing member has earned them, while their definitions are never exposed as
revealed views.

## Domain rules

- Progress is clamped to `0..100` and computed against the criterion target.
- `hints` criteria invert the comparison: fewer hints means closer to complete.
- Rarity is derived from holder count and catalogue size; bands are
  `legendary`, `rare`, `uncommon` and `common`.
- Tier score is tier-adjusted, so gold badges contribute more than bronze.
- Leaderboard ranks are deterministic: points first, then award count, then a
  stable handle label.
- Evaluation is idempotent. Existing awards are preserved and only genuinely
  new qualifications are reported as `newly_awarded`.
- Manual grants use the same award path and carry optional evidence.

## API

All routes are mounted under `/api/achievements`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/badges` | Filtered catalogue with optional member progress |
| `GET` | `` | Root alias of the catalogue |
| `POST` | `/badges` | Create a custom badge |
| `GET` | `/badges/{badge_id}` | One badge, holder count and masked view |
| `POST` | `/evaluate` | Evaluate one member or a batch |
| `POST` | `/evaluate/batch` | Evaluate several members |
| `GET` | `/members/{member_id}` | Full member achievement profile |
| `GET` | `/members/{member_id}/progress` | Progress records only |
| `POST` | `/members/{member_id}/awards/{badge_id}` | Manually grant a badge |
| `GET` | `/leaderboard` | Ranked achievement leaderboard |
| `GET` | `/stats` | Aggregate programme statistics |
| `POST` | `/seed` | Seed missing built-in badges |

The service dependency lazily seeds the catalogue on first use, so a fresh
database returns a complete gallery without a setup request.

## Frontend experience

The `/achievements` route is composed from local components:

- **Statistic strip** — unlocked badges, points, participation and rarity.
- **Filter bar** — tier tabs, criterion select and free-text search.
- **Badge gallery** — responsive cards with circular progress rings, tier
  accents, status badges and locked states.
- **Detail drawer** — criterion explanation, rarity, holders, award timestamp
  and manual unlock action.
- **Metric evaluation form** — solves, categories, streak and hints inputs that
  call the criteria engine and surface newly unlocked badges.
- **Unlock toast** — an accessible `role="status"` celebration with a dismiss
  action.
- **Leaderboard card** — podium ranks, highlighted current member and empty
  state.

Accessibility details include labelled progress bars/meters, `aria-pressed`
filters, keyboard-operable cards, focus-visible rings, `aria-live` unlock
announcements, reduced-motion fallbacks and responsive layouts down to mobile
widths.

## Verification

```bash
python3 -m ruff check .
python3 -m ruff format --check .
python3 -m mypy
PYTHONPATH=src python3 -m pytest -q
cd frontend
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
cd ..
python3 scripts/loc_gate.py 448fe50 HEAD --min 2000
```
