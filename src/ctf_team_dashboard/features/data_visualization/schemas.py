"""Typed request and response schemas for the visualisation API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ctf_team_dashboard.features.data_visualization.models import (
    DEFAULT_PALETTE,
    DEFAULT_TEAM_ID,
    MAX_LABEL_LENGTH,
    MAX_TITLE_LENGTH,
    AggregateOperation,
    AggregateResult,
    AggregateRow,
    BarShape,
    ChartGeometry,
    ChartSpec,
    ChartTheme,
    ChartType,
    DataPoint,
    GeometryDatum,
    LegendItem,
    LineShape,
    Palette,
    PlotPoint,
    RadarAxis,
    RadarShape,
    SankeyFlowLayout,
    SankeyNodeLayout,
    ScaleType,
    Tick,
)


class VisualizationModel(BaseModel):
    """Base model with serialisation rules shared by visualisation schemas."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DataPointCreate(VisualizationModel):
    """One observation supplied by an ingestion request."""

    label: str = Field(min_length=1, max_length=MAX_LABEL_LENGTH)
    value: float
    category: str = Field(default=DEFAULT_TEAM_ID, max_length=MAX_LABEL_LENGTH)


class DataIngestRequest(VisualizationModel):
    """Payload accepted by the data ingestion endpoint."""

    points: list[DataPointCreate] = Field(default_factory=list)
    replace: bool = True


class ChartSpecCreate(VisualizationModel):
    """Payload used to create a chart specification."""

    id: str | None = Field(default=None, max_length=MAX_LABEL_LENGTH)
    team_id: str = Field(default=DEFAULT_TEAM_ID, max_length=MAX_LABEL_LENGTH)
    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    chart_type: ChartType
    series_json: str = "[]"
    options_json: str = "{}"
    palette: str = DEFAULT_PALETTE


class ChartSpecUpdate(VisualizationModel):
    """Partial payload used to update a chart specification."""

    title: str | None = Field(default=None, min_length=1, max_length=MAX_TITLE_LENGTH)
    chart_type: ChartType | None = None
    series_json: str | None = None
    options_json: str | None = None
    palette: str | None = None


class DataPointRead(VisualizationModel):
    """A stored or inline observation returned by the API."""

    label: str
    value: float
    category: str
    series: str = ""

    @classmethod
    def from_domain(cls, point: DataPoint) -> DataPointRead:
        """Build an API model from a domain point."""
        return cls(
            label=point.label, value=point.value, category=point.category, series=point.series
        )


class ChartSpecRead(VisualizationModel):
    """A persisted chart specification."""

    id: str
    team_id: str
    title: str
    chart_type: ChartType
    series_json: str
    options_json: str
    palette: str
    created_at: datetime
    updated_at: datetime
    point_count: int
    is_empty: bool

    @classmethod
    def from_domain(cls, chart: ChartSpec, point_count: int = 0) -> ChartSpecRead:
        """Build an API model from a chart specification."""
        return cls(
            id=chart.id,
            team_id=chart.team_id,
            title=chart.title,
            chart_type=chart.chart_type,
            series_json=chart.series_json,
            options_json=chart.options_json,
            palette=chart.palette,
            created_at=chart.created_at,
            updated_at=chart.updated_at,
            point_count=point_count,
            is_empty=chart.is_empty,
        )


class PaletteRead(VisualizationModel):
    """A categorical colour palette offered to the UI."""

    id: str
    name: str
    description: str
    colors: list[str]
    dark_colors: list[str]
    size: int

    @classmethod
    def from_domain(cls, palette: Palette) -> PaletteRead:
        """Build an API model from a palette descriptor."""
        return cls(
            id=palette.id,
            name=palette.name,
            description=palette.description,
            colors=list(palette.colors),
            dark_colors=list(palette.dark_colors),
            size=palette.size,
        )


class TickRead(VisualizationModel):
    """An axis tick with its projected position."""

    value: float
    label: str
    position: float

    @classmethod
    def from_domain(cls, tick: Tick) -> TickRead:
        """Build an API model from a domain tick."""
        return cls(value=tick.value, label=tick.label, position=tick.position)


