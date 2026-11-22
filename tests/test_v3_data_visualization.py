"""Tests for the V3 advanced data visualisation feature.

The suite covers pure geometry maths, persistence, service rules and the
mounted HTTP API against the isolated fixtures supplied by the foundation.
"""

from __future__ import annotations

import json
import math

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.db.engine import Database
from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.data_visualization.models import (
    PALETTES,
    AggregateOperation,
    ChartOptions,
    ChartSpec,
    ChartType,
    DataPoint,
    SankeyLink,
    Scale,
    ScaleType,
    SortDirection,
    SortField,
    aggregate_by_category,
    axis_ratio,
    color_at,
    layout_sankey,
    normalise_sankey_links,
    palette_colors,
    palette_names,
    parse_chart_payload,
    radar_axes,
    radar_coordinate,
    scale_is_log,
    sort_points,
    sparkline_area_path,
    sparkline_path,
    text_color_for,
)
from ctf_team_dashboard.features.data_visualization.service import (
    VisualizationService,
    available_chart_types,
)
from ctf_team_dashboard.features.data_visualization.store import (
    ChartDataRepository,
    ChartSpecRepository,
    VisualizationStore,
)


def _chart(**overrides: object) -> ChartSpec:
    """Build a chart specification with deterministic defaults."""
    now = utcnow()
    values: dict[str, object] = {
        "id": "chart-test-0001",
        "team_id": "team-0001",
        "title": "Solves by category",
        "chart_type": ChartType.BAR,
        "series_json": (
            '[{"name":"Solves","points":['
            '{"label":"Mon","value":3,"category":"web"},'
            '{"label":"Tue","value":7,"category":"crypto"}]}]'
        ),
        "options_json": "{}",
        "palette": "aurora",
        "created_at": now,
        "updated_at": now,
    }
    values.update(overrides)
    return ChartSpec(
        id=str(values["id"]),
        team_id=str(values["team_id"]),
        title=str(values["title"]),
        chart_type=values["chart_type"]
        if isinstance(values["chart_type"], ChartType)
        else ChartType.BAR,
        series_json=str(values["series_json"]),
        options_json=str(values["options_json"]),
        palette=str(values["palette"]),
        created_at=values["created_at"] if isinstance(values["created_at"], type(now)) else now,
        updated_at=values["updated_at"] if isinstance(values["updated_at"], type(now)) else now,
    )


def _points() -> tuple[DataPoint, ...]:
    """Return a small labelled point set used by several tests."""
    return (
        DataPoint("Mon", 3, "web"),
        DataPoint("Tue", 7, "crypto"),
        DataPoint("Wed", 5, "web"),
    )


# ----------------------------------------------------------------------
# Pure domain helpers
# ----------------------------------------------------------------------
def test_palette_registry_and_theme_colours() -> None:
    """Palettes expose stable identifiers and distinct theme variants."""
    names = palette_names()
    assert "aurora" in names
    assert len(names) == len(set(names))
    assert palette_colors("aurora") == PALETTES["aurora"].colors
    assert palette_colors("aurora", "dark") == PALETTES["aurora"].dark_colors
    assert color_at(0, ("a", "b")) == "a"
    assert color_at(3, ("a", "b")) == "b"
    assert text_color_for("#ffffff") == "#0f172a"
    assert text_color_for("#101010") == "#ffffff"
    with pytest.raises(ValueError):
        palette_colors("unknown")


def test_chart_options_parse_dump_and_validation() -> None:
    """Options accept overrides and reject out of range values."""
    options = ChartOptions.parse(
        json.dumps(
            {
                "scale": "log",
                "tick_count": 6,
                "sort": "value",
                "direction": "desc",
                "limit": 4,
                "theme": "dark",
                "width": 800,
                "radar_max": 12,
            }
        )
    )
    assert options.scale is ScaleType.LOG
    assert options.tick_count == 6
    assert options.limit == 4
    assert options.theme.value == "dark"
    assert ChartOptions.parse(options.dump()) == options
    merged = options.merged({"tick_count": 4, "theme": "light", "limit": None})
    assert merged.tick_count == 4
    assert merged.theme.value == "light"
    assert merged.limit == 4
    with pytest.raises(ValueError):
        ChartOptions.parse('{"scale":"nope"}')
    with pytest.raises(ValueError):
        ChartOptions.parse('{"tick_count":99}')
    with pytest.raises(ValueError):
        ChartOptions.parse('{"width":10}')
    with pytest.raises(ValueError):
        ChartOptions.parse('{"radar_max":-1}')


