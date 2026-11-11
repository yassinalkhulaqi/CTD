"""Application factory for the CTF Team Dashboard."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ctf_team_dashboard import __version__
from ctf_team_dashboard.config import Settings, get_settings
from ctf_team_dashboard.db.engine import init_database
from ctf_team_dashboard.errors import DashboardError
from ctf_team_dashboard.routers import challenges, health, members, solves, stats, teams
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

    app.include_router(health.router)
    app.include_router(teams.router)
    app.include_router(members.router)
    app.include_router(challenges.router)
    app.include_router(solves.router)
    app.include_router(stats.router)

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

    return app


app = create_app()
