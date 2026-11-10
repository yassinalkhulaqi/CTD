"""Application configuration for the CTF Team Dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the CTF Team Dashboard."""

    database_path: Path = Path("ctf_team_dashboard.sqlite")
