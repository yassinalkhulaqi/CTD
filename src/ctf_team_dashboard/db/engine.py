"""SQLite engine, connection management and schema migration."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from ctf_team_dashboard.config import Settings, get_settings

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")

_PRAGMAS: tuple[tuple[str, str], ...] = (
    ("journal_mode", "WAL"),
    ("foreign_keys", "ON"),
    ("synchronous", "NORMAL"),
    ("temp_store", "MEMORY"),
    ("busy_timeout", "5000"),
)


def _apply_pragmas(connection: sqlite3.Connection) -> None:
    """Apply the connection level pragmas used by the dashboard."""
    for pragma, value in _PRAGMAS:
        connection.execute(f"PRAGMA {pragma}={value}")


class Database:
    """Thread-safe SQLite gateway used by the repository layer.

    The dashboard runs single-node by design; SQLite in WAL mode provides
    concurrent readers with a single writer while keeping the deployment
    footprint at zero additional services.
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self._connection: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------
    def connect(self) -> sqlite3.Connection:
        """Return the shared connection, opening it on first use."""
        with self._lock:
            if self._connection is None:
                self._ensure_directory()
                connection = sqlite3.connect(
                    self.path,
                    check_same_thread=False,
                    isolation_level=None,
                )
                connection.row_factory = sqlite3.Row
                _apply_pragmas(connection)
                self._connection = connection
            return self._connection

    def _ensure_directory(self) -> None:
        """Create the parent directory of the database file when required."""
        parent = self.path.parent
        if str(parent) not in {"", "."} and not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        """Close the shared connection if one is open."""
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run a block inside an immediate transaction."""
        connection = self.connect()
        with self._lock:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except Exception:
                connection.execute("ROLLBACK")
                raise
            else:
                connection.execute("COMMIT")

    @contextmanager
    def cursor(self) -> Iterator[sqlite3.Cursor]:
        """Yield a cursor over the shared connection."""
        connection = self.connect()
        with self._lock:
            yield connection.cursor()

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------
    def migrate(self) -> None:
        """Create the schema when it does not exist yet."""
        script = _SCHEMA_PATH.read_text(encoding="utf-8")
        connection = self.connect()
        with self._lock:
            connection.executescript(script)
            from ctf_team_dashboard.features import apply_feature_schemas

            apply_feature_schemas(connection)

    def reset(self) -> None:
        """Drop every table and recreate the schema."""
        connection = self.connect()
        with self._lock:
            connection.executescript(
                """
                PRAGMA writable_schema = OFF;
                DROP TABLE IF EXISTS events;
                DROP TABLE IF EXISTS solves;
                DROP TABLE IF EXISTS challenges;
                DROP TABLE IF EXISTS members;
                DROP TABLE IF EXISTS teams;
                """
            )
        self.migrate()

    def table_names(self) -> set[str]:
        """Return the set of user tables currently present."""
        with self.cursor() as cursor:
            rows = cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        return {str(row["name"]) for row in rows}


_database: Database | None = None
_database_lock = threading.Lock()


def get_database() -> Database:
    """Return the process-wide database gateway."""
    global _database
    with _database_lock:
        if _database is None:
            _database = Database(get_settings().database_path)
        return _database


def set_database(database: Database | None) -> None:
    """Replace the process-wide database gateway (used by tests)."""
    global _database
    with _database_lock:
        if _database is not None and database is not _database:
            _database.close()
        _database = database


def init_database(settings: Settings | None = None) -> Database:
    """Initialise the database and ensure the schema exists."""
    global _database
    resolved = settings or get_settings()
    with _database_lock:
        database = _database
        if database is None or database.path != resolved.database_path:
            if database is not None:
                database.close()
            database = Database(resolved.database_path)
            _database = database
        database.migrate()
        return database
