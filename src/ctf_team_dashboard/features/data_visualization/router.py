"""HTTP endpoints for the advanced visualisation feature."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from ctf_team_dashboard.features.data_visualization.models import (
    AggregateOperation,
    ChartTheme,
    ChartType,
    DataPoint,
    ScaleType,
    SortDirection,
    SortField,
)
from ctf_team_dashboard.features.data_visualization.schemas import (
    AggregateResultRead,
    ChartSpecCreate,
    ChartSpecRead,
    ChartSpecUpdate,
    DataIngestRequest,
    DataPointRead,
    GeometryRead,
    PaletteRead,
    geometry_overrides,
)
from ctf_team_dashboard.features.data_visualization.service import VisualizationService

router = APIRouter(prefix="/api/visualizations", tags=["visualizations"])


def get_visualization_service() -> VisualizationService:
    """Dependency returning a service bound to the shared database."""
    return VisualizationService()


VisualizationServiceDep = Annotated[VisualizationService, Depends(get_visualization_service)]


def _spec_read(service: VisualizationService, chart_id: str) -> ChartSpecRead:
    """Build a specification response including its ingested point count."""
    chart = service.get_chart(chart_id)
    return ChartSpecRead.from_domain(chart, len(service.list_data(chart_id)))


@router.get("", response_model=list[ChartSpecRead])
def list_visualizations(
    service: VisualizationServiceDep,
    team_id: str | None = None,
    chart_type: ChartType | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ChartSpecRead]:
    """Return chart specifications with optional filters and pagination."""
    charts = service.list_charts(
        team_id=team_id,
        chart_type=chart_type,
        limit=limit,
        offset=offset,
    )
    return [_spec_read(service, chart.id) for chart in charts]


@router.post(
    "",
    response_model=ChartSpecRead,
    status_code=status.HTTP_201_CREATED,
)
def create_visualization(
    payload: ChartSpecCreate,
    service: VisualizationServiceDep,
) -> ChartSpecRead:
    """Create a chart specification."""
    chart = service.create_chart(
        chart_id=payload.id,
        team_id=payload.team_id,
        title=payload.title,
        chart_type=payload.chart_type,
        series_json=payload.series_json,
        options_json=payload.options_json,
        palette=payload.palette,
    )
    return ChartSpecRead.from_domain(chart)


@router.get("/palettes", response_model=list[PaletteRead])
def list_palettes(service: VisualizationServiceDep) -> list[PaletteRead]:
    """Return the categorical palettes understood by the chart renderers."""
    return [PaletteRead.from_domain(palette) for palette in service.palettes()]


@router.get("/{chart_id}", response_model=ChartSpecRead)
def get_visualization(chart_id: str, service: VisualizationServiceDep) -> ChartSpecRead:
    """Return a single chart specification."""
    return _spec_read(service, chart_id)


@router.put("/{chart_id}", response_model=ChartSpecRead)
def update_visualization(
    chart_id: str,
    payload: ChartSpecUpdate,
    service: VisualizationServiceDep,
) -> ChartSpecRead:
    """Update the mutable fields of a chart specification."""
    chart = service.update_chart(
        chart_id,
        title=payload.title,
        chart_type=payload.chart_type,
        series_json=payload.series_json,
        options_json=payload.options_json,
        palette=payload.palette,
    )
    return _spec_read(service, chart.id)


@router.post(
    "/{chart_id}/data",
    response_model=list[DataPointRead],
    status_code=status.HTTP_201_CREATED,
)
def ingest_visualization_data(
    chart_id: str,
    payload: DataIngestRequest,
    service: VisualizationServiceDep,
) -> list[DataPointRead]:
    """Ingest a batch of observations into a chart."""
    points = [
        DataPoint(label=item.label, value=item.value, category=item.category)
        for item in payload.points
    ]
    stored = service.ingest_data(chart_id, points, replace=payload.replace)
    return [DataPointRead.from_domain(point) for point in stored]


@router.get("/{chart_id}/data", response_model=list[DataPointRead])
def list_visualization_data(
    chart_id: str,
    service: VisualizationServiceDep,
) -> list[DataPointRead]:
    """Return the observations stored for a chart."""
    return [DataPointRead.from_domain(point) for point in service.list_data(chart_id)]


@router.get("/{chart_id}/geometry", response_model=GeometryRead)
def get_geometry(
    chart_id: str,
    service: VisualizationServiceDep,
    scale: ScaleType | None = None,
    theme: ChartTheme | None = None,
    sort: SortField | None = None,
    direction: SortDirection | None = None,
    tick_count: int | None = Query(default=None, ge=2, le=12),
    limit: int | None = Query(default=None, ge=1, le=500),
    width: float | None = Query(default=None, ge=120, le=2000),
    height: float | None = Query(default=None, ge=80, le=1200),
    padding: float | None = Query(default=None, ge=0, le=100),
    radar_max: float | None = Query(default=None, gt=0),
) -> GeometryRead:
    """Compute SVG geometry for a chart with optional request overrides."""
    overrides = geometry_overrides(
        scale=scale,
        theme=theme,
        sort=sort,
        direction=direction,
        tick_count=tick_count,
        limit=limit,
        width=width,
        height=height,
        padding=padding,
        radar_max=radar_max,
    )
    return GeometryRead.from_domain(service.geometry(chart_id, overrides))


@router.get("/{chart_id}/aggregate", response_model=AggregateResultRead)
def get_aggregate(
    chart_id: str,
    service: VisualizationServiceDep,
    operation: AggregateOperation | None = None,
    category: str | None = None,
    sort: SortField | None = None,
    direction: SortDirection | None = None,
    limit: int | None = Query(default=None, ge=1, le=500),
) -> AggregateResultRead:
    """Reduce chart observations by category."""
    result = service.aggregate(
        chart_id,
        operation=operation,
        category=category,
        sort=sort,
        direction=direction,
        limit=limit,
    )
    return AggregateResultRead.from_domain(result)