def test_linear_scale_projection_and_ticks() -> None:
    """Linear scales produce rounded domains and positioned ticks."""
    scale = Scale.from_values([1.0, 9.0], tick_count=5)
    assert scale.domain_min == 0.0
    assert scale.domain_max == 10.0
    assert scale.normalize(5.0) == pytest.approx(0.5)
    assert scale.project(10.0, 20.0, 120.0) == pytest.approx(120.0)
    ticks = scale.ticks()
    assert [tick.value for tick in ticks] == [0.0, 5.0, 10.0]
    assert ticks[0].label == "0"
    assert ticks[-1].position == pytest.approx(1.0)
    flat = Scale.from_values([5.0, 5.0])
    assert flat.span > 0
    assert not scale_is_log(flat.scale_type)


def test_log_scale_handles_zero_and_negative_values() -> None:
    """Log scales clamp non-positive values to the lower decade."""
    scale = Scale.from_values([0.0, -3.0, 2.0, 200.0], scale_type=ScaleType.LOG)
    assert scale.domain_min == pytest.approx(1.0)
    assert scale.domain_max == pytest.approx(1000.0)
    assert scale.normalize(0.0) == 0.0
    assert scale.normalize(100.0) == pytest.approx(2 / 3)
    assert [tick.label for tick in scale.ticks()]
    assert scale_is_log("log")


def test_sparkline_path_math_is_pure_and_precise() -> None:
    """Sparkline paths are deterministic strings built only from values."""
    assert sparkline_path([0, 5, 10], width=10, height=10, padding=0) == (
        "M 0.00 10.00 L 5.00 5.00 L 10.00 0.00"
    )
    assert sparkline_path([7, 7], width=20, height=10, padding=0) == ("M 0.00 5.00 L 20.00 5.00")
    assert sparkline_path([]) == ""
    area = sparkline_area_path([0, 10], width=10, height=10, padding=0)
    assert area.startswith("M 0.00 10.00 L 10.00 0.00")
    assert area.endswith("L 0.00 10.00 Z")


def test_sorting_and_limiting_points() -> None:
    """Sorting is stable and limiting keeps the leading observations."""
    points = _points()
    by_value = sort_points(points, SortField.VALUE, SortDirection.DESC)
    assert [point.value for point in by_value] == [7, 5, 3]
    by_category = sort_points(points, SortField.CATEGORY, SortDirection.ASC)
    assert [point.category for point in by_category] == ["crypto", "web", "web"]
    assert [point.label for point in by_category[1:]] == ["Mon", "Wed"]
    assert len(sort_points(points, SortField.LABEL, SortDirection.DESC)[:2]) == 2


def test_aggregate_operations_by_category() -> None:
    """Every reduction handles the categories it is given."""
    points = _points()
    sums = aggregate_by_category(points, AggregateOperation.SUM)
    assert [(row.category, row.value) for row in sums] == [("web", 8.0), ("crypto", 7.0)]
    averages = aggregate_by_category(points, AggregateOperation.AVG)
    assert next(row for row in averages if row.category == "web").value == pytest.approx(4.0)
    assert (
        next(
            row
            for row in aggregate_by_category(points, AggregateOperation.MAX)
            if row.category == "web"
        ).value
        == 5.0
    )
    assert (
        next(
            row
            for row in aggregate_by_category(points, AggregateOperation.MIN)
            if row.category == "web"
        ).value
        == 3.0
    )
    counts = aggregate_by_category(points, AggregateOperation.COUNT)
    assert all(row.value == row.count for row in counts)
    assert counts[0].color.startswith("#")
    filtered = aggregate_by_category(points, AggregateOperation.SUM, category_filter="web", limit=1)
    assert len(filtered) == 1
    assert filtered[0].category == "web"


