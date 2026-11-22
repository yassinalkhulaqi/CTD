"""SQLite persistence for chart specifications and ingested observations."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from ctf_team_dashboard.db.engine import Database, get_database
from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.features.data_visualization.models import (
    ChartSpec,
    ChartType,
    DataPoint,
)
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    format_datetime,
    parse_datetime,
    row_to_dict,
)

_CHART_COLUMNS = (
    "id, team_id, title, chart_type, series_json, options_json, palette, created_at, updated_at"
)
_DATA_COLUMNS = "chart_id, label, value, category, position"


def _timestamp(data: dict[str, Any], key: str) -> datetime:
    """Parse a stored ISO timestamp, falling back to the current time."""
    parsed = parse_datetime(str(data[key]))
    return parsed if parsed is not None else utcnow()


class ChartSpecRepository(BaseRepository):
    """Persistence for chart definitions."""

    table = "v3_charts"

    @staticmethod
    def to_model(row: sqlite3.Row) -> ChartSpec:
        """Map a database row onto a chart specification."""
        data = row_to_dict(row)
        return ChartSpec(
            id=str(data["id"]),
            team_id=str(data["team_id"]),
            title=str(data["title"]),
            chart_type=ChartType.parse(str(data["chart_type"])),
            series_json=str(data["series_json"]),
            options_json=str(data["options_json"]),
            palette=str(data["palette"]),
            created_at=_timestamp(data, "created_at"),
            updated_at=_timestamp(data, "updated_at"),
        )

    def get(self, chart_id: str) -> ChartSpec | None:
        """Return a chart by identifier, or ``None`` when missing."""
        row = self.fetch_one(
            f"SELECT {_CHART_COLUMNS} FROM {self.table} WHERE id = ?",
            (chart_id,),
        )
        return self.to_model(row) if row is not None else None

    def list_all(
        self,
        *,
        team_id: str | None = None,
        chart_type: ChartType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChartSpec]:
        """Return charts matching optional filters in display order."""
        clauses: list[str] = []
        params: list[Any] = []
        if team_id:
            clauses.append("team_id = ?")
            params.append(team_id)
        if chart_type is not None:
            clauses.append("chart_type = ?")
            params.append(chart_type.value)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.fetch_all(
            f"SELECT {_CHART_COLUMNS} FROM {self.table}{where} "
            "ORDER BY updated_at DESC, id ASC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )
        return [self.to_model(row) for row in rows]

    def insert(self, chart: ChartSpec) -> ChartSpec:
        """Insert a chart specification."""
        self.execute(
            f"""
            INSERT INTO {self.table}
                (id, team_id, title, chart_type, series_json, options_json,
                 palette, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chart.id,
                chart.team_id,
                chart.title,
                chart.chart_type.value,
                chart.series_json,
                chart.options_json,
                chart.palette,
                format_datetime(chart.created_at),
                format_datetime(chart.updated_at),
            ),
        )
        return chart

    def update(self, chart: ChartSpec) -> ChartSpec:
        """Replace the mutable fields of an existing chart."""
        self.execute(
            f"""
            UPDATE {self.table}
            SET title = ?, chart_type = ?, series_json = ?, options_json = ?,
                palette = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                chart.title,
                chart.chart_type.value,
                chart.series_json,
                chart.options_json,
                chart.palette,
                format_datetime(chart.updated_at),
                chart.id,
            ),
        )
        return chart

    def has_id(self, chart_id: str) -> bool:
        """Return whether a chart identifier is already in use."""
        return self.exists("id = ?", (chart_id,))


class ChartDataRepository(BaseRepository):
    """Persistence for observations ingested into a chart."""

    table = "v3_chart_data"

    @staticmethod
    def to_model(row: sqlite3.Row) -> DataPoint:
        """Map a database row onto a data point."""
        data = row_to_dict(row)
        return DataPoint(
            label=str(data["label"]),
            value=float(data["value"]),
            category=str(data["category"]),
        )

    def list_for_chart(self, chart_id: str) -> tuple[DataPoint, ...]:
        """Return all ingested points in their original order."""
        rows = self.fetch_all(
            f"SELECT {_DATA_COLUMNS} FROM {self.table} "
            "WHERE chart_id = ? ORDER BY position ASC, id ASC",
            (chart_id,),
        )
        return tuple(self.to_model(row) for row in rows)

    def count_for_chart(self, chart_id: str) -> int:
        """Return the number of ingested points for a chart."""
        return self.count("chart_id = ?", (chart_id,))

    def replace_points(self, chart_id: str, points: Sequence[DataPoint]) -> int:
        """Atomically replace all ingested points for a chart."""
        database = self.database
        with database.transaction() as connection:
            connection.execute(f"DELETE FROM {self.table} WHERE chart_id = ?", (chart_id,))
            connection.executemany(
                f"INSERT INTO {self.table} ({_DATA_COLUMNS}) VALUES (?, ?, ?, ?, ?)",
                [
                    (chart_id, point.label, point.value, point.category, position)
                    for position, point in enumerate(points)
                ],
            )
        return len(points)

    def append_points(self, chart_id: str, points: Sequence[DataPoint]) -> int:
        """Append ingested points after the current rows."""
        if not points:
            return 0
        start = self.count_for_chart(chart_id)
        self.execute_many(
            f"INSERT INTO {self.table} ({_DATA_COLUMNS}) VALUES (?, ?, ?, ?, ?)",
            [
                (chart_id, point.label, point.value, point.category, start + position)
                for position, point in enumerate(points)
            ],
        )
        return len(points)


class VisualizationStore:
    """Combined gateway used by the visualisation service."""

    def __init__(self, database: Database | None = None) -> None:
        resolved = database or get_database()
        self.charts = ChartSpecRepository(resolved)
        self.data = ChartDataRepository(resolved)

    @property
    def database(self) -> Database:
        """Return the database gateway shared by both repositories."""
        return self.charts.database
