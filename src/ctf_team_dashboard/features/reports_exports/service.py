"""Business rules and orchestration for the report studio.

The service validates user input, owns identifier generation, captures a data
snapshot for each report, enforces the draft-to-final workflow and coordinates
the template, report and export repositories.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import uuid4

from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.repositories import Repositories

from .models import (
    ExportJob,
    ExportStatus,
    RenderedReport,
    Report,
    ReportFormat,
    ReportSection,
    ReportStats,
    ReportStatus,
    ReportTemplate,
    SectionKind,
    TemplateScope,
    dump_data,
    parse_data,
    parse_sections,
    section_from_mapping,
)
from .renderers import render_export, render_report
from .store import ExportRepository, ReportRepository, ReportTemplateRepository

MAX_SECTIONS = 40
MAX_NAME_LENGTH = 96
MAX_TITLE_LENGTH = 140
MAX_BODY_LENGTH = 8_000


def normalise_sections(raw: Sequence[Any]) -> tuple[ReportSection, ...]:
    """Convert a mixed sequence of sections and mappings into domain sections."""
    if len(raw) > MAX_SECTIONS:
        raise ValidationError(f"A template may contain at most {MAX_SECTIONS} sections")
    sections: list[ReportSection] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        section = item if isinstance(item, ReportSection) else section_from_mapping(item, index)
        if section.id in seen:
            raise ValidationError(f"Duplicate section identifier: {section.id}")
        if len(section.title) > MAX_NAME_LENGTH:
            raise ValidationError(f"Section title must be at most {MAX_NAME_LENGTH} characters")
        if len(section.body) > MAX_BODY_LENGTH:
            raise ValidationError(f"Section body must be at most {MAX_BODY_LENGTH} characters")
        if section.kind not in set(SectionKind):
            raise ValidationError(f"Unsupported section kind: {section.kind}")
        seen.add(section.id)
        sections.append(section.updated(order=index))
    return tuple(sections)


class ReportService:
    """Coordinate template authoring, report lifecycle and export generation."""

    def __init__(
        self,
        templates: ReportTemplateRepository | None = None,
        reports: ReportRepository | None = None,
        exports: ExportRepository | None = None,
        repositories: Repositories | None = None,
    ) -> None:
        """Create a service, injecting repositories when the caller needs to."""
        self.templates = templates or ReportTemplateRepository()
        self.reports = reports or ReportRepository()
        self.exports = exports or ExportRepository()
        self._repositories = repositories

    @staticmethod
    def _identifier(prefix: str) -> str:
        """Generate a short, collision-resistant identifier."""
        return f"{prefix}_{uuid4().hex[:10]}"

    def list_templates(self) -> tuple[ReportTemplate, ...]:
        """Return every template, most recently updated first."""
        return tuple(self.templates.list_all())

    def get_template(self, template_id: str) -> ReportTemplate:
        """Return a template or raise :class:`NotFoundError`."""
        template = self.templates.get(template_id)
        if template is None:
            raise NotFoundError(f"Report template '{template_id}' does not exist")
        return template

    def create_template(
        self,
        name: str,
        sections: Sequence[Any],
        report_format: ReportFormat | str = ReportFormat.MARKDOWN,
        scope: TemplateScope | str = TemplateScope.TEAM,
    ) -> ReportTemplate:
        """Validate and persist a new report template."""
        cleaned = name.strip()
        if not cleaned:
            raise ValidationError("A template name is required")
        if len(cleaned) > MAX_NAME_LENGTH:
            raise ValidationError(f"Template name must be at most {MAX_NAME_LENGTH} characters")
        configured = normalise_sections(sections)
        if not configured:
            raise ValidationError("A template needs at least one section")
        template = ReportTemplate(
            id=self._identifier("tpl"),
            name=cleaned,
            sections_json="[]",
            format=ReportFormat.parse(report_format),
            scope=TemplateScope.parse(scope),
        )
        template = template.with_sections(configured)
        return self.templates.create(template)

    def list_reports(
        self,
        status: ReportStatus | None = None,
        limit: int = 100,
    ) -> tuple[Report, ...]:
        """Return reports with optional lifecycle filtering."""
        if limit < 1 or limit > 500:
            raise ValidationError("The report limit must be between 1 and 500")
        return tuple(self.reports.list_all(status=status, limit=limit))

    def get_report(self, report_id: str) -> Report:
        """Return a report or raise :class:`NotFoundError`."""
        report = self.reports.get(report_id)
        if report is None:
            raise NotFoundError(f"Report '{report_id}' does not exist")
        return report

    def collect_scope_data(self, scope_id: str) -> dict[str, Any]:
        """Build a default data snapshot from the dashboard's seeded domain data."""
        repositories = self._repositories or Repositories()
        team = repositories.teams.get(scope_id) or repositories.teams.get_by_slug(scope_id)
        team_id = team.id if team is not None else scope_id
        challenges = repositories.challenges.list_all(team_id)
        members = repositories.members.list_all(team_id)
        solves = repositories.solves.list_all(team_id=team_id)
        solved = [challenge for challenge in challenges if challenge.is_solved]
        return {
            "scope": scope_id,
            "team": team.name if team is not None else scope_id,
            "challenges": [
                {
                    "id": challenge.id,
                    "title": challenge.title,
                    "category": challenge.category.value,
                    "status": challenge.status.value,
                    "points": challenge.points,
                }
                for challenge in challenges
            ],
            "members": [
                {
                    "id": member.id,
                    "handle": member.handle,
                    "display_name": member.label,
                    "role": member.role.value,
                }
                for member in members
            ],
            "solves": [
                {
                    "member_id": solve.member_id,
                    "challenge_id": solve.challenge_id,
                    "points": solve.points_awarded,
                }
                for solve in solves
            ],
            "points": sum(solve.points_awarded for solve in solves),
            "solved": len(solved),
            "total": len(challenges),
        }

    def create_report(
        self,
        template_id: str,
        title: str,
        scope_id: str,
        data: Mapping[str, Any] | None = None,
    ) -> Report:
        """Create a draft report from an existing template."""
        template = self.get_template(template_id)
        cleaned = title.strip()
        if not cleaned:
            raise ValidationError("A report title is required")
        if len(cleaned) > MAX_TITLE_LENGTH:
            raise ValidationError(f"Report title must be at most {MAX_TITLE_LENGTH} characters")
        if not scope_id.strip():
            raise ValidationError("A report scope is required")
        snapshot = self.validate_snapshot(
            dict(data) if data is not None else self.collect_scope_data(scope_id)
        )
        report = Report(
            id=self._identifier("rep"),
            template_id=template.id,
            title=cleaned,
            scope_id=scope_id.strip(),
            status=ReportStatus.DRAFT,
            data_json=dump_data(snapshot),
        )
        return self.reports.create(report)

    def update_report_data(self, report_id: str, data: Mapping[str, Any]) -> Report:
        """Replace the data snapshot captured by a draft report."""
        report = self.get_report(report_id)
        if not report.is_draft:
            raise ConflictError("A finalised report cannot be edited")
        self.reports.set_snapshot(report_id, dump_data(self.validate_snapshot(data)))
        return self.get_report(report_id)

    def finalise_report(self, report_id: str) -> Report:
        """Move a draft report into the final state."""
        report = self.get_report(report_id)
        if report.is_final:
            raise ConflictError("The report is already finalised")
        template = self.get_template(report.template_id)
        if template.is_empty:
            raise ConflictError("A template without enabled sections cannot be finalised")
        self.reports.set_status(report_id, ReportStatus.FINAL)
        return self.get_report(report_id)

    def preview_report(
        self,
        report_id: str,
        report_format: ReportFormat | str | None = None,
        data: Mapping[str, Any] | None = None,
    ) -> RenderedReport:
        """Render a report without persisting an export job."""
        report = self.get_report(report_id)
        template = self.get_template(report.template_id)
        selected = ReportFormat.parse(report_format) if report_format else template.format
        snapshot = dict(data) if data is not None else report.data
        return render_report(template, report, snapshot, selected)

    def export_report(self, report_id: str, report_format: ReportFormat | str) -> ExportJob:
        """Render, persist and return an export job for a finalised report."""
        report = self.get_report(report_id)
        if report.is_draft:
            raise ConflictError("Finalise the report before exporting it")
        template = self.get_template(report.template_id)
        selected = ReportFormat.parse(report_format)
        rendered = render_report(template, report, report.data, selected)
        payload = render_export(rendered)
        job = ExportJob(
            id=self._identifier("exp"),
            report_id=report.id,
            format=selected,
            status=ExportStatus.COMPLETE,
            content=payload.content,
        )
        return self.exports.create(job)

    def list_exports(self, limit: int = 100) -> tuple[ExportJob, ...]:
        """Return the most recent export jobs first."""
        if limit < 1 or limit > 500:
            raise ValidationError("The export limit must be between 1 and 500")
        return tuple(self.exports.list_all(limit))

    def get_export(self, export_id: str) -> ExportJob:
        """Return an export job or raise :class:`NotFoundError`."""
        job = self.exports.get(export_id)
        if job is None:
            raise NotFoundError(f"Export job '{export_id}' does not exist")
        return job

    def stats(self) -> ReportStats:
        """Aggregate counters for the studio overview."""
        return ReportStats(
            templates=self.templates.count(),
            reports=self.reports.count(),
            draft_reports=self.reports.count_status(ReportStatus.DRAFT),
            final_reports=self.reports.count_status(ReportStatus.FINAL),
            exports=self.exports.count(),
            exports_by_format=self.exports.count_by_format(),
        )

    def parse_sections_json(self, raw: str) -> tuple[ReportSection, ...]:
        """Parse and normalise a stored ``sections_json`` string for API responses."""
        return parse_sections(raw)

    def validate_snapshot(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """Validate a user supplied snapshot before it is stored."""
        if len(data) > 200:
            raise ValidationError("A data snapshot may contain at most 200 keys")
        for key, value in data.items():
            if not str(key).strip():
                raise ValidationError("Data snapshot keys cannot be empty")
            if isinstance(value, (dict, list)) and len(value) > 1_000:
                raise ValidationError(f"Data snapshot value '{key}' is too large")
        return parse_data(dump_data(dict(data)))
