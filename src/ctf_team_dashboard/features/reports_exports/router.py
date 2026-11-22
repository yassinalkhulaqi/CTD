"""HTTP endpoints of the report studio and export pipeline."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from .models import ReportFormat, ReportStatus
from .schemas import (
    ExportRead,
    ExportRequest,
    PreviewRead,
    ReportCreate,
    ReportRead,
    ReportStatsRead,
    SnapshotUpdate,
    TemplateCreate,
    TemplateRead,
)
from .service import ReportService

router = APIRouter(prefix="/api/reports", tags=["reports"])


def get_report_service() -> ReportService:
    """Dependency returning a service bound to the shared database."""
    return ReportService()


ServiceDep = Annotated[ReportService, Depends(get_report_service)]
StatusQuery = Annotated[ReportStatus | None, Query(alias="status")]
FormatQuery = Annotated[ReportFormat | None, Query(alias="format")]
LimitQuery = Annotated[int, Query(ge=1, le=500)]


@router.get("/templates", response_model=list[TemplateRead])
def list_templates(service: ServiceDep) -> list[TemplateRead]:
    """Return every saved report template."""
    return [TemplateRead.from_model(template) for template in service.list_templates()]


@router.post(
    "/templates",
    response_model=TemplateRead,
    status_code=status.HTTP_201_CREATED,
)
def create_template(payload: TemplateCreate, service: ServiceDep) -> TemplateRead:
    """Create a reusable report template."""
    sections = [section.model_dump(exclude_none=True) for section in payload.sections]
    template = service.create_template(payload.name, sections, payload.format, payload.scope)
    return TemplateRead.from_model(template)


@router.get("/exports", response_model=list[ExportRead])
def list_exports(
    service: ServiceDep,
    limit: LimitQuery = 100,
) -> list[ExportRead]:
    """Return the most recent export jobs."""
    return [ExportRead.from_model(job) for job in service.list_exports(limit)]


@router.get("/stats", response_model=ReportStatsRead)
def stats(service: ServiceDep) -> ReportStatsRead:
    """Return aggregate counters for the studio overview."""
    return ReportStatsRead.from_model(service.stats())


@router.get("", response_model=list[ReportRead])
def list_reports(
    service: ServiceDep,
    report_status: StatusQuery = None,
    limit: LimitQuery = 100,
) -> list[ReportRead]:
    """Return reports, optionally filtered by lifecycle status."""
    return [ReportRead.from_model(report) for report in service.list_reports(report_status, limit)]


@router.post("", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
def create_report(payload: ReportCreate, service: ServiceDep) -> ReportRead:
    """Create a draft report from a template and an optional data snapshot."""
    report = service.create_report(
        template_id=payload.template_id,
        title=payload.title,
        scope_id=payload.scope_id,
        data=payload.data,
    )
    return ReportRead.from_model(report)


@router.patch("/{report_id}/data", response_model=ReportRead)
def update_snapshot(
    report_id: str,
    payload: SnapshotUpdate,
    service: ServiceDep,
) -> ReportRead:
    """Replace the data snapshot captured by a draft report."""
    report = service.update_report_data(report_id, payload.data)
    return ReportRead.from_model(report)


@router.get("/{report_id}", response_model=ReportRead)
def get_report(report_id: str, service: ServiceDep) -> ReportRead:
    """Return one report with its captured data snapshot."""
    return ReportRead.from_model(service.get_report(report_id))


@router.post("/{report_id}/finalise", response_model=ReportRead)
def finalise_report(report_id: str, service: ServiceDep) -> ReportRead:
    """Finalise a draft report so it can be exported."""
    return ReportRead.from_model(service.finalise_report(report_id))


@router.post(
    "/{report_id}/export",
    response_model=ExportRead,
    status_code=status.HTTP_201_CREATED,
)
def export_report(
    report_id: str,
    payload: ExportRequest,
    service: ServiceDep,
) -> ExportRead:
    """Render and persist an export in one of the four supported formats."""
    job = service.export_report(report_id, payload.format)
    return ExportRead.from_model(job)


@router.get("/{report_id}/preview", response_model=PreviewRead)
def preview_report(
    report_id: str,
    service: ServiceDep,
    report_format: FormatQuery = None,
) -> PreviewRead:
    """Render a live preview without creating an export job."""
    rendered = service.preview_report(report_id, report_format)
    return PreviewRead.from_model(rendered)
