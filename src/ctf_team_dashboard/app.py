"""Application factory for the CTF Team Dashboard."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from ctf_team_dashboard import __version__
from ctf_team_dashboard.config import Settings, get_settings
from ctf_team_dashboard.db.engine import init_database
from ctf_team_dashboard.dependencies import enforce_rate_limit, get_rate_limiter
from ctf_team_dashboard.errors import DashboardError
from ctf_team_dashboard.routers import (
    analytics,
    audit,
    auth,
    challenge_details,
    challenges,
    dashboard,
    health,
    members,
    realtime,
    solves,
    stats,
    teams,
)
from ctf_team_dashboard.security.headers import apply_security_headers
from ctf_team_dashboard.seed import persist_seed_data

logger = logging.getLogger("ctf_team_dashboard")

DESCRIPTION = """
Live dashboard for CTF team progress.

The API exposes teams, members, challenges and solves together with the
aggregated statistics that power the dashboard front end.
"""


def _configure_logging(settings: Settings) -> None:
    """Configure the root logger from the resolved settings."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Prepare the database and seed demo data on startup."""
    settings: Settings = app.state.settings
    _configure_logging(settings)
    database = init_database(settings)
    logger.info("database ready at %s", database.path)
    if settings.seed_on_startup:
        counts = persist_seed_data()
        logger.info("seed data ready: %s", counts)
    yield
    database.close()


def _mount_spa(app: FastAPI, static_dir: Path) -> bool:
    """Serve the built single page application when it is available.

    The dashboard uses client side routing, so any unknown path that is not an
    API call must fall back to ``index.html``.

    Args:
        app: The application to configure.
        static_dir: The directory holding the built assets.

    Returns:
        ``True`` when the assets were mounted.
    """
    index = static_dir / "index.html"
    if not index.is_file():
        return False

    assets = static_dir / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        """Return the single page application for every unknown path."""
        candidate = (static_dir / full_path).resolve()
        try:
            candidate.relative_to(static_dir.resolve())
        except ValueError:
            candidate = index
        if not candidate.is_file():
            candidate = index
        return FileResponse(candidate)

    return True


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    resolved = settings or get_settings()
    app = FastAPI(
        title="CTF Team Dashboard",
        version=__version__,
        description=DESCRIPTION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.state.settings = resolved

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def _apply_request_guards(request: Request, call_next: Any) -> Response:
        """Apply the rate limiter and the security headers to every request."""
        if resolved.rate_limit_per_minute > 0 and request.url.path.startswith("/api/"):
            await enforce_rate_limit(request, get_rate_limiter(), resolved)
        response: Response = await call_next(request)
        apply_security_headers(response, enable_hsts=resolved.enable_hsts)
        response.headers.setdefault("X-Dashboard-Version", __version__)
        return response

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(teams.router)
    app.include_router(members.router)
    app.include_router(challenges.router)
    app.include_router(challenge_details.router)
    app.include_router(solves.router)
    app.include_router(stats.router)
    app.include_router(dashboard.router)
    app.include_router(realtime.router)
    app.include_router(analytics.router)
    app.include_router(audit.router)

    @app.exception_handler(DashboardError)
    async def _handle_dashboard_error(
        _request: Request, exc: DashboardError
    ) -> JSONResponse:
        """Render domain errors using the shared error envelope."""
        headers: dict[str, str] = {}
        retry_after = exc.details.get("retry_after")
        if retry_after is not None:
            headers["Retry-After"] = str(int(float(retry_after)))
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_payload(),
            headers=headers,
        )

    static_dir = Path(resolved.static_dir) if resolved.static_dir else None
    if static_dir is not None:
        app.state.spa_mounted = _mount_spa(app, static_dir)

    return app


app = create_app()