def test_radar_axes_and_coordinates_are_normalised() -> None:
    """Radar spokes are bounded to the unit circle."""
    axes = radar_axes(_points(), maximum=10)
    assert len(axes) == 3
    assert [axis.label for axis in axes] == ["Mon", "Tue", "Wed"]
    assert [round(axis.ratio, 2) for axis in axes] == [0.3, 0.7, 0.5]
    assert axes[0].angle == pytest.approx(-90.0)
    assert radar_coordinate(0, 4, 1.0)[1] == pytest.approx(-1.0)
    assert axis_ratio(-4, 10) == 0.0
    assert axis_ratio(100, 100) == 1.0
    assert 0 < axis_ratio(10, 100, ScaleType.LOG) < 1


def test_sankey_normalisation_and_layout() -> None:
    """Duplicate flows merge and the layout assigns depths and curves."""
    links = (
        SankeyLink("A", "B", 3),
        SankeyLink("A", "B", 4),
        SankeyLink("B", "C", 2),
        SankeyLink("A", "A", 9),
        SankeyLink("C", "D", -1),
    )
    normalised = normalise_sankey_links(links)
    assert len(normalised) == 2
    assert normalised[0] == SankeyLink("A", "B", 7.0)
    layout = layout_sankey(normalised, width=400, height=200, padding=20)
    assert [node.depth for node in layout.nodes] == [0, 1, 2]
    assert all(flow.path.startswith("M ") and " C " in flow.path for flow in layout.flows)
    assert layout.max_value == pytest.approx(7.0)
    assert layout_sankey((), width=400, height=200).nodes == ()


def test_chart_payload_parsing_and_errors() -> None:
    """Inline series and Sankey links parse from compact JSON."""
    payload = parse_chart_payload('[{"label":"x","value":2}]')
    assert payload.points[0].label == "x"
    assert payload.points[0].series == "Series"
    sankey = parse_chart_payload('{"series":[],"links":[{"source":"a","target":"b","value":3}]}')
    assert sankey.links[0].source == "a"
    assert parse_chart_payload("").is_empty
    with pytest.raises(ValueError):
        parse_chart_payload("{not json")
    with pytest.raises(ValueError):
        parse_chart_payload('{"value":1}')
    with pytest.raises(ValueError):
        parse_chart_payload('[{"label":"x","value":"nope"}]')


# ----------------------------------------------------------------------
# Persistence and service
# ----------------------------------------------------------------------
def test_store_roundtrip_and_point_replacement(database: Database) -> None:
    """Both feature tables persist and update chart data atomically."""
    store = VisualizationStore(database)
    chart = _chart()
    store.charts.insert(chart)
    assert store.charts.has_id(chart.id)
    assert store.charts.get(chart.id) == chart
    assert len(store.charts.list_all(team_id="team-0001")) == 1
    points = _points()
    assert store.data.replace_points(chart.id, points) == 3
    assert store.data.count_for_chart(chart.id) == 3
    assert store.data.list_for_chart(chart.id) == points
    assert store.data.append_points(chart.id, (DataPoint("Thu", 4, "pwn"),)) == 1
    assert store.data.list_for_chart(chart.id)[-1].label == "Thu"
    store.data.replace_points(chart.id, (DataPoint("Only", 1, "misc"),))
    assert len(store.data.list_for_chart(chart.id)) == 1
    assert ChartSpecRepository(database).count() == 1
    assert ChartDataRepository(database).count() == 1


