# V3 feature: Onboarding tour

The onboarding tour turns a fresh CTF workspace into a guided experience. It
combines an ordered setup wizard, a spotlight tour, a setup checklist and
illustrated empty states. Progress is stored per user and can be resumed,
skipped or reset without affecting challenges, solves or notes.

| Item | Value |
| --- | --- |
| Backend package | `src/ctf_team_dashboard/features/onboarding_tour/` |
| Frontend directory | `frontend/src/features/onboarding-tour/` |
| API prefix | `/api/onboarding` |
| Route | `/onboarding` |
| Plugin id / label / group | `onboarding` / `Onboarding` / `Settings` |
| Tables | `v3_onboarding_steps`, `v3_onboarding_progress`, `v3_checklists` |
| Baseline | `448fe50` |

## Feature overview

A user arriving at the dashboard sees a progress banner with a completion
ring, a contextual welcome note, the wizard stepper and a checklist. Choosing
a step (or pressing **Resume tour**) opens a modal spotlight that walks through
the surfaces of the application. Each step can be marked complete or skipped;
completion advances the next-step derivation and ticks the linked checklist
item. Skipping unlocks later steps but deliberately earns no credit, so the
completion percentage always reflects real progress.

The backend ships a validated seven-step catalogue on first use:

1. `welcome` — read the welcome note (`#onboarding-welcome`)
2. `profile` — set a display name (`/settings`, optional)
3. `workspace` — explore the challenge board (`[data-tour="challenge-board"]`)
4. `first-flag` — submit a flag (`tour:submit-flag`)
5. `scoreboard` — read the scoreboard (`/analytics`, optional)
6. `team` — meet the roster (`#team-roster`)
7. `review` — review and finish (`/onboarding`, optional)

The default checklist contains six items. Three of them are linked to step
`completion_key` values (`tour.welcome`, `tour.workspace`, `tour.first_flag`)
and are ticked automatically when the corresponding step is completed.

## Domain rules

### `OnboardingStep`

A frozen, slotted dataclass with `id`, `slug`, `title`, `description`,
`target`, `order`, `completion_key`, `kind`, `estimated_seconds`, `required`,
`hint`, `icon` and `created_at`. Derived helpers provide the ordinal label,
the target kind, the duration label and flexible reference matching by id,
slug or completion key. The module-level `validate_target` accepts only four
safe target grammars — `#anchor`, `/route`, `[data-tour="name"]` and
`tour:token` — which prevents arbitrary selectors reaching the DOM.

### `OnboardingProgress`

A per-user, per-step record with a UTC `completed_at` timestamp and a `skipped`
flag. `is_complete`, `state`, `status_label` and `elapsed_seconds` are pure
derivations. Records are upserted on the `(user_id, step_id)` key, so replaying
an action never creates duplicates.

### `SetupChecklist` and `ChecklistItem`

The checklist stores its items as a compact JSON document in `items_json`.
`parse_checklist_items` is defensive: malformed JSON, non-list payloads and
entries without an id or label degrade to an empty checklist rather than
breaking the page. `mark` returns a new value, preserving immutability.

### `WelcomeNote` and `ResumeState`

A welcome note is generated from the current status: an informational greeting
before the tour starts, a tip while it is in progress and a success message
when finished. `ResumeState` carries `can_resume`, the next step slug, the
percentage, the last activity timestamp and a ready-to-render message.

### Aggregation helpers

* `completion_percent` clamps the ratio to 0–100 and reports zero for an empty
  catalogue. Skipped steps never contribute to the numerator.
* `derive_next_step` returns the first unresolved step in display order.
* `derive_step_states` returns `complete`, `skipped`, `active`, `available` or
  `locked`. A step is `active` when it is next, `available` when every earlier
  *required* step is resolved and `locked` otherwise. Optional steps never
  lock the journey.
* `validate_catalogue` rejects empty catalogues, blank slugs or keys, duplicate
  slugs, keys and orders, non-positive orders, blank titles and unsafe targets.

The service layer adds orchestration: catalogue seeding is idempotent,
completing a linked step ticks its checklist item, skipping is conflict-checked,
and `reset` deletes progress and recreates the default checklist.

## HTTP API

