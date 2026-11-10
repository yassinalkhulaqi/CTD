from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.app import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Return a FastAPI test client for the dashboard app."""
    test_client = TestClient(create_app())
    try:
        yield test_client
    finally:
        test_client.close()
