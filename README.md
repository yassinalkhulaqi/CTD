# CTF Team Dashboard

Live dashboard for CTF team progress: solved/unsolved tracking, category
statistics, realtime activity and time remaining.

## Stack

- FastAPI backend (`src/`) — SQLite, JWT auth, RBAC, WebSocket gateway
- React + TypeScript frontend (`frontend/`) — Vite, Zustand, SVG charts

## Getting started

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
python -m pip install -e ".[dev]"
python -m pytest
python -m ctf_team_dashboard
```

The frontend runs on its own dev server:

```bash
cd frontend
npm install
npm run dev
```

## Architecture

| Layer | Location | Responsibility |
| --- | --- | --- |
| Domain | `src/ctf_team_dashboard/domain` | Entities, enumerations and value objects |
| Persistence | `src/ctf_team_dashboard/repositories` | SQLite access behind typed repositories |
| Services | `src/ctf_team_dashboard/services` | Business rules, statistics, caching |
| API | `src/ctf_team_dashboard/routers` | FastAPI routers and request schemas |
| Security | `src/ctf_team_dashboard/security` | Tokens, passwords, rate limiting, audit |
| Realtime | `src/ctf_team_dashboard/realtime` | Event bus, publisher and WebSocket gateway |

The frontend mirrors that split:

| Layer | Location | Responsibility |
| --- | --- | --- |
| API | `frontend/src/api` | HTTP client, query cache, typed endpoints |
| State | `frontend/src/stores` | Zustand stores for the dashboard state |
| Design system | `frontend/src/components/ui` | Accessible primitives and charts |
| Features | `frontend/src/features` | Authentication and challenge tracking |
| Pages | `frontend/src/app` | Routed screens and the application shell |

## API surface

| Group | Endpoints |
| --- | --- |
| Health | `GET /api/health`, `GET /api/health/ready` |
| Auth | `POST /api/auth/login`, `/refresh`, `/logout`, `/register`, `GET /api/auth/me` |
| Teams | `GET/POST /api/teams`, `GET /api/teams/scoreboard` |
| Members | `GET/POST /api/members`, `GET /api/members/contributions` |
| Challenges | `GET/POST /api/challenges`, `GET /api/challenges/board`, notes, timeline, flags |
| Solves | `GET/POST /api/solves`, `GET /api/solves/velocity` |
| Stats | `GET /api/stats/overview`, `/categories`, `/leaderboard`, `/timeline`, `/heatmap` |
| Dashboard | `GET /api/dashboard`, `GET /api/dashboard/categories` |
| Analytics | `GET /api/analytics/velocity`, `/intervals`, `/difficulty`, `/heatmap` |
| Realtime | `WS /ws`, `GET /api/realtime/status`, `/realtime/replay` |
| Audit | `GET /api/audit/entries`, `/actions`, `/summary` |

Every error is rendered with the same envelope:

```json
{ "error": { "code": "not_found", "message": "Team 'x' does not exist" } }
```

## Configuration

Every setting is read from the environment with the `CTFD_` prefix.

| Variable | Default | Description |
| --- | --- | --- |
| `CTFD_DATABASE_PATH` | `ctf_team_dashboard.sqlite` | SQLite database location |
| `CTFD_AUTH_ENABLED` | `false` | Require authentication on the API |
| `CTFD_AUTH_SECRET` | `change-me-in-production` | Signing secret of the tokens |
| `CTFD_ACCESS_TOKEN_TTL_SECONDS` | `3600` | Lifetime of an access token |
| `CTFD_REFRESH_TOKEN_TTL_SECONDS` | `1209600` | Lifetime of a refresh token |
| `CTFD_RATE_LIMIT_PER_MINUTE` | `240` | Request budget per minute and caller |
| `CTFD_CORS_ORIGINS` | `http://localhost:5173` | Comma separated allowed origins |
| `CTFD_SEED_ON_STARTUP` | `true` | Seed the demo dataset on startup |
| `CTFD_STATIC_DIR` | *(unset)* | Serve a built frontend from this directory |
| `CTFD_ENABLE_HSTS` | `false` | Send the strict transport security header |
| `CTFD_LOG_LEVEL` | `INFO` | Log level of the server |

## Quality gates

```bash
# Backend
python -m ruff check .
python -m mypy
python -m pytest --cov=ctf_team_dashboard

# Frontend
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
```

The backend enforces a coverage floor of 70% and currently sits at 83%.

## Roles

| Role | Capabilities |
| --- | --- |
| `viewer` | Read the dashboard, the teams, the challenges and the solves |
| `analyst` | Record solves |
| `lead` | Create and update the challenges, manage the members |
| `admin` | Delete the challenges, manage the teams and the API keys, read the audit trail |
