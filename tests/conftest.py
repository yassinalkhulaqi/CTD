"""Shared pytest fixtures for the CTF Team Dashboard test suite."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.app import create_app
from ctf_team_dashboard.config import Settings, reset_settings_cache
from ctf_team_dashboard.db.engine import Database, set_database
from ctf_team_dashboard.repositories import Repositories
from ctf_team_dashboard.seed import build_seed_data, persist_seed_data


@pytest.fixture(autouse=True)
async def reset_shared_state() -> AsyncIterator[None]:
    """Reset process-wide limiters and audit state before every test.

    The merged program runs twenty feature suites in one process. The rate
    limiter and audit log are intentionally process-wide in production, so
    without this fixture requests from earlier tests would exhaust the shared
    request budget and leak audit entries into later assertions.
    """
    from ctf_team_dashboard.dependencies import get_rate_limiter
    from ctf_team_dashboard.security.audit import get_audit_log

    await get_rate_limiter().reset()
    get_audit_log().clear()
    yield


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Return settings pointing at an isolated temporary database."""
    reset_settings_cache()
    return Settings(
        database_path=tmp_path / "test.sqlite",
        seed_on_startup=True,
        auth_secret="test-secret",
    )


@pytest.fixture
def database(settings: Settings) -> Iterator[Database]:
    """Provide a migrated, isolated database for the duration of a test."""
    gateway = Database(settings.database_path)
    set_database(gateway)
    gateway.migrate()
    try:
        yield gateway
    finally:
        gateway.close()
        set_database(None)


@pytest.fixture
def repositories(database: Database) -> Repositories:
    """Return repositories bound to the isolated test database."""
    return Repositories()


@pytest.fixture
def seeded(repositories: Repositories) -> Repositories:
    """Return repositories populated with the deterministic seed dataset."""
    persist_seed_data(repositories, force=True)
    return repositories


@pytest.fixture
def client(settings: Settings, database: Database) -> Iterator[TestClient]:
    """Return a FastAPI test client wired to the isolated database."""
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seed_entities() -> tuple[list[object], list[object], list[object], list[object]]:
    """Return the raw seed entities without persisting them."""
    return build_seed_data()
