"""Business rules for chart authoring, ingestion and analysis.

The service validates caller input, owns identifier generation and decides
which data source feeds a chart. All geometry and reduction maths is delegated
to the pure helpers in :mod:`models`.
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.data_visualization.models import (
    DEFAULT_PALETTE,
    DEFAULT_TEAM_ID,
    MAX_LABEL_LENGTH,
    MAX_POINTS,
    MAX_SERIES,
    MAX_TITLE_LENGTH,
    PALETTES,
    AggregateOperation,
    AggregateResult,
    ChartGeometry,
    ChartOptions,
    ChartPayload,
    ChartSpec,
    ChartTheme,
    ChartType,
    DataPoint,
    GeometryBuilder,
    Palette,
    SortDirection,
    SortField,
    aggregate_by_category,
    dump_chart_payload,
    palette_colors,
    palette_descriptor,
    palette_names,
    parse_chart_payload,
)
from ctf_team_dashboard.features.data_visualization.store import VisualizationStore


def _identifier(prefix: str = "chart") -> str:
    """Generate a short unique identifier."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _clean_text(value: str, label: str, maximum: int) -> str:
    """Trim and validate a required text value."""
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"{label} must not be empty", details={"field": label})
    if len(cleaned) > maximum:
        raise ValidationError(
            f"{label} must not exceed {maximum} characters",
            details={"field": label, "maximum": maximum},
        )
    return cleaned


def _validate_payload(raw: str) -> tuple[ChartPayload, str]:
    """Parse, bound and canonicalise a ``series_json`` value."""
    try:
        payload = parse_chart_payload(raw)
    except ValueError as error:
        raise ValidationError(str(error), details={"field": "series_json"}) from error
    if len(payload.series) > MAX_SERIES:
        raise ValidationError(
            f"a chart accepts at most {MAX_SERIES} series",
            details={"field": "series_json", "maximum": MAX_SERIES},
        )
    if len(payload.points) > MAX_POINTS:
        raise ValidationError(
            f"a chart accepts at most {MAX_POINTS} inline points",
            details={"field": "series_json", "maximum": MAX_POINTS},
        )
    return payload, dump_chart_payload(payload)


def _validate_options(raw: str) -> tuple[ChartOptions, str]:
    """Parse and canonicalise an ``options_json`` value."""
    try:
        options = ChartOptions.parse(raw)
    except ValueError as error:
        raise ValidationError(str(error), details={"field": "options_json"}) from error
    return options, options.dump()


def _validate_palette(value: str) -> str:
    """Return a canonical palette identifier."""
    try:
        return palette_descriptor(value).id
    except ValueError as error:
        raise ValidationError(str(error), details={"field": "palette"}) from error


def _validate_chart_type(value: ChartType | str) -> ChartType:
    """Return a validated chart type."""
    try:
        return ChartType.parse(str(value))
    except ValueError as error:
        raise ValidationError(str(error), details={"field": "chart_type"}) from error


def _validate_points(points: Iterable[DataPoint]) -> tuple[DataPoint, ...]:
    """Validate a batch of ingested observations."""
    cleaned: list[DataPoint] = []
    for point in points:
        label = _clean_text(point.label, "point label", MAX_LABEL_LENGTH)
        category = (
            _clean_text(point.category, "point category", MAX_LABEL_LENGTH)
            if point.category.strip()
            else DEFAULT_TEAM_ID
        )
        if not math.isfinite(point.value):
            raise ValidationError("point value must be finite", details={"field": "value"})
        cleaned.append(DataPoint(label=label, value=point.value, category=category))
    if len(cleaned) > MAX_POINTS:
        raise ValidationError(
            f"a chart accepts at most {MAX_POINTS} ingested points",
            details={"field": "points", "maximum": MAX_POINTS},
        )
    return tuple(cleaned)


def _validate_pagination(limit: int, offset: int) -> tuple[int, int]:
    """Validate list pagination arguments."""
    if not 1 <= limit <= 100:
        raise ValidationError("limit must be between 1 and 100", details={"field": "limit"})
    if offset < 0:
        raise ValidationError("offset must not be negative", details={"field": "offset"})
    return limit, offset


