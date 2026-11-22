"""Domain model and pure geometry for advanced data visualisations.

Every calculation in this module is deterministic and side effect free. The
HTTP and service layers only validate inputs, persist entities and hand values
to these helpers, which keeps chart maths easy to test and reuse.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any

from ctf_team_dashboard.domain.enums import StrEnum
from ctf_team_dashboard.domain.models import utcnow

DEFAULT_PALETTE = "aurora"
DEFAULT_TEAM_ID = "default"
DEFAULT_SERIES_NAME = "Series"
MAX_TITLE_LENGTH = 160
MAX_LABEL_LENGTH = 120
MAX_POINTS = 500
MAX_SERIES = 12
MIN_LOG_VALUE = 1e-9
MIN_TICKS = 2
MAX_TICKS = 12


class ChartType(StrEnum):
    """Chart renderers supported by the visualisation gallery."""

    BAR = "bar"
    LINE = "line"
    RADAR = "radar"
    SANKEY = "sankey"
    SPARKLINE = "sparkline"


class ScaleType(StrEnum):
    """Numeric projection used by an axis."""

    LINEAR = "linear"
    LOG = "log"


class AggregateOperation(StrEnum):
    """Reduction applied when grouping points by category."""

    SUM = "sum"
    AVG = "avg"
    MAX = "max"
    MIN = "min"
    COUNT = "count"


class SortField(StrEnum):
    """Field used to order points before rendering."""

    LABEL = "label"
    VALUE = "value"
    CATEGORY = "category"


class SortDirection(StrEnum):
    """Direction applied to point ordering and aggregates."""

    ASC = "asc"
    DESC = "desc"


class ChartTheme(StrEnum):
    """Palette variant selected from the active interface theme."""

    LIGHT = "light"
    DARK = "dark"


@dataclass(frozen=True, slots=True)
class Palette:
    """A named set of accessible categorical colours."""

    id: str
    name: str
    description: str
    colors: tuple[str, ...]
    dark_colors: tuple[str, ...]

    @property
    def size(self) -> int:
        """Return the number of colours in the palette."""
        return len(self.colors)

    def colors_for(self, theme: ChartTheme | str) -> tuple[str, ...]:
        """Return the colour sequence matching a theme."""
        resolved = ChartTheme.parse(str(theme), ChartTheme.LIGHT)
        return self.dark_colors if resolved is ChartTheme.DARK else self.colors


PALETTES: dict[str, Palette] = {
    palette.id: palette
    for palette in (
        Palette(
            id="aurora",
            name="Aurora",
            description="Cool indigo and teal tones for everyday dashboards.",
            colors=("#4f46e5", "#0891b2", "#059669", "#d97706", "#db2777", "#7c3aed"),
            dark_colors=("#818cf8", "#22d3ee", "#34d399", "#fbbf24", "#fb7185", "#a78bfa"),
        ),
        Palette(
            id="ember",
            name="Ember",
            description="Warm reds and oranges suited to alert oriented views.",
            colors=("#dc2626", "#ea580c", "#d97706", "#ca8a04", "#be123c", "#9d174d"),
            dark_colors=("#fb7185", "#fb923c", "#fbbf24", "#facc15", "#f43f5e", "#f472b6"),
        ),
        Palette(
            id="ocean",
            name="Ocean",
            description="Blue and cyan shades for dense time series.",
            colors=("#1d4ed8", "#0284c7", "#0891b2", "#0d9488", "#4338ca", "#2563eb"),
            dark_colors=("#60a5fa", "#38bdf8", "#22d3ee", "#2dd4bf", "#818cf8", "#93c5fd"),
        ),
        Palette(
            id="meadow",
            name="Meadow",
            description="Green and gold tones for progress reporting.",
            colors=("#15803d", "#4d7c0f", "#a16207", "#047857", "#65a30d", "#0f766e"),
            dark_colors=("#4ade80", "#a3e635", "#fbbf24", "#34d399", "#bef264", "#5eead4"),
        ),
        Palette(
            id="mono",
            name="Monochrome",
            description="Neutral greys for print and high density tables.",
            colors=("#1e293b", "#475569", "#64748b", "#94a3b8", "#334155", "#0f172a"),
            dark_colors=("#e2e8f0", "#cbd5e1", "#94a3b8", "#64748b", "#f1f5f9", "#ffffff"),
        ),
    )
}
PALETTE_ORDER: tuple[str, ...] = tuple(PALETTES)


def palette_descriptor(name: str) -> Palette:
    """Return a palette by identifier or raise ``ValueError``."""
    palette = PALETTES.get(name.strip().lower())
    if palette is None:
        raise ValueError(f"unknown palette {name!r}")
    return palette


def palette_names() -> tuple[str, ...]:
    """Return the identifiers of every registered palette."""
    return PALETTE_ORDER


def palette_colors(name: str, theme: ChartTheme | str = ChartTheme.LIGHT) -> tuple[str, ...]:
    """Return theme aware colours for a palette identifier."""
    return palette_descriptor(name).colors_for(theme)


def color_at(index: int, colors: Sequence[str]) -> str:
    """Return a colour from a sequence, cycling when the index overflows."""
    if not colors:
        return "#6366f1"
    return colors[index % len(colors)]


def relative_luminance(color: str) -> float:
    """Compute WCAG relative luminance for a ``#rrggbb`` colour."""
    value = color.lstrip("#")
    if len(value) != 6:
        return 0.0
    channels = [int(value[index : index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def text_color_for(color: str) -> str:
    """Return a readable foreground colour for a categorical fill."""
    return "#0f172a" if relative_luminance(color) > 0.45 else "#ffffff"


def with_alpha(color: str, alpha: float) -> str:
    """Return an ``rgba`` string for a hex colour and opacity."""
    value = color.lstrip("#")
    if len(value) != 6:
        return f"rgba(99, 102, 241, {alpha:.2f})"
    red = int(value[0:2], 16)
    green = int(value[2:4], 16)
    blue = int(value[4:6], 16)
    return f"rgba({red}, {green}, {blue}, {max(0.0, min(1.0, alpha)):.2f})"


@dataclass(frozen=True, slots=True)
class DataPoint:
    """One labelled observation attached to a chart."""

    label: str
    value: float
    category: str = DEFAULT_TEAM_ID
    series: str = ""

    @property
    def magnitude(self) -> float:
        """Return the absolute value used for size comparisons."""
        return abs(self.value)

    @property
    def tooltip(self) -> str:
        """Return the compact label used by chart tooltips."""
        return f"{self.label} · {format_number(self.value)}"

    def with_series(self, name: str) -> DataPoint:
        """Return a copy carrying a series name."""
        return replace(self, series=name)


@dataclass(frozen=True, slots=True)
class DataSeries:
    """A named collection of observations rendered as one mark group."""

    name: str
    points: tuple[DataPoint, ...] = ()

    @classmethod
    def of(cls, name: str, points: Iterable[DataPoint]) -> DataSeries:
        """Build a series from any iterable of points."""
        return cls(name=name, points=tuple(points))

    @property
    def size(self) -> int:
        """Return the number of points in the series."""
        return len(self.points)

    @property
    def values(self) -> tuple[float, ...]:
        """Return the raw values of the series."""
        return tuple(point.value for point in self.points)

    @property
    def categories(self) -> tuple[str, ...]:
        """Return the distinct categories in first appearance order."""
        seen: dict[str, None] = {}
        for point in self.points:
            seen[point.category] = None
        return tuple(seen)

    @property
    def extent(self) -> tuple[float, float]:
        """Return the minimum and maximum value, or zero when empty."""
        if not self.points:
            return 0.0, 0.0
        return min(self.values), max(self.values)


@dataclass(frozen=True, slots=True)
class SankeyLink:
    """A directed flow between two Sankey nodes."""

    source: str
    target: str
    value: float
    color: str = ""
    width: float = 0.0
    path: str = ""
    source_offset: float = 0.0
    target_offset: float = 0.0


@dataclass(frozen=True, slots=True)
class ChartPayload:
    """Parsed chart input, including optional Sankey flows."""

    series: tuple[DataSeries, ...] = ()
    links: tuple[SankeyLink, ...] = ()

    @property
    def points(self) -> tuple[DataPoint, ...]:
        """Return every point with its owning series name attached."""
        return tuple(
            point.with_series(series.name) for series in self.series for point in series.points
        )

    @property
    def labels(self) -> tuple[str, ...]:
        """Return distinct point labels in first appearance order."""
        seen: dict[str, None] = {}
        for point in self.points:
            seen[point.label] = None
        return tuple(seen)

    @property
    def is_empty(self) -> bool:
        """Return whether the payload holds no points and no links."""
        return not self.points and not self.links


def _clean_label(raw: Any, fallback: str) -> str:
    """Convert a JSON label to a bounded non-empty string."""
    text = str(raw).strip() if raw is not None else ""
    return (text or fallback)[:MAX_LABEL_LENGTH]


def _clean_value(raw: Any) -> float:
    """Convert a JSON number to a finite float."""
    try:
        value = float(raw)
    except (TypeError, ValueError) as error:
        raise ValueError("point value must be numeric") from error
    if not math.isfinite(value):
        raise ValueError("point value must be finite")
    return value


def _parse_point(raw: Any, series_name: str, index: int) -> DataPoint:
    """Parse one point object from a chart payload."""
    if not isinstance(raw, Mapping):
        raise ValueError("each point must be an object")
    label = _clean_label(raw.get("label", raw.get("name")), f"Point {index + 1}")
    category = _clean_label(raw.get("category"), DEFAULT_TEAM_ID)
    return DataPoint(
        label=label,
        value=_clean_value(raw.get("value", 0)),
        category=category,
        series=series_name,
    )


def _parse_series(raw: Any, index: int) -> DataSeries:
    """Parse one series object, or a bare list of points."""
    if isinstance(raw, Mapping):
        name = _clean_label(raw.get("name", raw.get("label")), f"Series {index + 1}")
        points_raw = raw.get("points", [])
    else:
        name = DEFAULT_SERIES_NAME
        points_raw = raw
    if not isinstance(points_raw, list):
        raise ValueError("series points must be a list")
    points = tuple(
        _parse_point(point, name, point_index) for point_index, point in enumerate(points_raw)
    )
    return DataSeries(name=name, points=points)


def _parse_links(raw: Any) -> tuple[SankeyLink, ...]:
    """Parse the directed flows of a Sankey payload."""
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError("sankey links must be a list")
    links: list[SankeyLink] = []
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ValueError("each sankey link must be an object")
        source = _clean_label(item.get("source", item.get("from")), "")
        target = _clean_label(item.get("target", item.get("to")), "")
        if not source or not target:
            raise ValueError(f"sankey link {index + 1} needs a source and a target")
        links.append(
            SankeyLink(source=source, target=target, value=_clean_value(item.get("value", 0)))
        )
    return normalise_sankey_links(links)


def parse_chart_payload(raw: str | None) -> ChartPayload:
    """Parse a ``series_json`` value into domain objects."""
    if not raw or not raw.strip():
        return ChartPayload()
    try:
        decoded: Any = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"series_json is not valid JSON: {error.msg}") from error
    if isinstance(decoded, list):
        looks_like_series = any(isinstance(item, Mapping) and "points" in item for item in decoded)
        series = (
            tuple(_parse_series(item, index) for index, item in enumerate(decoded))
            if looks_like_series
            else (_parse_series(decoded, 0),)
        )
        return ChartPayload(series=series)
    if isinstance(decoded, Mapping):
        if "series" not in decoded and "links" not in decoded:
            raise ValueError("series_json object must declare series or links")
        series_raw = decoded.get("series", [])
        if not isinstance(series_raw, list):
            raise ValueError("series must be a list")
        series = tuple(_parse_series(item, index) for index, item in enumerate(series_raw))
        return ChartPayload(series=series, links=_parse_links(decoded.get("links")))
    raise ValueError("series_json must encode an object or a list")


def dump_chart_payload(payload: ChartPayload) -> str:
    """Serialise a chart payload to compact JSON."""
    encoded: dict[str, Any] = {
        "series": [
            {
                "name": series.name,
                "points": [
                    {"label": point.label, "value": point.value, "category": point.category}
                    for point in series.points
                ],
            }
            for series in payload.series
        ],
        "links": [
            {"source": link.source, "target": link.target, "value": link.value}
            for link in payload.links
        ],
    }
    return json.dumps(encoded, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class ChartOptions:
    """Rendering, scaling and ordering options for a chart."""

    scale: ScaleType = ScaleType.LINEAR
    tick_count: int = 5
    width: float = 640.0
    height: float = 320.0
    padding: float = 28.0
    sort: SortField = SortField.LABEL
    direction: SortDirection = SortDirection.ASC
    limit: int | None = None
    operation: AggregateOperation = AggregateOperation.SUM
    show_legend: bool = True
    theme: ChartTheme = ChartTheme.LIGHT
    radar_max: float | None = None
    smooth: bool = False

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> ChartOptions:
        """Build validated options from a decoded JSON object."""
        try:
            scale = ScaleType.parse(str(data.get("scale", "linear")))
            sort = SortField.parse(str(data.get("sort", "label")))
            direction = SortDirection.parse(str(data.get("direction", "asc")))
            operation = AggregateOperation.parse(str(data.get("operation", "sum")))
            theme = ChartTheme.parse(str(data.get("theme", "light")))
            tick_count = int(data.get("tick_count", 5))
            width = float(data.get("width", 640))
            height = float(data.get("height", 320))
            padding = float(data.get("padding", 28))
            radar_max_raw = data.get("radar_max")
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid chart option: {error}") from error

        if not MIN_TICKS <= tick_count <= MAX_TICKS:
            raise ValueError(f"tick_count must be between {MIN_TICKS} and {MAX_TICKS}")
        if not 120 <= width <= 2000 or not 80 <= height <= 1200:
            raise ValueError("width and height are outside the supported range")
        if not 0 <= padding <= min(width, height) / 2:
            raise ValueError("padding is outside the supported range")

        limit_raw = data.get("limit")
        limit = None
        if limit_raw is not None and limit_raw != "":
            try:
                limit = int(limit_raw)
            except (TypeError, ValueError) as error:
                raise ValueError("limit must be an integer") from error
            if not 1 <= limit <= MAX_POINTS:
                raise ValueError(f"limit must be between 1 and {MAX_POINTS}")

        radar_max: float | None = None
        if radar_max_raw is not None and radar_max_raw != "":
            try:
                radar_max = float(radar_max_raw)
            except (TypeError, ValueError) as error:
                raise ValueError("radar_max must be numeric") from error
            if not math.isfinite(radar_max) or radar_max <= 0:
                raise ValueError("radar_max must be a positive finite number")

        return cls(
            scale=scale,
            tick_count=tick_count,
            width=width,
            height=height,
            padding=padding,
            sort=sort,
            direction=direction,
            limit=limit,
            operation=operation,
            show_legend=bool(data.get("show_legend", True)),
            theme=theme,
            radar_max=radar_max,
            smooth=bool(data.get("smooth", False)),
        )

    @classmethod
    def parse(cls, raw: str | Mapping[str, Any] | None) -> ChartOptions:
        """Parse an ``options_json`` value or a decoded mapping."""
        if raw is None or raw == "":
            return cls()
        if isinstance(raw, str):
            try:
                decoded: Any = json.loads(raw)
            except json.JSONDecodeError as error:
                raise ValueError(f"options_json is not valid JSON: {error.msg}") from error
        else:
            decoded = raw
        if not isinstance(decoded, Mapping):
            raise ValueError("options_json must encode an object")
        return cls.from_mapping(decoded)

    def dump(self) -> str:
        """Serialise options to compact JSON."""
        encoded: dict[str, Any] = {
            "scale": self.scale.value,
            "tick_count": self.tick_count,
            "width": self.width,
            "height": self.height,
            "padding": self.padding,
            "sort": self.sort.value,
            "direction": self.direction.value,
            "operation": self.operation.value,
            "show_legend": self.show_legend,
            "theme": self.theme.value,
            "smooth": self.smooth,
        }
        if self.limit is not None:
            encoded["limit"] = self.limit
        if self.radar_max is not None:
            encoded["radar_max"] = self.radar_max
        return json.dumps(encoded, separators=(",", ":"))

    def merged(self, changes: Mapping[str, Any]) -> ChartOptions:
        """Return options with selected fields overridden by a request."""
        current: dict[str, Any] = json.loads(self.dump())
        for key, value in changes.items():
            if value is not None:
                current[key] = value
        return ChartOptions.from_mapping(current)


@dataclass(frozen=True, slots=True)
class ChartSpec:
    """Persisted definition of a chart and its rendering configuration."""

    id: str
    team_id: str
    title: str
    chart_type: ChartType
    series_json: str
    options_json: str
    palette: str = DEFAULT_PALETTE
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    @property
    def payload(self) -> ChartPayload:
        """Return the parsed chart payload."""
        return parse_chart_payload(self.series_json)

    @property
    def options(self) -> ChartOptions:
        """Return the parsed chart options."""
        return ChartOptions.parse(self.options_json)

    @property
    def is_empty(self) -> bool:
        """Return whether the inline payload declares no data."""
        return self.payload.is_empty

    @property
    def supports_links(self) -> bool:
        """Return whether this chart type renders directed flows."""
        return self.chart_type is ChartType.SANKEY


def format_number(value: float) -> str:
    """Format a numeric axis label in a compact, stable form."""
    if not math.isfinite(value):
        return "—"
    magnitude = abs(value)
    if magnitude >= 1_000_000:
        return f"{value / 1_000_000:.1f}M".replace(".0M", "M")
    if magnitude >= 1_000:
        return f"{value / 1_000:.1f}k".replace(".0k", "k")
    if magnitude == 0:
        return "0"
    if magnitude < 0.01:
        return f"{value:.2e}"
    rounded = round(value, 2)
    return f"{rounded:g}"


def nice_step(raw: float) -> float:
    """Round an axis step to a 1, 2, 5 or 10 multiple."""
    if not math.isfinite(raw) or raw <= 0:
        return 1.0
    exponent = math.floor(math.log10(raw))
    base = 10.0**exponent
    fraction = raw / base
    candidates = (1.0, 2.0, 5.0, 10.0)
    chosen = next((candidate for candidate in candidates if candidate >= fraction), 10.0)
    return chosen * base


@dataclass(frozen=True, slots=True)
class Tick:
    """One axis tick with its numeric value, label and normal position."""

    value: float
    label: str
    position: float


@dataclass(frozen=True, slots=True)
class Scale:
    """A linear or logarithmic projection of data values onto an axis."""

    domain_min: float
    domain_max: float
    scale_type: ScaleType = ScaleType.LINEAR
    tick_count: int = 5

    @classmethod
    def from_values(
        cls,
        values: Iterable[float],
        *,
        scale_type: ScaleType = ScaleType.LINEAR,
        tick_count: int = 5,
    ) -> Scale:
        """Derive a padded, rounded domain from a set of observations."""
        finite = [value for value in values if math.isfinite(value)]
        ticks = max(MIN_TICKS, min(MAX_TICKS, tick_count))
        if scale_type is ScaleType.LOG:
            positives = [max(value, MIN_LOG_VALUE) for value in finite if value > 0]
            if not positives:
                low, high = 1.0, 10.0
            else:
                low = max(min(positives), MIN_LOG_VALUE)
                high = max(positives)
                if high <= low:
                    low = max(low / 10, MIN_LOG_VALUE)
                    high = high * 10
                low = 10.0 ** math.floor(math.log10(low))
                high = 10.0 ** math.ceil(math.log10(high))
                if high <= low:
                    high = low * 10
            return cls(low, high, scale_type, ticks)

        if not finite:
            return cls(0.0, 1.0, scale_type, ticks)
        low, high = min(finite), max(finite)
        if math.isclose(low, high):
            spread = max(abs(low) * 0.1, 1.0)
            low -= spread
            high += spread
        step = nice_step((high - low) / max(1, ticks - 1))
        low = math.floor(low / step) * step
        high = math.ceil(high / step) * step
        if high <= low:
            high = low + step
        return cls(low, high, scale_type, ticks)

    @property
    def span(self) -> float:
        """Return the width of the domain."""
        return self.domain_max - self.domain_min

    def normalize(self, value: float) -> float:
        """Project a data value onto the interval ``[0, 1]``."""
        if scale_is_log(self.scale_type):
            low = math.log10(max(self.domain_min, MIN_LOG_VALUE))
            high = math.log10(max(self.domain_max, low * 10))
            current = math.log10(max(value, self.domain_min, MIN_LOG_VALUE))
            ratio = (current - low) / (high - low) if high > low else 0.0
        else:
            ratio = (value - self.domain_min) / self.span if self.span > 0 else 0.0
        return max(0.0, min(1.0, ratio))

    def project(self, value: float, start: float, end: float) -> float:
        """Project a data value onto the screen interval ``[start, end]``."""
        return start + self.normalize(value) * (end - start)

    def ticks(self) -> tuple[Tick, ...]:
        """Return evenly spaced, human readable ticks for the domain."""
        if scale_is_log(self.scale_type):
            return self._log_ticks()
        step = nice_step(self.span / max(1, self.tick_count - 1))
        values: list[float] = []
        current = math.ceil(self.domain_min / step) * step
        for _ in range(MAX_TICKS * 4):
            if current > self.domain_max + step * 1e-6:
                break
            values.append(round(current, 6))
            current += step
        if not values:
            values = [self.domain_min, self.domain_max]
        return self._ticks_from_values(values)

    def _log_ticks(self) -> tuple[Tick, ...]:
        """Return decade ticks, thinned when the domain is very wide."""
        low = math.log10(max(self.domain_min, MIN_LOG_VALUE))
        high = math.log10(max(self.domain_max, self.domain_min * 10))
        candidates: list[float] = []
        for decade in range(math.floor(low), math.ceil(high) + 1):
            for multiplier in (1.0, 2.0, 5.0):
                value = multiplier * 10.0**decade
                if self.domain_min <= value <= self.domain_max:
                    candidates.append(value)
        if not candidates:
            candidates = [self.domain_min, self.domain_max]
        if len(candidates) > self.tick_count:
            last = len(candidates) - 1
            indices = {
                round(index * last / (self.tick_count - 1)) for index in range(self.tick_count)
            }
            candidates = [candidates[index] for index in sorted(indices)]
        return self._ticks_from_values(candidates)

    def _ticks_from_values(self, values: Sequence[float]) -> tuple[Tick, ...]:
        """Build tick objects from numeric values."""
        return tuple(
            Tick(value=value, label=format_number(value), position=self.normalize(value))
            for value in values
        )


def scale_is_log(scale: ScaleType | str) -> bool:
    """Return whether a scale identifier is logarithmic."""
    return ScaleType.parse(str(scale)) is ScaleType.LOG


def sort_points(
    points: Iterable[DataPoint],
    field_name: SortField | str = SortField.LABEL,
    direction: SortDirection | str = SortDirection.ASC,
) -> tuple[DataPoint, ...]:
    """Sort points by a field with a deterministic secondary key."""
    field_value = SortField.parse(str(field_name))
    descending = SortDirection.parse(str(direction)) is SortDirection.DESC
    values = list(points)

    def key(point: DataPoint) -> tuple[object, ...]:
        if field_value is SortField.VALUE:
            primary: object = -point.value if descending else point.value
        elif field_value is SortField.CATEGORY:
            primary = point.category.lower()
        else:
            primary = point.label.lower()
        secondary = (point.label.lower(), point.category.lower(), point.value)
        return (primary, *secondary)

    if descending and field_value is not SortField.VALUE:
        return tuple(sorted(values, key=key, reverse=True))
    return tuple(sorted(values, key=key))


def limit_points(points: Iterable[DataPoint], limit: int | None) -> tuple[DataPoint, ...]:
    """Return at most ``limit`` points."""
    values = tuple(points)
    if limit is None or limit <= 0 or len(values) <= limit:
        return values
    return values[:limit]


@dataclass(frozen=True, slots=True)
class AggregateRow:
    """The reduction of all points belonging to one category."""

    category: str
    operation: AggregateOperation
    value: float
    count: int
    color: str

    @property
    def display(self) -> str:
        """Return a compact display value."""
        return format_number(self.value)


@dataclass(frozen=True, slots=True)
class AggregateResult:
    """A complete category aggregation with chart context."""

    chart_id: str
    operation: AggregateOperation
    rows: tuple[AggregateRow, ...]
    total: float
    categories: int

    @property
    def is_empty(self) -> bool:
        """Return whether no rows were produced."""
        return not self.rows


def aggregate_by_category(
    points: Iterable[DataPoint],
    operation: AggregateOperation | str,
    *,
    colors: Sequence[str] = (),
    sort: SortField | str = SortField.VALUE,
    direction: SortDirection | str = SortDirection.DESC,
    limit: int | None = None,
    category_filter: str | None = None,
) -> tuple[AggregateRow, ...]:
    """Group points by category and reduce their values."""
    operation_value = AggregateOperation.parse(str(operation))
    grouped: dict[str, list[float]] = defaultdict(list)
    for point in points:
        category = point.category.strip() or DEFAULT_TEAM_ID
        if category_filter and category.lower() != category_filter.strip().lower():
            continue
        if math.isfinite(point.value):
            grouped[category].append(point.value)

    rows: list[AggregateRow] = []
    for index, (category, values) in enumerate(grouped.items()):
        if operation_value is AggregateOperation.SUM:
            value = sum(values)
        elif operation_value is AggregateOperation.AVG:
            value = sum(values) / len(values)
        elif operation_value is AggregateOperation.MAX:
            value = max(values)
        elif operation_value is AggregateOperation.MIN:
            value = min(values)
        else:
            value = float(len(values))
        rows.append(
            AggregateRow(
                category=category,
                operation=operation_value,
                value=value,
                count=len(values),
                color=color_at(index, colors),
            )
        )

    sort_value = SortField.parse(str(sort))
    descending = SortDirection.parse(str(direction)) is SortDirection.DESC

    def row_key(row: AggregateRow) -> tuple[object, ...]:
        primary: object = -row.value if descending else row.value
        return (primary, row.category.lower())

    ordered = (
        tuple(sorted(rows, key=row_key))
        if sort_value is SortField.VALUE
        else tuple(sorted(rows, key=lambda row: row.category.lower(), reverse=descending))
    )
    return limit_points_rows(ordered, limit)


def limit_points_rows(rows: Sequence[AggregateRow], limit: int | None) -> tuple[AggregateRow, ...]:
    """Return at most ``limit`` aggregate rows."""
    if limit is None or limit <= 0 or len(rows) <= limit:
        return tuple(rows)
    return tuple(rows[:limit])


def polyline_path(coordinates: Sequence[tuple[float, float]]) -> str:
    """Build an SVG path string from absolute coordinates."""
    if not coordinates:
        return ""
    segments: list[str] = []
    for index, (x_coord, y_coord) in enumerate(coordinates):
        command = "M" if index == 0 else "L"
        segments.append(f"{command} {x_coord:.2f} {y_coord:.2f}")
    return " ".join(segments)


def sparkline_coordinates(
    values: Iterable[float],
    *,
    width: float = 120.0,
    height: float = 32.0,
    padding: float = 3.0,
) -> tuple[tuple[float, float], ...]:
    """Map values onto a small SVG viewport with pure arithmetic."""
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        return ()
    inner_width = max(0.0, width - padding * 2)
    inner_height = max(0.0, height - padding * 2)
    minimum, maximum = min(finite), max(finite)
    if math.isclose(minimum, maximum):
        coordinates = [
            (padding + index * inner_width / max(1, len(finite) - 1), padding + inner_height / 2)
            for index in range(len(finite))
        ]
        return tuple(coordinates)
    span = maximum - minimum
    return tuple(
        (
            padding + index * inner_width / max(1, len(finite) - 1),
            padding + inner_height - (value - minimum) / span * inner_height,
        )
        for index, value in enumerate(finite)
    )


def sparkline_path(
    values: Iterable[float],
    *,
    width: float = 120.0,
    height: float = 32.0,
    padding: float = 3.0,
) -> str:
    """Build the line path for a sparkline."""
    return polyline_path(sparkline_coordinates(values, width=width, height=height, padding=padding))


def sparkline_area_path(
    values: Iterable[float],
    *,
    width: float = 120.0,
    height: float = 32.0,
    padding: float = 3.0,
) -> str:
    """Build a closed area path for a sparkline."""
    coordinates = sparkline_coordinates(values, width=width, height=height, padding=padding)
    if not coordinates:
        return ""
    baseline = max(0.0, height - padding)
    path = polyline_path(coordinates)
    last_x = coordinates[-1][0]
    first_x = coordinates[0][0]
    return f"{path} L {last_x:.2f} {baseline:.2f} L {first_x:.2f} {baseline:.2f} Z"


def normalise_sankey_links(links: Iterable[SankeyLink]) -> tuple[SankeyLink, ...]:
    """Merge duplicate flows, drop invalid links and order by magnitude."""
    totals: dict[tuple[str, str], float] = defaultdict(float)
    for link in links:
        source = link.source.strip()
        target = link.target.strip()
        if not source or not target or source == target:
            continue
        if not math.isfinite(link.value) or link.value <= 0:
            continue
        totals[(source, target)] += link.value
    normalised = [
        SankeyLink(source=source, target=target, value=value)
        for (source, target), value in totals.items()
    ]
    return tuple(sorted(normalised, key=lambda link: (-link.value, link.source, link.target)))


@dataclass(frozen=True, slots=True)
class SankeyNodeLayout:
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


@dataclass(frozen=True, slots=True)
class SankeyFlowLayout:
    """A positioned Sankey ribbon with its SVG curve."""

    source: str
    target: str
    value: float
    width: float
    path: str
    color: str


@dataclass(frozen=True, slots=True)
class SankeyLayout:
    """The complete result of laying out a Sankey diagram."""

    nodes: tuple[SankeyNodeLayout, ...]
    flows: tuple[SankeyFlowLayout, ...]
    max_value: float


def sankey_depth(links: Sequence[SankeyLink], nodes: Sequence[str]) -> dict[str, int]:
    """Assign a column index to every node using longest-path layering."""
    depths = dict.fromkeys(nodes, 0)
    for _ in range(len(nodes)):
        changed = False
        for link in links:
            candidate = depths[link.source] + 1
            if candidate > depths[link.target] and candidate < len(nodes):
                depths[link.target] = candidate
                changed = True
        if not changed:
            break
    return depths


def layout_sankey(
    links: Iterable[SankeyLink],
    *,
    colors: Sequence[str] = (),
    width: float = 640.0,
    height: float = 320.0,
    padding: float = 28.0,
) -> SankeyLayout:
    """Position Sankey nodes and compute cubic ribbon paths."""
    ordered = normalise_sankey_links(links)
    if not ordered:
        return SankeyLayout((), (), 0.0)
    node_names: list[str] = []
    for link in ordered:
        for name in (link.source, link.target):
            if name not in node_names:
                node_names.append(name)
    depths = sankey_depth(ordered, node_names)
    throughput: dict[str, float] = dict.fromkeys(node_names, 0.0)
    for link in ordered:
        throughput[link.source] = max(throughput[link.source], link.value)
        throughput[link.target] = max(throughput[link.target], link.value)
    max_value = max(throughput.values())
    columns: dict[int, list[str]] = defaultdict(list)
    for name in node_names:
        columns[depths[name]].append(name)
    column_indexes = sorted(columns)
    node_width = 14.0
    gap = 12.0
    available_height = max(10.0, height - padding * 2)
    max_column_size = max(len(column) for column in columns.values())
    total_gap = gap * max(0, max_column_size - 1)
    height_scale = (available_height - total_gap) / max_value if max_value else 0.0
    x_step = (width - padding * 2 - node_width) / max(1, len(column_indexes) - 1)

    positions: dict[str, SankeyNodeLayout] = {}
    for column_index in column_indexes:
        names = sorted(columns[column_index], key=lambda name: node_names.index(name))
        column_height = sum(throughput[name] * height_scale for name in names) + gap * (
            len(names) - 1
        )
        cursor = padding + max(0.0, (available_height - column_height) / 2)
        for name in names:
            node_height = max(4.0, throughput[name] * height_scale)
            positions[name] = SankeyNodeLayout(
                id=name.lower().replace(" ", "-"),
                label=name,
                value=throughput[name],
                depth=depths[name],
                x=padding + column_index * x_step,
                y=cursor,
                width=node_width,
                height=node_height,
                color=color_at(node_names.index(name), colors),
            )
            cursor += node_height + gap

    source_offsets: dict[str, float] = defaultdict(float)
    target_offsets: dict[str, float] = defaultdict(float)
    flows: list[SankeyFlowLayout] = []
    for link in ordered:
        source = positions[link.source]
        target = positions[link.target]
        ribbon = max(1.0, height_scale * link.value)
        start_y = source.y + source_offsets[link.source]
        end_y = target.y + target_offsets[link.target]
        start_x = source.x + source.width
        end_x = target.x
        control = (end_x - start_x) * 0.45
        path = (
            f"M {start_x:.2f} {start_y:.2f} "
            f"C {start_x + control:.2f} {start_y:.2f}, "
            f"{end_x - control:.2f} {end_y:.2f}, {end_x:.2f} {end_y:.2f}"
        )
        flows.append(
            SankeyFlowLayout(
                source=link.source,
                target=link.target,
                value=link.value,
                width=ribbon,
                path=path,
                color=color_at(node_names.index(link.source), colors),
            )
        )
        source_offsets[link.source] += ribbon
        target_offsets[link.target] += ribbon
    return SankeyLayout(tuple(positions.values()), tuple(flows), max_value)


def radar_coordinate(index: int, count: int, ratio: float) -> tuple[float, float]:
    """Return the SVG coordinate of a radar value on a unit circle."""
    angle = -math.pi / 2 + index * 2 * math.pi / max(1, count)
    return (math.cos(angle) * ratio, math.sin(angle) * ratio)


@dataclass(frozen=True, slots=True)
class RadarAxis:
    """A normalised radar spoke and its screen position."""

    label: str
    value: float
    ratio: float
    angle: float
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class RadarShape:
    """The polygon describing one series on a radar chart."""

    name: str
    color: str
    points: tuple[tuple[float, float], ...]
    path: str


def axis_ratio(
    value: float, maximum: float, scale_type: ScaleType | str = ScaleType.LINEAR
) -> float:
    """Normalise a radar value against its axis maximum."""
    if not math.isfinite(value) or value <= 0 or maximum <= 0:
        return 0.0
    if scale_is_log(scale_type):
        numerator = math.log10(max(value, 1.0))
        denominator = math.log10(max(maximum, 10.0))
        ratio = numerator / denominator if denominator > 0 else 0.0
    else:
        ratio = value / maximum
    return max(0.0, min(1.0, ratio))


def radar_axes(
    points: Iterable[DataPoint],
    *,
    maximum: float | None = None,
    scale_type: ScaleType | str = ScaleType.LINEAR,
) -> tuple[RadarAxis, ...]:
    """Build normalised radar spokes from labelled points."""
    values = list(points)
    if not values:
        return ()
    ceiling = (
        maximum if maximum is not None else max((point.magnitude for point in values), default=0.0)
    )
    axes: list[RadarAxis] = []
    for index, point in enumerate(values):
        ratio = axis_ratio(point.magnitude, ceiling, scale_type)
        x_coord, y_coord = radar_coordinate(index, len(values), 1.18)
        angle = -90.0 + index * 360.0 / len(values)
        axes.append(
            RadarAxis(
                label=point.label,
                value=point.value,
                ratio=ratio,
                angle=angle,
                x=round(x_coord, 4),
                y=round(y_coord, 4),
            )
        )
    return tuple(axes)


@dataclass(frozen=True, slots=True)
class PlotPoint:
    """A data point projected into SVG coordinates."""

    x: float
    y: float
    label: str
    value: float
    series: str
    color: str
    tooltip: str


@dataclass(frozen=True, slots=True)
class BarShape:
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


@dataclass(frozen=True, slots=True)
class LineShape:
    """A projected line series including its path and area fill."""

    name: str
    color: str
    points: tuple[PlotPoint, ...]
    path: str
    area_path: str


@dataclass(frozen=True, slots=True)
class LegendItem:
    """A legend swatch for a series or a category."""

    label: str
    color: str
    kind: str = "series"


@dataclass(frozen=True, slots=True)
class GeometryDatum:
    """A flat observation used by the accessible data table fallback."""

    label: str
    category: str
    series: str
    value: float
    color: str


@dataclass(frozen=True, slots=True)
class ChartGeometry:
    """All coordinates needed to render one chart without recomputing maths."""

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
    ticks: tuple[Tick, ...]
    bars: tuple[BarShape, ...]
    lines: tuple[LineShape, ...]
    radar_axes: tuple[RadarAxis, ...]
    radar_shapes: tuple[RadarShape, ...]
    radar_rings: tuple[float, ...]
    sankey_nodes: tuple[SankeyNodeLayout, ...]
    sankey_flows: tuple[SankeyFlowLayout, ...]
    sparkline_path: str
    sparkline_area: str
    legend: tuple[LegendItem, ...]
    data: tuple[GeometryDatum, ...]

    @property
    def has_data(self) -> bool:
        """Return whether any observation was projected."""
        return bool(self.data or self.sankey_flows)

    @property
    def mark_count(self) -> int:
        """Return the number of visual marks in the projected geometry."""
        return len(self.bars) + len(self.lines) + len(self.radar_shapes) + len(self.sankey_flows)


class GeometryBuilder:
    """Turn a chart specification and its observations into render geometry."""

    def __init__(
        self,
        *,
        chart_id: str,
        chart_type: ChartType,
        payload: ChartPayload,
        points: Sequence[DataPoint],
        options: ChartOptions,
        palette: str,
    ) -> None:
        self.chart_id = chart_id
        self.chart_type = chart_type
        self.payload = payload
        self.options = options
        self.palette = palette
        self.colors = palette_colors(palette, options.theme)
        self.points = limit_points(
            sort_points(points, options.sort, options.direction), options.limit
        )

    def build(self) -> ChartGeometry:
        """Dispatch to the renderer for the declared chart type."""
        values = [point.value for point in self.points]
        scale = Scale.from_values(
            values, scale_type=self.options.scale, tick_count=self.options.tick_count
        )
        common: dict[str, Any] = {
            "chart_id": self.chart_id,
            "chart_type": self.chart_type,
            "width": self.options.width,
            "height": self.options.height,
            "padding": self.options.padding,
            "palette": self.palette,
            "theme": self.options.theme,
            "scale": self.options.scale,
            "domain_min": scale.domain_min,
            "domain_max": scale.domain_max,
            "ticks": scale.ticks(),
            "data": self._data(),
            "legend": self._legend(),
        }
        if self.chart_type is ChartType.BAR:
            return ChartGeometry(**common, **self._bar(scale))
        if self.chart_type is ChartType.LINE:
            return ChartGeometry(**common, **self._line(scale))
        if self.chart_type is ChartType.RADAR:
            return ChartGeometry(**common, **self._radar())
        if self.chart_type is ChartType.SANKEY:
            return ChartGeometry(**common, **self._sankey())
        return ChartGeometry(**common, **self._sparkline())

    def _series_names(self) -> tuple[str, ...]:
        """Return series names in stable first appearance order."""
        names: dict[str, None] = {}
        for point in self.points:
            key = point.series or DEFAULT_SERIES_NAME
            names[key] = None
        return tuple(names)

    def _color_for(self, point: DataPoint) -> str:
        """Return a consistent colour for a point's series."""
        names = self._series_names()
        name = point.series or DEFAULT_SERIES_NAME
        index = names.index(name) if name in names else 0
        return color_at(index, self.colors)

    def _legend(self) -> tuple[LegendItem, ...]:
        """Build legend entries when the chart declares multiple series."""
        if not self.options.show_legend:
            return ()
        names = self._series_names()
        if len(names) <= 1:
            return ()
        return tuple(
            LegendItem(label=name, color=color_at(index, self.colors))
            for index, name in enumerate(names)
        )

    def _data(self) -> tuple[GeometryDatum, ...]:
        """Build the flat table representation of the projected points."""
        return tuple(
            GeometryDatum(
                label=point.label,
                category=point.category,
                series=point.series or DEFAULT_SERIES_NAME,
                value=point.value,
                color=self._color_for(point),
            )
            for point in self.points
        )

    def _bar(self, scale: Scale) -> dict[str, Any]:
        """Compute grouped vertical bars."""
        labels = list(dict.fromkeys(point.label for point in self.points))
        names = self._series_names()
        left = self.options.padding
        right = self.options.width - self.options.padding
        top = self.options.padding
        bottom = self.options.height - self.options.padding
        plot_width = max(1.0, right - left)
        slot = plot_width / max(1, len(labels))
        group_width = slot * 0.72
        bar_width = group_width / max(1, len(names))
        baseline_value = min(max(0.0, scale.domain_min), scale.domain_max)
        baseline = scale.project(baseline_value, bottom, top)
        bars: list[BarShape] = []
        for label_index, label in enumerate(labels):
            for series_index, name in enumerate(names):
                matching = [
                    point
                    for point in self.points
                    if point.label == label and (point.series or DEFAULT_SERIES_NAME) == name
                ]
                for point in matching:
                    y_coord = scale.project(point.value, bottom, top)
                    x_coord = (
                        left
                        + label_index * slot
                        + (slot - group_width) / 2
                        + series_index * bar_width
                    )
                    bars.append(
                        BarShape(
                            label=label,
                            category=point.category,
                            series=name,
                            value=point.value,
                            color=self._color_for(point),
                            x=round(x_coord, 2),
                            y=round(min(y_coord, baseline), 2),
                            width=round(max(1.0, bar_width - 2), 2),
                            height=round(max(1.0, abs(y_coord - baseline)), 2),
                            tooltip=point.tooltip,
                        )
                    )
        return {
            "bars": tuple(bars),
            "lines": (),
            "radar_axes": (),
            "radar_shapes": (),
            "radar_rings": (),
            "sankey_nodes": (),
            "sankey_flows": (),
            "sparkline_path": "",
            "sparkline_area": "",
        }

    def _line(self, scale: Scale) -> dict[str, Any]:
        """Compute projected line series and their area fills."""
        labels = list(dict.fromkeys(point.label for point in self.points))
        names = self._series_names()
        left = self.options.padding
        right = self.options.width - self.options.padding
        top = self.options.padding
        bottom = self.options.height - self.options.padding
        lines: list[LineShape] = []
        x_step = (right - left) / max(1, len(labels) - 1)
        for series_index, name in enumerate(names):
            series_points = [
                point for point in self.points if (point.series or DEFAULT_SERIES_NAME) == name
            ]
            projected: list[PlotPoint] = []
            for point in series_points:
                label_index = labels.index(point.label)
                projected.append(
                    PlotPoint(
                        x=round(left + label_index * x_step, 2),
                        y=round(scale.project(point.value, bottom, top), 2),
                        label=point.label,
                        value=point.value,
                        series=name,
                        color=color_at(series_index, self.colors),
                        tooltip=point.tooltip,
                    )
                )
            path = polyline_path([(point.x, point.y) for point in projected])
            area = ""
            if projected:
                area = (
                    f"{path} L {projected[-1].x:.2f} {bottom:.2f} "
                    f"L {projected[0].x:.2f} {bottom:.2f} Z"
                )
            lines.append(
                LineShape(
                    name=name,
                    color=color_at(series_index, self.colors),
                    points=tuple(projected),
                    path=path,
                    area_path=area,
                )
            )
        return {
            "bars": (),
            "lines": tuple(lines),
            "radar_axes": (),
            "radar_shapes": (),
            "radar_rings": (),
            "sankey_nodes": (),
            "sankey_flows": (),
            "sparkline_path": "",
            "sparkline_area": "",
        }

    def _radar(self) -> dict[str, Any]:
        """Compute radar spokes, rings and one polygon per series."""
        labels = list(dict.fromkeys(point.label for point in self.points))
        maximum = self.options.radar_max or max(
            (point.magnitude for point in self.points), default=0.0
        )
        axes = radar_axes(
            [DataPoint(label=label, value=maximum or 1.0) for label in labels],
            maximum=maximum,
            scale_type=self.options.scale,
        )
        shapes: list[RadarShape] = []
        names = self._series_names()
        for series_index, name in enumerate(names):
            values = [
                point for point in self.points if (point.series or DEFAULT_SERIES_NAME) == name
            ]
            coordinates: list[tuple[float, float]] = []
            for index, label in enumerate(labels):
                matching = next((point for point in values if point.label == label), None)
                ratio = axis_ratio(
                    matching.magnitude if matching else 0.0,
                    maximum,
                    self.options.scale,
                )
                coordinates.append(radar_coordinate(index, max(1, len(labels)), ratio))
            path = polyline_path(coordinates) + (" Z" if coordinates else "")
            shapes.append(
                RadarShape(
                    name=name,
                    color=color_at(series_index, self.colors),
                    points=tuple((round(x, 4), round(y, 4)) for x, y in coordinates),
                    path=path,
                )
            )
        return {
            "bars": (),
            "lines": (),
            "radar_axes": axes,
            "radar_shapes": tuple(shapes),
            "radar_rings": (0.25, 0.5, 0.75, 1.0),
            "sankey_nodes": (),
            "sankey_flows": (),
            "sparkline_path": "",
            "sparkline_area": "",
        }

    def _sankey(self) -> dict[str, Any]:
        """Compute Sankey node positions and ribbon paths."""
        links = self.payload.links
        if not links and self.points:
            links = tuple(
                SankeyLink(source=point.category, target=point.label, value=abs(point.value))
                for point in self.points
                if abs(point.value) > 0
            )
        layout = layout_sankey(
            links,
            colors=self.colors,
            width=self.options.width,
            height=self.options.height,
            padding=self.options.padding,
        )
        return {
            "bars": (),
            "lines": (),
            "radar_axes": (),
            "radar_shapes": (),
            "radar_rings": (),
            "sankey_nodes": layout.nodes,
            "sankey_flows": layout.flows,
            "sparkline_path": "",
            "sparkline_area": "",
        }

    def _sparkline(self) -> dict[str, Any]:
        """Compute the two sparkline paths from the first available series."""
        values = [point.value for point in self.points]
        path = sparkline_path(
            values,
            width=self.options.width,
            height=self.options.height,
            padding=self.options.padding,
        )
        area = sparkline_area_path(
            values,
            width=self.options.width,
            height=self.options.height,
            padding=self.options.padding,
        )
        return {
            "bars": (),
            "lines": (),
            "radar_axes": (),
            "radar_shapes": (),
            "radar_rings": (),
            "sankey_nodes": (),
            "sankey_flows": (),
            "sparkline_path": path,
            "sparkline_area": area,
        }


__all__ = [
    "CHART_TYPES",
    "DEFAULT_PALETTE",
    "MAX_POINTS",
    "PALETTES",
    "AggregateOperation",
    "AggregateResult",
    "AggregateRow",
    "BarShape",
    "ChartGeometry",
    "ChartOptions",
    "ChartPayload",
    "ChartSpec",
    "ChartTheme",
    "ChartType",
    "DataPoint",
    "DataSeries",
    "GeometryBuilder",
    "GeometryDatum",
    "LegendItem",
    "LineShape",
    "Palette",
    "PlotPoint",
    "RadarAxis",
    "RadarShape",
    "SankeyFlowLayout",
    "SankeyLink",
    "SankeyNodeLayout",
    "Scale",
    "ScaleType",
    "SortDirection",
    "SortField",
    "Tick",
    "aggregate_by_category",
    "axis_ratio",
    "color_at",
    "dump_chart_payload",
    "format_number",
    "layout_sankey",
    "limit_points",
    "normalise_sankey_links",
    "palette_colors",
    "palette_descriptor",
    "palette_names",
    "parse_chart_payload",
    "polyline_path",
    "radar_axes",
    "radar_coordinate",
    "relative_luminance",
    "scale_is_log",
    "sort_points",
    "sparkline_area_path",
    "sparkline_coordinates",
    "sparkline_path",
    "text_color_for",
    "with_alpha",
]

CHART_TYPES = tuple(ChartType.values())
