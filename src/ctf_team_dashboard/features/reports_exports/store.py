"""SQLite persistence for report templates, reports and export jobs.

Tables are created by ``SCHEMA_SQL`` in the package ``__init__`` and migrated
automatically by the platform kernel. Repositories only issue parameterised SQL
and translate rows into the immutable domain models.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from typing import Any

from ctf_team_dashboard.db.engine import Database
from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    format_datetime,
    parse_datetime,
    row_to_dict,
)

from .models import (
    ExportJob,
    ExportStatus,
    Report,
    ReportFormat,
    ReportStatus,
    ReportTemplate,
    TemplateScope,
)


class ReportTemplateRepository(BaseRepository):
    """Persistence operations for :class:`ReportTemplate` records."""

    table = "v3_report_templates"

    def __init__(self, database: Database | None = None) -> None:
        """Bind the repository to a database gateway."""
        super().__init__(database)
        self.table = "v3_report_templates"

    @staticmethod
    def to_model(row: sqlite3.Row) -> ReportTemplate:
        """Map a database row onto the domain model."""
        data = row_to_dict(row)
        updated = parse_datetime(str(data["updated_at"]))
        return ReportTemplate(
            id=str(data["id"]),
            name=str(data["name"]),
            sections_json=str(data["sections_json"]),
            format=ReportFormat.parse(str(data["format"]), ReportFormat.MARKDOWN),
            scope=TemplateScope.parse(str(data["scope"]), TemplateScope.TEAM),
            updated_at=updated if updated is not None else utcnow(),
        )

    def list_all(self, limit: int = 100) -> list[ReportTemplate]:
        """Return templates ordered by most recently updated."""
        rows = self.fetch_all(
            f"SELECT * FROM {self.table} ORDER BY updated_at DESC, id ASC LIMIT ?",
            (limit,),
        )
        return [self.to_model(row) for row in rows]

    def get(self, template_id: str) -> ReportTemplate | None:
        """Return a template by identifier."""
        row = self.fetch_one(f"SELECT * FROM {self.table} WHERE id = ?", (template_id,))
        return self.to_model(row) if row is not None else None

    def create(self, template: ReportTemplate) -> ReportTemplate:
        """Insert a template and return the stored model."""
        self.execute(
            f"""
            INSERT INTO {self.table} (id, name, sections_json, format, scope, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                template.id,
                template.name,
                template.sections_json,
                template.format.value,
                template.scope.value,
                format_datetime(template.updated_at),
            ),
        )
        return template

    def update(self, template: ReportTemplate) -> ReportTemplate:
        """Replace the mutable fields of a stored template."""
        self.execute(
            f"""
            UPDATE {self.table}
               SET name = ?, sections_json = ?, format = ?, scope = ?, updated_at = ?
             WHERE id = ?
            """,
            (
                template.name,
                template.sections_json,
                template.format.value,
                template.scope.value,
                format_datetime(template.updated_at),
                template.id,
            ),
        )
        return template

    def delete(self, template_id: str) -> bool:
        """Delete a template and report whether a row was removed."""
        return self.execute(f"DELETE FROM {self.table} WHERE id = ?", (template_id,)) > 0

    def count(self, where: str = "", params: Sequence[Any] = ()) -> int:
        """Return the number of templates matching an optional clause."""
        return super().count(where, params)


