# V3 Feature Program — Master Plan

## Baseline and goals

| Item | Value |
| --- | --- |
| Integration baseline | `448fe500d01b63b04f685c84959b115eaff8e744` (`main`) |
| Foundation branch | `dev/v3-00-platform-kernel` |
| Feature branches | `dev/v3-01-*` … `dev/v3-20-*` (20 branches) |
| Minimum net LOC per feature branch | 2,000 |
| Minimum program net LOC | 40,000 |
| Target net LOC | 50,000+ |
| Push policy | Only `dev/*` branches; never push `main`; never force-push |

The program grows the CTF Team Dashboard into a complete operating surface for
a team: authoring, analysis, coordination, reporting, personalisation and
administration. Every branch is a vertical slice that ships backend domain
logic, persistence, an HTTP API, a routed React screen, interaction design,
tests and documentation. Nothing is added only to inflate line counts.

## Architecture invariants

1. **Baseline first.** Every net-LOC figure is measured against `main` at the
   baseline commit with `git diff --numstat`.
2. **Foundation is shared.** `dev/v3-00-platform-kernel` adds dynamic backend
   feature discovery and dynamic frontend plugin discovery. Feature branches
   branch from the foundation tip and never edit a shared registry, the app
   factory, the database engine or the router table.
3. **Packages are self-contained.** A backend feature is a single package
   `src/ctf_team_dashboard/features/<slug>/` exporting `SCHEMA_SQL` and
   `register(app)`. A frontend feature is a single directory
   `frontend/src/features/<slug>/` exporting `plugin` from `plugin.ts`.
4. **Tests live with the feature.** Backend tests are
   `tests/test_v3_<slug>.py`; frontend tests are colocated `*.test.ts(x)`.
5. **No shared generated assets.** CSS lives in per-feature `*.module.css`
   files. `frontend/dist`, caches and `node_modules` are never staged.
6. **Every branch passes gates** before it is pushed. A blocked gate is
   recorded verbatim and retried; it is never disabled.

## Branch train

Dependencies column lists the branches whose contracts a branch consumes. All
branches are technically independent because the registries are dynamic; the
dependencies only describe the narrative order of the final merge train.

