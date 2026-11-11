"""Database access layer for the CTF Team Dashboard."""

from ctf_team_dashboard.db.engine import (
    Database,
    get_database,
    init_database,
    set_database,
)

__all__ = ["Database", "get_database", "init_database", "set_database"]
