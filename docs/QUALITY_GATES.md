# Quality gates

Every branch must pass these commands from the repository root before it is
pushed. The commands are the same ones used in CI and in the V3 branch checks.

## Backend

```bash
python3 -m ruff check .
python3 -m ruff format --check .
python3 -m mypy
python3 -m pytest -q
python3 -m pytest -q --cov=ctf_team_dashboard
```

The coverage floor is configured at 70% in `pyproject.toml`. Do not lower it.

Note: the suite uses the `asyncio` marker, so do **not** disable the asyncio
plugin with `-p no:asyncio`; that removes the marker registration and makes
collection fail on this repository.

## Frontend

```bash
cd frontend
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
```

`npm run lint` runs ESLint with `--max-warnings=0`. `npm run format:check`
runs Prettier over every `src` file. New CSS belongs in per-feature module
files so that no branch has to edit a shared stylesheet.

## LOC gate

```bash
python3 scripts/loc_gate.py 448fe50 HEAD 2000
python3 scripts/loc_gate.py 448fe50 --all --min 2000 --program-min 40000
python3 scripts/branch_report.py 448fe50 --all
```

The gate uses `git diff --numstat`, treats generated files and caches as
excluded, and fails when a branch contributes fewer than 2,000 net lines.

## Gate policy

A gate is never disabled, downgraded or skipped to make a branch pass. When a
gate cannot run because of the environment, record the exact command and the
exact failure in the branch notes and rerun it once the environment recovers.