class ReportRepository(BaseRepository):
    """Persistence operations for :class:`Report` records."""

    table = "v3_reports"

    def __init__(self, database: Database | None = None) -> None:
        """Bind the repository to a database gateway."""
        super().__init__(database)
        self.table = "v3_reports"

    @staticmethod
    def to_model(row: sqlite3.Row) -> Report:
        """Map a database row onto the domain model."""
        data = row_to_dict(row)
        created = parse_datetime(str(data["created_at"]))
        return Report(
            id=str(data["id"]),
            template_id=str(data["template_id"]),
            title=str(data["title"]),
            scope_id=str(data["scope_id"]),
            status=ReportStatus.parse(str(data["status"]), ReportStatus.DRAFT),
            created_at=created if created is not None else utcnow(),
            data_json=str(data.get("data_json") or "{}"),
        )

    def list_all(
        self,
        *,
        status: ReportStatus | None = None,
        template_id: str | None = None,
        limit: int = 100,
    ) -> list[Report]:
        """Return reports with optional status and template filters."""
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        if template_id is not None:
            clauses.append("template_id = ?")
            params.append(template_id)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.fetch_all(
            f"SELECT * FROM {self.table}{where} ORDER BY created_at DESC, id ASC LIMIT ?",
            [*params, limit],
        )
        return [self.to_model(row) for row in rows]

    def get(self, report_id: str) -> Report | None:
        """Return a report by identifier."""
        row = self.fetch_one(f"SELECT * FROM {self.table} WHERE id = ?", (report_id,))
        return self.to_model(row) if row is not None else None

    def create(self, report: Report) -> Report:
        """Insert a report and return the stored model."""
        self.execute(
            f"""
            INSERT INTO {self.table}
                (id, template_id, title, scope_id, status, created_at, data_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report.id,
                report.template_id,
                report.title,
                report.scope_id,
                report.status.value,
                format_datetime(report.created_at),
                report.data_json,
            ),
        )
        return report

    def set_status(self, report_id: str, status: ReportStatus) -> bool:
        """Update the lifecycle status of a report."""
        return (
            self.execute(
                f"UPDATE {self.table} SET status = ? WHERE id = ?",
                (status.value, report_id),
            )
            > 0
        )

    def set_snapshot(self, report_id: str, data_json: str) -> bool:
        """Replace the captured data snapshot of a report."""
        return (
            self.execute(
                f"UPDATE {self.table} SET data_json = ? WHERE id = ?",
                (data_json, report_id),
            )
            > 0
        )

    def delete(self, report_id: str) -> bool:
        """Delete a report and report whether a row was removed."""
        return self.execute(f"DELETE FROM {self.table} WHERE id = ?", (report_id,)) > 0

    def count_status(self, status: ReportStatus) -> int:
        """Return the number of reports in a given lifecycle state."""
        return self.count("status = ?", (status.value,))

    def count(self, where: str = "", params: Sequence[Any] = ()) -> int:
        """Return the number of reports matching an optional clause."""
        return super().count(where, params)


class ExportRepository(BaseRepository):
    """Persistence operations for :class:`ExportJob` records."""

    table = "v3_exports"

    def __init__(self, database: Database | None = None) -> None:
        """Bind the repository to a database gateway."""
        super().__init__(database)
        self.table = "v3_exports"

    @staticmethod
    def to_model(row: sqlite3.Row) -> ExportJob:
        """Map a database row onto the domain model."""
        data = row_to_dict(row)
        created = parse_datetime(str(data["created_at"]))
        return ExportJob(
            id=str(data["id"]),
            report_id=str(data["report_id"]),
            format=ReportFormat.parse(str(data["format"]), ReportFormat.MARKDOWN),
            status=ExportStatus.parse(str(data["status"]), ExportStatus.FAILED),
            content=str(data["content"]),
            created_at=created if created is not None else utcnow(),
        )

    def list_all(self, limit: int = 100) -> list[ExportJob]:
        """Return the most recent export jobs first."""
        rows = self.fetch_all(
            f"SELECT * FROM {self.table} ORDER BY created_at DESC, id ASC LIMIT ?",
            (limit,),
        )
        return [self.to_model(row) for row in rows]

    def list_for_report(self, report_id: str) -> list[ExportJob]:
        """Return every export produced for one report."""
        rows = self.fetch_all(
            f"SELECT * FROM {self.table} WHERE report_id = ? ORDER BY created_at DESC",
            (report_id,),
        )
        return [self.to_model(row) for row in rows]

    def get(self, export_id: str) -> ExportJob | None:
        """Return an export job by identifier."""
        row = self.fetch_one(f"SELECT * FROM {self.table} WHERE id = ?", (export_id,))
        return self.to_model(row) if row is not None else None

    def create(self, job: ExportJob) -> ExportJob:
        """Insert an export job and return the stored model."""
        self.execute(
            f"""
            INSERT INTO {self.table} (id, report_id, format, status, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                job.id,
                job.report_id,
                job.format.value,
                job.status.value,
                job.content,
                format_datetime(job.created_at),
            ),
        )
        return job

    def count_by_format(self) -> dict[str, int]:
        """Return export counts keyed by serialisation format."""
        rows = self.fetch_all(
            f"SELECT format, COUNT(*) AS total FROM {self.table} GROUP BY format ORDER BY format"
        )
        return {str(row["format"]): int(row["total"]) for row in rows}

    def delete(self, export_id: str) -> bool:
        """Delete an export job and report whether a row was removed."""
        return self.execute(f"DELETE FROM {self.table} WHERE id = ?", (export_id,)) > 0

    def count(self, where: str = "", params: Sequence[Any] = ()) -> int:
        """Return the number of exports matching an optional clause."""
        return super().count(where, params)
