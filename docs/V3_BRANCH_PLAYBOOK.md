# V3 branch playbook

This document is the contract for every `dev/v3-*` feature branch. Read it
before writing code. Following it exactly means your branch cannot conflict
with any other V3 branch, because each branch only adds files inside its own
two feature directories plus its own tests and documentation.

## What you must not edit

After the foundation, **do not edit** any of these files:

* `src/ctf_team_dashboard/app.py`
* `src/ctf_team_dashboard/db/engine.py`
* `src/ctf_team_dashboard/features/__init__.py`
* `frontend/src/app/routes.tsx`
* `frontend/src/app/AppShell.tsx`
* `frontend/src/features/plugins.ts`
* `frontend/src/index.css`
* `pyproject.toml`, `package.json`, `tsconfig.json`, `vitest.config.ts`
* `tests/conftest.py`

Everything else under your own feature paths is yours.

## Backend contract

Create `src/ctf_team_dashboard/features/<slug>/` with these files:

* `__init__.py` — exports `SCHEMA_SQL: str` and `register(app: FastAPI) -> None`.
* `models.py` — frozen slotted dataclasses, enums where useful, derived
  properties and pure calculation helpers. This is where domain depth lives.
* `store.py` — persistence via `BaseRepository` from
  `ctf_team_dashboard.repositories.base` (import only, never edit it). Use
  parameterised SQL and `CREATE TABLE IF NOT EXISTS` in `SCHEMA_SQL`.
* `service.py` — business rules, validation, orchestration and aggregation.
  Raise `ValidationError`, `NotFoundError` or `ConflictError` from
  `ctf_team_dashboard.errors` instead of ad hoc exceptions.
* `router.py` — an `APIRouter(prefix="/api/<slug>", tags=["<slug>"])` with
  typed request/response models (Pydantic `BaseModel` classes may live in
  `schemas.py` inside the package). `register(app)` mounts it.
* `py.typed` — empty marker file.

The package `__init__.py` must look like this (adapt names):

```python
"""<Feature> module for the CTF Team Dashboard."""

from __future__ import annotations

from fastapi import FastAPI

from ctf_team_dashboard.features.<slug>.router import router

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS <slug>_items (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def register(app: FastAPI) -> None:
    """Mount the <feature> API router."""
    app.include_router(router)
```

The registry imports your package and calls `register` automatically. Your
schema script is executed by `Database.migrate()` automatically. The pytest
`client` and `database` fixtures therefore see your tables with no changes.

### Backend style rules

* Python 3.10 compatible syntax, `from __future__ import annotations` in each
  module, full annotations on every function (mypy runs with `strict = true`).
* Ruff selects `E,F,W,I,N,UP,B,A,C4,DTZ,T10,T20,SIM,PT,RUF` with line length
  100 and double quotes. No `print()` in `src` (T201). Sort imports
  automatically with `python3 -m ruff check --fix .` and format with
  `python3 -m ruff format .`.
* Use timezone-aware UTC timestamps via `utcnow()` from
  `ctf_team_dashboard.domain.models`. Store them as ISO strings.
* Prefer pure, testable functions and small classes with one responsibility.
* Do not weaken or skip existing tests. Add your own.

## Frontend contract

Create `frontend/src/features/<slug>/` with these files:

* `plugin.ts` — exports `const plugin: FeaturePlugin` with a unique `id`
  (slug), a `label`, a unique `path` starting with `/`, a `description`, a
  `group`, and the root `component`.
* `types.ts` — domain types and view models.
* `api.ts` — typed fetch functions built on `get`, `post`, `patch`, `del`
  from `../../api/client`.
* `hooks.ts` (optional) — data loading and local state hooks.
* `<Feature>Page.tsx` — the routed page, composed from your components.
* `components/` — at least three focused presentational components.
* `<Feature>Page.module.css` and component CSS modules — all styling local.
* At least three `*.test.ts(x)` files covering pure logic, the API adapter and
  a rendered interaction.

Example `plugin.ts`:

```ts
import type { FeaturePlugin } from "../plugins";
import { NotesPage } from "./NotesPage";

export const plugin: FeaturePlugin = {
  id: "notes",
  label: "Notes",
  path: "/notes",
  description: "Challenge notes and templates",
  group: "Workspace",
  component: NotesPage,
};
```

The foundation discovers this file with `import.meta.glob`, mounts the route
and adds a module link to the top launcher automatically.

### Frontend style rules

* TypeScript strict mode with `noUnusedLocals` and `noUnusedParameters`.
* ESLint with zero warnings allowed; Prettier formatting required.
* Use the existing design system primitives from `../../components/ui` where
  they fit (Button, Card, Badge, Tabs, Field, Feedback, Table, Overlay...).
* Use CSS custom properties defined in `frontend/src/index.css`; do not edit
  that file. Add responsive rules, hover/focus states and reduced-motion
  handling in your own module files.
* Real user experience: loading, empty, error and success states; keyboard
  operable controls; accessible labels; optimistic updates where sensible.
* No `any`, no `@ts-ignore`, no disabled lint rules.

## Tests and documentation

* `tests/test_v3_<slug>.py` — cover models, store, service, router success and
  error paths. Use fixtures `client`, `database`, `seeded`, `settings`.
* `docs/features/v3-<slug>.md` — feature overview, domain rules, API table,
  UI walkthrough, test notes and accessibility notes. Aim for genuine
  documentation, not placeholder text.

## Size and quality bar

Your branch must add **at least 2,000 net lines** against the baseline. Reach
that number through real depth: several domain models with behaviour, a
complete store and service layer, a full CRUD API, a polished multi-component
screen with local CSS, thorough unit and integration tests, and documentation.
Do not duplicate code, pad with comments, generate filler or weaken tests.
Aim for roughly 2,300–2,800 net lines so the branch has margin.

## Verification before commit

From the worktree root:

```bash
python3 -m ruff check . && python3 -m ruff format --check .
python3 -m mypy
python3 -m pytest -q
(cd frontend && npm run lint && npm run format:check && npm run typecheck && npm test && npm run build)
python3 scripts/loc_gate.py 448fe50 HEAD --min 2000
```

If `format:check` complains about pre-existing files, run `npm run format`
inside your worktree and stage the normalised files; the foundation already
did this, so it should be clean.

Commit only your own files. Do not stage `node_modules`, `dist`, caches or
`.coverage`. Do not push; the coordinator pushes all branches at the end.