All endpoints accept a `user_id` query parameter (default `demo-user` in open
mode). Failures use the shared error envelope: `not_found` → 404, `conflict` →
409 and `validation_error` → 422.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/onboarding/steps` | Ordered catalogue with per-user derived states |
| `GET` | `/api/onboarding/progress` | Full progress summary with checklist and note |
| `GET` | `/api/onboarding/next` | Next unresolved step, or `null` |
| `POST` | `/api/onboarding/steps/{id}/complete` | Complete a step and sync the checklist |
| `POST` | `/api/onboarding/steps/{id}/skip` | Skip a step without awarding credit |
| `GET` | `/api/onboarding/checklist` | Return the setup checklist |
| `PUT` | `/api/onboarding/checklist` | Replace the full checklist |
| `PUT` | `/api/onboarding/checklist/{item_id}` | Tick or untick one item |
| `POST` | `/api/onboarding/reset` | Clear progress and restore defaults |
| `POST` | `/api/onboarding/targets/check` | Validate a spotlight target |

The `{id}` segment accepts a step identifier, a slug or a completion key, which
makes deep links readable. `GET /progress` is the primary payload for the UI:
it contains the step list, records, counters, next step, checklist, resume state
and welcome note in a single typed response.

## Persistence schema

* `v3_onboarding_steps` — unique slug and completion key, explicit step order,
  kind, timing, required flag, hint and icon.
* `v3_onboarding_progress` — composite primary key on `(user_id, step_id)`,
  ISO `completed_at` string and an integer `skipped` flag.
* `v3_checklists` — primary key on `user_id`, JSON `items_json` and
  `updated_at`.

The schema is exported as `SCHEMA_SQL` from the package `__init__` and applied
by `Database.migrate()` through the dynamic feature registry. No shared file
was edited.

## UI walkthrough

1. **Landing.** `OnboardingPage` loads steps and progress through two cached
   queries. A skeleton appears on first load; an error state with **Try again**
   appears on failure; an illustrated empty state appears for an empty
   catalogue.
2. **Progress banner.** `ProgressBanner` shows a circular completion ring, the
   status badge, the welcome note and either **Resume tour** or **Start tour**.
   **Reset progress** is disabled until there is something to clear.
3. **Stepper.** `WizardStepper` draws a connected vertical list with a state
   icon, label and duration per step. Locked steps are disabled; the current
   step carries `aria-current="step"`.
4. **Step cards.** `StepCard` presents the description, target, hint and the
   **Show me**, **Skip** and **Mark complete** actions. Resolved cards dim and
   disable their actions.
5. **Spotlight.** `TourOverlay` opens as a modal with a ring over a schematic
   target area, the step copy, a hint and keyboard hints. Buttons move back,
   forward or dismiss; the last step is labelled **Finish**.
6. **Checklist.** `ChecklistPanel` renders a progress bar and native checkboxes
   with optimistic feedback; completing linked wizard steps ticks items too.
7. **Reset.** Resetting clears progress for the current user and restores the
   six default checklist items; notes and solves are never touched.

## Accessibility notes

* The tour uses `role="dialog"` with `aria-modal="true"` and
  `aria-labelledby`; focus moves to the close control when a step opens.
* Keyboard shortcuts: `ArrowRight`, `ArrowDown` and `Enter` advance;
  `ArrowLeft` and `ArrowUp` go back; `Escape` closes. Other keys are ignored.
* Stepper buttons expose a descriptive `aria-label` including position and
  state and use `aria-current="step"`.
* Checklist items are real checkbox inputs inside labels; progress bars expose
  `role="progressbar"` with numeric values and labels.
* Decorative SVG illustrations and spotlight rings are `aria-hidden`; status
  copy lives in text nodes with `role="status"` where appropriate.
* All styling uses theme custom properties, responsive breakpoints, hover and
  focus states, and a `prefers-reduced-motion` override in every CSS module.

## Testing notes

Backend (`tests/test_v3_onboarding_tour.py`) covers pure percentage, target
grammar, ordering, next-step derivation, prerequisites, catalogue validation,
checklist JSON handling, resume and note helpers; all three repositories; and
the service rules for seeding, completion, skipping, conflict resolution,
checklist validation, reset and user isolation. Router tests exercise every
endpoint plus 404, 409 and 422 paths. 51 tests pass.

Frontend tests are colocated in five files:

* `tour.test.ts` — ordering, state labels, keyboard map and checklist math.
* `api.test.ts` — URLs, verbs and JSON bodies of every typed endpoint.
* `components/ChecklistPanel.test.tsx` — stepper, cards, checklist, banner and
  empty-state rendering and interactions.
* `TourOverlay.test.tsx` — dialog semantics, focus and keyboard behaviour.
* `OnboardingPage.test.tsx` — mocked-hook page integration: resume, keyboard
  navigation, mutations, empty and error states.

34 frontend tests pass alongside the existing suite. Both backend and frontend
gates (lint, format, type check, tests and build) pass for this branch.