class BarRead(VisualizationModel):
    """A positioned bar mark."""

    label: str
    category: str
    series: str
    value: float
    color: str
    x: float
    y: float
    width: float
    height: float
    tooltip: str

    @classmethod
    def from_domain(cls, bar: BarShape) -> BarRead:
        """Build an API model from a bar shape."""
        return cls(
            label=bar.label,
            category=bar.category,
            series=bar.series,
            value=bar.value,
            color=bar.color,
            x=bar.x,
            y=bar.y,
            width=bar.width,
            height=bar.height,
            tooltip=bar.tooltip,
        )


class PlotPointRead(VisualizationModel):
    """A point projected into SVG coordinates."""

    x: float
    y: float
    label: str
    value: float
    series: str
    color: str
    tooltip: str

    @classmethod
    def from_domain(cls, point: PlotPoint) -> PlotPointRead:
        """Build an API model from a projected point."""
        return cls(
            x=point.x,
            y=point.y,
            label=point.label,
            value=point.value,
            series=point.series,
            color=point.color,
            tooltip=point.tooltip,
        )


class LineRead(VisualizationModel):
    """A projected line series."""

    name: str
    color: str
    points: list[PlotPointRead]
    path: str
    area_path: str

    @classmethod
    def from_domain(cls, line: LineShape) -> LineRead:
        """Build an API model from a line shape."""
        return cls(
            name=line.name,
            color=line.color,
            points=[PlotPointRead.from_domain(point) for point in line.points],
            path=line.path,
            area_path=line.area_path,
        )


class RadarAxisRead(VisualizationModel):
    """A normalised radar spoke."""

    label: str
    value: float
    ratio: float
    angle: float
    x: float
    y: float

    @classmethod
    def from_domain(cls, axis: RadarAxis) -> RadarAxisRead:
        """Build an API model from a radar axis."""
        return cls(
            label=axis.label,
            value=axis.value,
            ratio=axis.ratio,
            angle=axis.angle,
            x=axis.x,
            y=axis.y,
        )


class RadarShapeRead(VisualizationModel):
    """A radar polygon."""

    name: str
    color: str
    points: list[list[float]]
    path: str

    @classmethod
    def from_domain(cls, shape: RadarShape) -> RadarShapeRead:
        """Build an API model from a radar shape."""
        return cls(
            name=shape.name,
            color=shape.color,
            points=[[x_coord, y_coord] for x_coord, y_coord in shape.points],
            path=shape.path,
        )


class SankeyNodeRead(VisualizationModel):
    """A positioned Sankey node."""

    id: str
    label: str
    value: float
    depth: int
    x: float
    y: float
    width: float
    height: float
    color: str

    @classmethod
    def from_domain(cls, node: SankeyNodeLayout) -> SankeyNodeRead:
        """Build an API model from a Sankey node."""
        return cls(
            id=node.id,
            label=node.label,
            value=node.value,
            depth=node.depth,
            x=node.x,
            y=node.y,
            width=node.width,
            height=node.height,
            color=node.color,
        )


class SankeyFlowRead(VisualizationModel):
    """A positioned Sankey ribbon."""

    source: str
    target: str
    value: float
    width: float
    path: str
    color: str

    @classmethod
    def from_domain(cls, flow: SankeyFlowLayout) -> SankeyFlowRead:
        """Build an API model from a Sankey flow."""
        return cls(
            source=flow.source,
            target=flow.target,
            value=flow.value,
            width=flow.width,
            path=flow.path,
            color=flow.color,
        )


class LegendRead(VisualizationModel):
    """A legend entry."""

    label: str
    color: str
    kind: str

    @classmethod
    def from_domain(cls, item: LegendItem) -> LegendRead:
        """Build an API model from a legend item."""
        return cls(label=item.label, color=item.color, kind=item.kind)


class GeometryDatumRead(VisualizationModel):
    """A row in the accessible data table fallback."""

    label: str
    category: str
    series: str
    value: float
    color: str

    @classmethod
    def from_domain(cls, datum: GeometryDatum) -> GeometryDatumRead:
        """Build an API model from a geometry datum."""
        return cls(
            label=datum.label,
            category=datum.category,
            series=datum.series,
            value=datum.value,
            color=datum.color,
        )


