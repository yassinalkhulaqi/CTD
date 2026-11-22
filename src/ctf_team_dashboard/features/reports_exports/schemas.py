"""Typed request and response schemas for the reporting API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import (
    ExportJob,
    RenderedReport,
    RenderedSection,
    Report,
    ReportFormat,
    ReportSection,
    ReportStats,
    ReportStatus,
    ReportTemplate,
    SectionKind,
    TemplateScope,
)


class ReportApiModel(BaseModel):
    """Base model with the shared API serialisation configuration."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SectionCreate(ReportApiModel):
    """A section configuration supplied by the report builder."""

    id: str | None = Field(default=None, max_length=80)
    title: str = Field(default="Section", max_length=96)
    kind: SectionKind = SectionKind.TEXT
    body: str = Field(default="", max_length=8_000)
    source: str = Field(default="", max_length=120)
    columns: list[str] = Field(default_factory=list)
    enabled: bool = True
    order: int = 0


class TemplateCreate(ReportApiModel):
    """Payload used to create a report template."""

    name: str = Field(min_length=1, max_length=96)
    sections: list[SectionCreate] = Field(default_factory=list)
    format: ReportFormat = ReportFormat.MARKDOWN
    scope: TemplateScope = TemplateScope.TEAM


class ReportCreate(ReportApiModel):
    """Payload used to create a draft report."""

    template_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=140)
    scope_id: str = Field(min_length=1)
    data: dict[str, Any] | None = None


class SnapshotUpdate(ReportApiModel):
    """Payload used to replace a report's captured data snapshot."""

    data: dict[str, Any] = Field(default_factory=dict)


class ExportRequest(ReportApiModel):
    """Payload selecting the serialisation format of an export."""

    format: ReportFormat = ReportFormat.MARKDOWN


class SectionRead(ReportApiModel):
    """A section configuration returned by the API."""

    id: str
    title: str
    kind: SectionKind
    body: str
    source: str
    columns: list[str]
    enabled: bool
    order: int
    placeholder_tokens: list[str]

    @classmethod
    def from_model(cls, section: ReportSection) -> SectionRead:
        """Build a read model from a domain section."""
        return cls(
            id=section.id,
            title=section.title,
            kind=section.kind,
            body=section.body,
            source=section.source,
            columns=list(section.columns),
            enabled=section.enabled,
            order=section.order,
            placeholder_tokens=list(section.placeholder_tokens),
        )


class TemplateRead(ReportApiModel):
    """A report template returned by the API."""

    id: str
    name: str
    format: ReportFormat
    scope: TemplateScope
    updated_at: datetime
    sections: list[SectionRead]
    section_count: int
    description: str

    @classmethod
    def from_model(cls, template: ReportTemplate) -> TemplateRead:
        """Build a read model from a domain template."""
        return cls(
            id=template.id,
            name=template.name,
            format=template.format,
            scope=template.scope,
            updated_at=template.updated_at,
            sections=[SectionRead.from_model(section) for section in template.sections],
            section_count=template.section_count,
            description=template.description,
        )


class ReportRead(ReportApiModel):
    """A report instance returned by the API."""

    id: str
    template_id: str
    title: str
    scope_id: str
    status: ReportStatus
    created_at: datetime
    data: dict[str, Any]
    is_final: bool

    @classmethod
    def from_model(cls, report: Report) -> ReportRead:
        """Build a read model from a domain report."""
        return cls(
            id=report.id,
            template_id=report.template_id,
            title=report.title,
            scope_id=report.scope_id,
            status=report.status,
            created_at=report.created_at,
            data=report.data,
            is_final=report.is_final,
        )


class ExportRead(ReportApiModel):
    """A materialised export returned by the API."""

    id: str
    report_id: str
    format: ReportFormat
    status: str
    content: str
    created_at: datetime
    byte_size: int
    line_count: int
    extension: str
    mime_type: str
    is_complete: bool

    @classmethod
    def from_model(cls, job: ExportJob) -> ExportRead:
        """Build a read model from a domain export job."""
        return cls(
            id=job.id,
            report_id=job.report_id,
            format=job.format,
            status=job.status.value,
            content=job.content,
            created_at=job.created_at,
            byte_size=job.byte_size,
            line_count=job.line_count,
            extension=job.extension,
            mime_type=job.mime_type,
            is_complete=job.is_complete,
        )


class RenderedSectionRead(ReportApiModel):
    """Structured content of one preview section."""

    id: str
    title: str
    kind: SectionKind
    text: str
    columns: list[str]
    rows: list[list[str]]
    items: list[str]
    metrics: list[list[str]]
    warnings: list[str]
    row_count: int
    is_empty: bool

    @classmethod
    def from_model(cls, section: RenderedSection) -> RenderedSectionRead:
        """Build a read model from a rendered section."""
        return cls(
            id=section.id,
            title=section.title,
            kind=section.kind,
            text=section.text,
            columns=list(section.columns),
            rows=[list(row) for row in section.rows],
            items=list(section.items),
            metrics=[list(metric) for metric in section.metrics],
            warnings=list(section.warnings),
            row_count=section.row_count,
            is_empty=section.is_empty,
        )


class PreviewRead(ReportApiModel):
    """A rendered report preview."""

    title: str
    format: ReportFormat
    generated_at: datetime
    summary: dict[str, int]
    meta: dict[str, str]
    warnings: list[str]
    sections: list[RenderedSectionRead]
    section_count: int
    total_rows: int
    has_warnings: bool
    is_empty: bool

    @classmethod
    def from_model(cls, rendered: RenderedReport) -> PreviewRead:
        """Build a read model from a rendered report."""
        return cls(
            title=rendered.title,
            format=rendered.format,
            generated_at=rendered.generated_at,
            summary=rendered.summary,
            meta=rendered.meta,
            warnings=list(rendered.warnings),
            sections=[RenderedSectionRead.from_model(section) for section in rendered.sections],
            section_count=rendered.section_count,
            total_rows=rendered.total_rows,
            has_warnings=rendered.has_warnings,
            is_empty=rendered.is_empty,
        )


class ReportStatsRead(ReportApiModel):
    """Aggregate counters for the report studio."""

    templates: int
    reports: int
    draft_reports: int
    final_reports: int
    exports: int
    exports_by_format: dict[str, int]
    total_artifacts: int
    finalisation_rate: float

    @classmethod
    def from_model(cls, stats: ReportStats) -> ReportStatsRead:
        """Build a read model from domain statistics."""
        return cls(
            templates=stats.templates,
            reports=stats.reports,
            draft_reports=stats.draft_reports,
            final_reports=stats.final_reports,
            exports=stats.exports,
            exports_by_format=dict(stats.exports_by_format),
            total_artifacts=stats.total_artifacts,
            finalisation_rate=stats.finalisation_rate,
        )