class VisualizationService:
    """Application service for the visualisation feature."""

    def __init__(self, store: VisualizationStore | None = None) -> None:
        self.store = store or VisualizationStore()

    def get_chart(self, chart_id: str) -> ChartSpec:
        """Return a chart or raise :class:`NotFoundError`."""
        chart = self.store.charts.get(chart_id)
        if chart is None:
            raise NotFoundError(f"Chart {chart_id!r} does not exist")
        return chart

    def list_charts(
        self,
        *,
        team_id: str | None = None,
        chart_type: ChartType | str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChartSpec]:
        """Return charts matching optional filters."""
        limit, offset = _validate_pagination(limit, offset)
        resolved_type = _validate_chart_type(chart_type) if chart_type else None
        return self.store.charts.list_all(
            team_id=team_id.strip() or None if team_id else None,
            chart_type=resolved_type,
            limit=limit,
            offset=offset,
        )

    def create_chart(
        self,
        *,
        chart_id: str | None = None,
        team_id: str = DEFAULT_TEAM_ID,
        title: str,
        chart_type: ChartType | str,
        series_json: str = "[]",
        options_json: str = "{}",
        palette: str = DEFAULT_PALETTE,
    ) -> ChartSpec:
        """Create and persist a validated chart specification."""
        identifier = _clean_text(chart_id, "id", MAX_LABEL_LENGTH) if chart_id else _identifier()
        if self.store.charts.has_id(identifier):
            raise ConflictError(f"Chart {identifier!r} already exists")
        resolved_type = _validate_chart_type(chart_type)
        _payload, canonical_payload = _validate_payload(series_json)
        _options, canonical_options = _validate_options(options_json)
        now: datetime = utcnow()
        chart = ChartSpec(
            id=identifier,
            team_id=_clean_text(team_id, "team_id", MAX_LABEL_LENGTH),
            title=_clean_text(title, "title", MAX_TITLE_LENGTH),
            chart_type=resolved_type,
            series_json=canonical_payload,
            options_json=canonical_options,
            palette=_validate_palette(palette),
            created_at=now,
            updated_at=now,
        )
        return self.store.charts.insert(chart)

    def update_chart(
        self,
        chart_id: str,
        *,
        title: str | None = None,
        chart_type: ChartType | str | None = None,
        series_json: str | None = None,
        options_json: str | None = None,
        palette: str | None = None,
    ) -> ChartSpec:
        """Apply a partial update to an existing chart specification."""
        chart = self.get_chart(chart_id)
        series = chart.series_json
        options = chart.options_json
        if series_json is not None:
            _payload, series = _validate_payload(series_json)
        if options_json is not None:
            _options, options = _validate_options(options_json)
        updated = ChartSpec(
            id=chart.id,
            team_id=chart.team_id,
            title=_clean_text(title, "title", MAX_TITLE_LENGTH)
            if title is not None
            else chart.title,
            chart_type=_validate_chart_type(chart_type)
            if chart_type is not None
            else chart.chart_type,
            series_json=series,
            options_json=options,
            palette=_validate_palette(palette) if palette is not None else chart.palette,
            created_at=chart.created_at,
            updated_at=utcnow(),
        )
        return self.store.charts.update(updated)

    def ingest_data(
        self,
        chart_id: str,
        points: Iterable[DataPoint],
        *,
        replace: bool = True,
    ) -> tuple[DataPoint, ...]:
        """Validate and persist observations for a chart."""
        chart = self.get_chart(chart_id)
        cleaned = _validate_points(points)
        existing = self.store.data.count_for_chart(chart_id)
        if existing + len(cleaned) > MAX_POINTS:
            raise ValidationError(
                f"a chart accepts at most {MAX_POINTS} ingested points",
                details={"field": "points", "maximum": MAX_POINTS},
            )
        if replace:
            self.store.data.replace_points(chart_id, cleaned)
        else:
            self.store.data.append_points(chart_id, cleaned)
        self.store.charts.update(
            ChartSpec(
                id=chart.id,
                team_id=chart.team_id,
                title=chart.title,
                chart_type=chart.chart_type,
                series_json=chart.series_json,
                options_json=chart.options_json,
                palette=chart.palette,
                created_at=chart.created_at,
                updated_at=utcnow(),
            )
        )
        return self.store.data.list_for_chart(chart_id)

    def list_data(self, chart_id: str) -> tuple[DataPoint, ...]:
        """Return the observations ingested into a chart."""
        self.get_chart(chart_id)
        return self.store.data.list_for_chart(chart_id)

    def _points_for(self, chart: ChartSpec) -> tuple[DataPoint, ...]:
        """Use ingested data when available, otherwise inline series data."""
        ingested = self.store.data.list_for_chart(chart.id)
        return ingested if ingested else chart.payload.points

    def geometry(
        self,
        chart_id: str,
        overrides: Mapping[str, Any] | None = None,
    ) -> ChartGeometry:
        """Compute render geometry for a chart, honouring request overrides."""
        chart = self.get_chart(chart_id)
        try:
            options = chart.options.merged(overrides or {})
        except ValueError as error:
            raise ValidationError(str(error), details={"field": "options"}) from error
        builder = GeometryBuilder(
            chart_id=chart.id,
            chart_type=chart.chart_type,
            payload=chart.payload,
            points=self._points_for(chart),
            options=options,
            palette=chart.palette,
        )
        return builder.build()

    def aggregate(
        self,
        chart_id: str,
        *,
        operation: AggregateOperation | str | None = None,
        category: str | None = None,
        sort: SortField | str | None = None,
        direction: SortDirection | str | None = None,
        limit: int | None = None,
    ) -> AggregateResult:
        """Reduce the chart's points by category."""
        chart = self.get_chart(chart_id)
        try:
            operation_value = (
                AggregateOperation.parse(str(operation))
                if operation is not None
                else chart.options.operation
            )
            sort_value = SortField.parse(str(sort)) if sort is not None else SortField.VALUE
            direction_value = (
                SortDirection.parse(str(direction)) if direction is not None else SortDirection.DESC
            )
        except ValueError as error:
            raise ValidationError(str(error), details={"field": "aggregate"}) from error
        if limit is not None and not 1 <= limit <= MAX_POINTS:
            raise ValidationError(
                f"limit must be between 1 and {MAX_POINTS}", details={"field": "limit"}
            )
        colors = palette_colors(chart.palette, chart.options.theme)
        rows = aggregate_by_category(
            self._points_for(chart),
            operation_value,
            colors=colors,
            sort=sort_value,
            direction=direction_value,
            limit=limit,
            category_filter=category,
        )
        return AggregateResult(
            chart_id=chart.id,
            operation=operation_value,
            rows=rows,
            total=sum(row.value for row in rows),
            categories=len(rows),
        )

    def palettes(self) -> tuple[Palette, ...]:
        """Return every palette available to the UI."""
        return tuple(PALETTES[name] for name in palette_names())

    def palette(self, name: str) -> Palette:
        """Return one palette descriptor."""
        try:
            return palette_descriptor(name)
        except ValueError as error:
            raise NotFoundError(str(error)) from error

    def theme_for(self, chart: ChartSpec, override: str | None = None) -> ChartTheme:
        """Resolve the active palette theme for a chart."""
        if override:
            try:
                return ChartTheme.parse(str(override))
            except ValueError as error:
                raise ValidationError(str(error), details={"field": "theme"}) from error
        return chart.options.theme


def available_chart_types() -> tuple[str, ...]:
    """Return the identifiers of every supported chart type."""
    return tuple(ChartType.values())


def validate_point_values(points: Sequence[DataPoint]) -> tuple[float, ...]:
    """Return point values after rejecting non-finite numbers."""
    cleaned = _validate_points(points)
    return tuple(point.value for point in cleaned)