| # | Branch | Scope | LOC target | Test area | Frontend / UX / design deliverable | Dependencies | Merge order |
| ---: | --- | --- | ---: | --- | --- | --- | --- |
| 00 | `dev/v3-00-platform-kernel` | Dynamic feature registries, LOC tooling, quality gates, architecture docs | 2,000 | registry tests | Module launcher shell, plugin registry tests, design tokens audit | — | 1 |
| 01 | `dev/v3-01-notes-workspace` | Markdown notes, templates, revisions, tags, autosave | 2,400 | notes domain + API + UI | Distraction-free editor, revision timeline, save-state indicator | 00 | 2 |
| 02 | `dev/v3-02-writeups-library` | Writeups, publication states, ratings, tagging | 2,400 | writeups domain + API + UI | Library grid, rating control, publish workflow, reading layout | 00, 01 | 3 |
| 03 | `dev/v3-03-hint-engine` | Tiered hints, unlock costs, team budget, reveal ledger | 2,400 | hint domain + API + UI | Cost curve visualisation, progressive reveal cards, budget meter | 00 | 4 |
| 04 | `dev/v3-04-scoreboard-engine` | Dynamic scoring, penalties, tie-breaks, ranking snapshots | 2,400 | scoring domain + API + UI | Podium, rank movement arrows, scoring breakdown drawer | 00 | 5 |
| 05 | `dev/v3-05-ctf-events` | Event lifecycle, schedules, registration, countdowns | 2,400 | events domain + API + UI | Event cards, status pills, countdown ring, registration flow | 00 | 6 |
| 06 | `dev/v3-06-team-roster` | Roster, roles, invites, capacity, availability | 2,400 | roster domain + API + UI | Roster table, role chips, invite dialog, capacity bar | 00, 05 | 7 |
| 07 | `dev/v3-07-submission-pipeline` | Flag submission, validation, dedupe, retry queue | 2,400 | pipeline domain + API + UI | Submission console, status pipeline, retry affordances, live log | 00, 04 | 8 |
| 08 | `dev/v3-08-activity-timeline` | Activity records, filters, grouping, aggregation | 2,400 | timeline domain + API + UI | Virtualised timeline, filter chips, group headers, relative time | 00 | 9 |
| 09 | `dev/v3-09-search-commands` | Index, ranking, query parsing, command registry | 2,400 | search domain + API + UI | Command palette, keyboard shortcuts, highlighted results | 00, 01, 02 | 10 |
| 10 | `dev/v3-10-notifications` | Notifications, preferences, digest, delivery log | 2,400 | notification domain + API + UI | Notification centre, toast queue, preference switches, badges | 00 | 11 |
| 11 | `dev/v3-11-achievements` | Badge catalogue, criteria engine, progress, awards | 2,400 | achievement domain + API + UI | Badge gallery, progress rings, unlock animation, detail sheet | 00 | 12 |
| 12 | `dev/v3-12-reports-exports` | Report templates, rendering, CSV/JSON/Markdown export | 2,400 | report domain + API + UI | Report builder, live preview, export menu, print stylesheet | 00, 04 | 13 |
| 13 | `dev/v3-13-settings-preferences` | Preferences, theme tokens, density, workspace layout | 2,400 | settings domain + API + UI | Settings sections, segmented controls, live theme preview | 00 | 14 |
| 14 | `dev/v3-14-onboarding-tour` | Setup wizard, guided tour, checklists, empty states | 2,400 | onboarding domain + API + UI | Wizard steps, spotlight tour, progress checklist, empty states | 00, 13 | 15 |
| 15 | `dev/v3-15-accessibility` | Keyboard navigation, focus, ARIA, motion, contrast | 2,400 | a11y utilities + UI | Focus rings, skip links, reduced motion, high-contrast mode | 00, 13 | 16 |
| 16 | `dev/v3-16-i18n-locales` | Locale framework, message catalogues, formatting | 2,400 | i18n domain + UI | Language switcher, RTL layout, number/date formatting, locale preview | 00, 13 | 17 |
| 17 | `dev/v3-17-data-visualization` | Chart models, radar/sankey/sparkline, aggregation | 2,400 | visualisation domain + UI | Responsive chart gallery, tooltips, legends, theme-aware palettes | 00, 04, 08 | 18 |
| 18 | `dev/v3-18-integrations-webhooks` | Webhook endpoints, delivery log, retry, adapters | 2,400 | integration domain + API + UI | Integration cards, secret handling UX, delivery inspector | 00, 10 | 19 |
| 19 | `dev/v3-19-offline-sync` | Offline queue, mutations, reconciliation, conflicts | 2,400 | sync domain + API + UI | Connectivity banner, queue inspector, conflict resolution UI | 00, 07 | 20 |
| 20 | `dev/v3-20-admin-console` | Moderation, account control, audit viewer, health | 2,400 | admin domain + API + UI | Admin dashboard, moderation queue, audit table, health gauges | 00, 10 | 21 |

## Test strategy

* Backend: one pytest module per feature covering models, store, service,
  validation, router and error paths. Use the existing `client`, `database`
  and `seeded` fixtures. Keep the strict mypy configuration intact.
* Frontend: colocated Vitest tests for pure logic, API adapters and at least
  one rendered interaction per feature. Use React Testing Library and the
  existing setup file.
* Program: `python3 scripts/loc_gate.py <baseline> --all --min 2000 --program-min 40000`.

## Merge order

Branches are pushed independently for review. The intended integration order
follows the "Merge order" column above. Because every feature is additive and
no shared file is edited after the foundation, merges are conflict free by
construction. Any follow-up fixes land on the same `dev/*` branch; `main` is
never updated from this program directly.