def test_service_create_ingest_update_and_list(database: Database) -> None:
    """The service orchestrates persistence across the two tables."""
    service = VisualizationService(VisualizationStore(database))
    created = service.create_chart(
        title="Points over time",
        chart_type=ChartType.LINE,
        series_json='[{"label":"a","value":1}]',
        palette="ocean",
    )
    assert created.title == "Points over time"
    assert created.palette == "ocean"
    assert json.loads(created.series_json)["series"][0]["name"] == "Series"
    with pytest.raises(ConflictError):
        service.create_chart(chart_id=created.id, title="Duplicate", chart_type="line")
    stored = service.ingest_data(created.id, _points())
    assert len(stored) == 3
    assert service.list_data(created.id) == stored
    updated = service.update_chart(created.id, title="Renamed", options_json='{"scale":"log"}')
    assert updated.title == "Renamed"
    assert updated.options.scale is ScaleType.LOG
    assert updated.updated_at >= created.updated_at
    assert [chart.id for chart in service.list_charts(team_id="default")] == [created.id]
    assert [chart.id for chart in service.list_charts(chart_type="line")] == [created.id]


def test_service_validation_and_missing_resources(database: Database) -> None:
    """Invalid input and unknown identifiers raise typed errors."""
    service = VisualizationService(VisualizationStore(database))
    with pytest.raises(ValidationError):
        service.create_chart(title="  ", chart_type="bar")
    with pytest.raises(ValidationError):
        service.create_chart(title="Bad", chart_type="bar", palette="missing")
    with pytest.raises(ValidationError):
        service.create_chart(title="Bad", chart_type="bar", options_json='{"tick_count":1}')
    with pytest.raises(ValidationError):
        service.create_chart(title="Bad", chart_type="bar", series_json="nope")
    with pytest.raises(NotFoundError):
        service.get_chart("missing")
    with pytest.raises(ValidationError):
        service.list_charts(limit=0)
    chart = service.create_chart(title="Valid", chart_type="bar")
    with pytest.raises(ValidationError):
        service.ingest_data(chart.id, (DataPoint("x", math.inf),))
    with pytest.raises(ValidationError):
        service.geometry(chart.id, {"scale": "broken"})
    with pytest.raises(ValidationError):
        service.aggregate(chart.id, operation="median")
    with pytest.raises(NotFoundError):
        service.palette("missing")


@pytest.mark.parametrize(
    "chart_type",
    [ChartType.BAR, ChartType.LINE, ChartType.RADAR, ChartType.SANKEY, ChartType.SPARKLINE],
)
def test_service_geometry_for_every_chart_type(database: Database, chart_type: ChartType) -> None:
    """Each renderer receives valid projected geometry."""
    service = VisualizationService(VisualizationStore(database))
    series_json = (
        '{"series":[{"name":"Solves","points":['
        '{"label":"web","value":3,"category":"web"},'
        '{"label":"crypto","value":7,"category":"crypto"}]}],'
        '"links":[{"source":"start","target":"web","value":3},'
        '{"source":"web","target":"finish","value":3}]}'
    )
    chart = service.create_chart(
        title=f"{chart_type.value} chart",
        chart_type=chart_type,
        series_json=series_json,
        options_json='{"theme":"dark"}',
    )
    geometry = service.geometry(chart.id)
    assert geometry.chart_type is chart_type
    assert geometry.theme.value == "dark"
    assert len(geometry.data) == 2
    assert geometry.ticks
    assert geometry.mark_count >= 0
    if chart_type is ChartType.BAR:
        assert len(geometry.bars) == 2
    if chart_type is ChartType.LINE:
        assert geometry.lines[0].path.startswith("M ")
    if chart_type is ChartType.RADAR:
        assert len(geometry.radar_axes) == 2
        assert len(geometry.radar_shapes) == 1
    if chart_type is ChartType.SANKEY:
        assert len(geometry.sankey_flows) == 2
    if chart_type is ChartType.SPARKLINE:
        assert geometry.sparkline_path.startswith("M ")


def test_service_aggregate_uses_ingested_data(database: Database) -> None:
    """Ingested observations override inline data for reductions."""
    service = VisualizationService(VisualizationStore(database))
    chart = service.create_chart(
        title="Aggregate",
        chart_type="bar",
        series_json='[{"label":"inline","value":100,"category":"web"}]',
    )
    service.ingest_data(chart.id, _points())
    result = service.aggregate(chart.id, operation=AggregateOperation.SUM)
    assert result.categories == 2
    assert result.total == pytest.approx(15.0)
    assert result.rows[0].category == "web"
    assert service.aggregate(chart.id, category="crypto").categories == 1


