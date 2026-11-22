"""Dynamic discovery and installation of optional V3 feature modules.

Every feature package under this namespace is self-contained. A package may
export two module level symbols:

``SCHEMA_SQL``
    A SQL script creating the tables owned by the feature.
``register(app)``
    A callable that mounts the feature's API router on the FastAPI app.

Discovery happens at runtime through :mod:`pkgutil`, so adding a new package
never requires editing a shared import list. Branch merges therefore stay
conflict free: every branch only adds files inside its own package.
"""

from __future__ import annotations

import importlib
import pkgutil
import sqlite3
from types import ModuleType
from typing import Any

from fastapi import FastAPI

_DISCOVERED: dict[str, ModuleType] | None = None


def available_feature_names() -> list[str]:
    """Return the sorted names of every discoverable feature package."""
    return sorted(info.name for info in pkgutil.iter_modules(__path__))


def load_feature(name: str) -> ModuleType:
    """Import one feature package by its short name."""
    return importlib.import_module(f"{__name__}.{name}")


def discover_features(*, refresh: bool = False) -> dict[str, ModuleType]:
    """Return all feature packages, importing them on first use.

    Args:
        refresh: Force a rescan, which is useful in tests that create packages
            dynamically.

    Returns:
        A mapping of short feature name to imported module.
    """
    global _DISCOVERED
    if _DISCOVERED is None or refresh:
        discovered: dict[str, ModuleType] = {}
        for name in available_feature_names():
            discovered[name] = load_feature(name)
        _DISCOVERED = discovered
    return _DISCOVERED


def feature_schema_statements() -> tuple[str, ...]:
    """Return the schema scripts exported by the feature packages."""
    statements: list[str] = []
    for module in discover_features().values():
        candidate: Any = getattr(module, "SCHEMA_SQL", None)
        if isinstance(candidate, str) and candidate.strip():
            statements.append(candidate.strip())
    return tuple(statements)


def apply_feature_schemas(connection: sqlite3.Connection) -> None:
    """Create every feature-owned table on the given connection."""
    for statement in feature_schema_statements():
        connection.executescript(statement)


def install_features(app: FastAPI) -> list[str]:
    """Mount the routers of every feature package on the application.

    Args:
        app: The FastAPI application to extend.

    Returns:
        The names of the features that exposed a ``register`` callable.
    """
    installed: list[str] = []
    for name, module in discover_features().items():
        register: Any = getattr(module, "register", None)
        if callable(register):
            register(app)
            installed.append(name)
    return installed


def __getattr__(name: str) -> ModuleType:
    """Resolve a feature package as an attribute of this module."""
    if name in available_feature_names():
        return load_feature(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
