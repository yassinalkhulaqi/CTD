"""Application entry point for the CTF Team Dashboard."""

from __future__ import annotations

import uvicorn

from ctf_team_dashboard.app import create_app
from ctf_team_dashboard.config import get_settings


def main() -> None:
    """Start the dashboard API server."""
    settings = get_settings()
    uvicorn.run(
        create_app(settings),
        host="127.0.0.1",
        port=8000,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
