"""Application entry point for the CTF Team Dashboard."""

from __future__ import annotations

import uvicorn

from ctf_team_dashboard.app import create_app


def main() -> None:
    """Start the dashboard API server."""
    uvicorn.run(create_app(), host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