def test_service_palette_catalogue(database: Database) -> None:
    """Every registered palette is exposed with its colour variants."""
    service = VisualizationService(VisualizationStore(database))
    assert len(service.palettes()) == len(PALETTES)
    assert service.palette("aurora").dark_colors
    assert set(available_chart_types()) == {member.value for member in ChartType}


# ----------------------------------------------------------------------
# HTTP API
# ----------------------------------------------------------------------
def test_api_crud_and_palette_catalogue(client: TestClient, seeded: object) -> None:
    """Create, list, read, update and palette discovery work over HTTP."""
    assert seeded is not None
    palettes = client.get("/api/visualizations/palettes")
    assert palettes.status_code == 200
    assert any(palette["id"] == "aurora" for palette in palettes.json())

    response = client.post(
        "/api/visualizations",
        json={
            "id": "chart-api-0001",
            "title": "API chart",
            "chart_type": "bar",
            "series_json": '[{"label":"a","value":1,"category":"web"}]',
            "options_json": '{"theme":"dark"}',
        },
    )
    assert response.status_code == 201
    assert response.json()["id"] == "chart-api-0001"
    assert client.get("/api/visualizations").json()[0]["id"] == "chart-api-0001"
    assert client.get("/api/visualizations/chart-api-0001").json()["title"] == "API chart"
    updated = client.put(
        "/api/visualizations/chart-api-0001",
        json={"title": "Updated API chart", "palette": "ember"},
    )
    assert updated.status_code == 200
    assert updated.json()["palette"] == "ember"
    filtered = client.get("/api/visualizations?chart_type=line")
    assert filtered.json() == []


def test_api_data_geometry_and_aggregate(client: TestClient) -> None:
    """Ingestion and read-only analysis endpoints return typed payloads."""
    created = client.post(
        "/api/visualizations",
        json={
            "title": "Geometry chart",
            "chart_type": "line",
            "series_json": "[]",
            "options_json": "{}",
        },
    ).json()
    chart_id = created["id"]
    ingest = client.post(
        f"/api/visualizations/{chart_id}/data",
        json={
            "points": [
                {"label": "Mon", "value": 3, "category": "web"},
                {"label": "Tue", "value": 9, "category": "crypto"},
            ]
        },
    )
    assert ingest.status_code == 201
    assert len(ingest.json()) == 2
    assert len(client.get(f"/api/visualizations/{chart_id}/data").json()) == 2
    geometry = client.get(
        f"/api/visualizations/{chart_id}/geometry",
        params={"scale": "linear", "sort": "value", "direction": "desc", "tick_count": 4},
    )
    assert geometry.status_code == 200
    body = geometry.json()
    assert body["chart_id"] == chart_id
    assert body["has_data"] is True
    assert body["lines"][0]["path"].startswith("M ")
    assert len(body["ticks"]) >= 2
    aggregate = client.get(
        f"/api/visualizations/{chart_id}/aggregate",
        params={"operation": "sum", "sort": "value", "direction": "desc"},
    )
    assert aggregate.status_code == 200
    assert aggregate.json()["rows"][0]["category"] == "crypto"
    assert aggregate.json()["total"] == pytest.approx(12.0)


def test_api_error_paths_and_registration(client: TestClient, database: Database) -> None:
    """Domain failures map to stable status codes and schemas exist."""
    assert {"v3_charts", "v3_chart_data"}.issubset(database.table_names())
    assert client.get("/api/visualizations/missing").status_code == 404
    duplicate = client.post(
        "/api/visualizations",
        json={"id": "dup", "title": "First", "chart_type": "bar"},
    )
    assert duplicate.status_code == 201
    conflict = client.post(
        "/api/visualizations",
        json={"id": "dup", "title": "Second", "chart_type": "bar"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "conflict"
    assert client.get("/api/visualizations/dup/aggregate", params={"limit": 0}).status_code == 422
    assert client.get("/api/visualizations/palettes").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/visualizations/{chart_id}/geometry" in paths