class GeometryRead(VisualizationModel):
    """Complete render geometry for a chart."""

    chart_id: str
    chart_type: ChartType
    width: float
    height: float
    padding: float
    palette: str
    theme: ChartTheme
    scale: ScaleType
    domain_min: float
    domain_max: float
    ticks: list[TickRead]
    bars: list[BarRead]
    lines: list[LineRead]
    radar_axes: list[RadarAxisRead]
    radar_shapes: list[RadarShapeRead]
    radar_rings: list[float]
    sankey_nodes: list[SankeyNodeRead]
    sankey_flows: list[SankeyFlowRead]
    sparkline_path: str
    sparkline_area: str
    legend: list[LegendRead]
    data: list[GeometryDatumRead]
    has_data: bool
    mark_count: int

    @classmethod
    def from_domain(cls, geometry: ChartGeometry) -> GeometryRead:
        """Build an API model from computed geometry."""
        return cls(
            chart_id=geometry.chart_id,
            chart_type=geometry.chart_type,
            width=geometry.width,
            height=geometry.height,
            padding=geometry.padding,
            palette=geometry.palette,
            theme=geometry.theme,
            scale=geometry.scale,
            domain_min=geometry.domain_min,
            domain_max=geometry.domain_max,
            ticks=[TickRead.from_domain(tick) for tick in geometry.ticks],
            bars=[BarRead.from_domain(bar) for bar in geometry.bars],
            lines=[LineRead.from_domain(line) for line in geometry.lines],
            radar_axes=[RadarAxisRead.from_domain(axis) for axis in geometry.radar_axes],
            radar_shapes=[RadarShapeRead.from_domain(shape) for shape in geometry.radar_shapes],
            radar_rings=list(geometry.radar_rings),
            sankey_nodes=[SankeyNodeRead.from_domain(node) for node in geometry.sankey_nodes],
            sankey_flows=[SankeyFlowRead.from_domain(flow) for flow in geometry.sankey_flows],
            sparkline_path=geometry.sparkline_path,
            sparkline_area=geometry.sparkline_area,
            legend=[LegendRead.from_domain(item) for item in geometry.legend],
            data=[GeometryDatumRead.from_domain(datum) for datum in geometry.data],
            has_data=geometry.has_data,
            mark_count=geometry.mark_count,
        )


class AggregateRowRead(VisualizationModel):
    """One aggregated category."""

    category: str
    operation: AggregateOperation
    value: float
    count: int
    color: str
    display: str

    @classmethod
    def from_domain(cls, row: AggregateRow) -> AggregateRowRead:
        """Build an API model from an aggregate row."""
        return cls(
            category=row.category,
            operation=row.operation,
            value=row.value,
            count=row.count,
            color=row.color,
            display=row.display,
        )


class AggregateResultRead(VisualizationModel):
    """The result of a category aggregation."""

    chart_id: str
    operation: AggregateOperation
    rows: list[AggregateRowRead]
    total: float
    categories: int
    is_empty: bool

    @classmethod
    def from_domain(cls, result: AggregateResult) -> AggregateResultRead:
        """Build an API model from an aggregate result."""
        return cls(
            chart_id=result.chart_id,
            operation=result.operation,
            rows=[AggregateRowRead.from_domain(row) for row in result.rows],
            total=result.total,
            categories=result.categories,
            is_empty=result.is_empty,
        )


def geometry_overrides(**values: Any) -> dict[str, Any]:
    """Build a geometry override mapping from optional query parameters."""
    return {key: value for key, value in values.items() if value is not None}


__all__ = [
    "AggregateResultRead",
    "AggregateRowRead",
    "ChartSpecCreate",
    "ChartSpecRead",
    "ChartSpecUpdate",
    "DataIngestRequest",
    "DataPointCreate",
    "DataPointRead",
    "GeometryRead",
    "PaletteRead",
    "VisualizationModel",
    "geometry_overrides",
]
