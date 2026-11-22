/** Domain and view types for the visualisation gallery. */

export type ChartType = "bar" | "line" | "radar" | "sankey" | "sparkline";

export type ScaleType = "linear" | "log";
export type AggregateOperation = "sum" | "avg" | "max" | "min" | "count";
export type SortDirection = "asc" | "desc";
export type ChartTheme = "light" | "dark";
export type ViewMode = "chart" | "table";

/** Persisted chart definition returned by the API. */
export interface ChartSpec {
  id: string;
  team_id: string;
  title: string;
  chart_type: ChartType;
  series_json: string;
  options_json: string;
  palette: string;
  created_at: string;
  updated_at: string;
  point_count: number;
  is_empty: boolean;
}

/** A labelled observation accepted by the ingestion endpoint. */
export interface DataPointInput {
  label: string;
  value: number;
  category?: string;
}

/** A stored observation with its owning series. */
export interface DataPoint {
  label: string;
  value: number;
  category: string;
  series: string;
}

/** Payload used to create a chart specification. */
export interface ChartSpecCreate {
  id?: string;
  team_id?: string;
  title: string;
  chart_type: ChartType;
  series_json?: string;
  options_json?: string;
  palette?: string;
}

/** Partial payload used to update a chart specification. */
export interface ChartSpecUpdate {
  title?: string;
  chart_type?: ChartType;
  series_json?: string;
  options_json?: string;
  palette?: string;
}

/** Payload used to ingest a batch of observations. */
export interface DataIngestRequest {
  points: DataPointInput[];
  replace?: boolean;
}

/** A named categorical colour palette. */
export interface Palette {
  id: string;
  name: string;
  description: string;
  colors: string[];
  dark_colors: string[];
  size: number;
}

/** An axis tick projected onto a chart axis. */
export interface Tick {
  value: number;
  label: string;
  position: number;
}

/** A positioned bar mark. */
export interface Bar {
  label: string;
  category: string;
  series: string;
  value: number;
  color: string;
  x: number;
  y: number;
  width: number;
  height: number;
  tooltip: string;
}

/** A point projected into SVG coordinates. */
export interface PlotPoint {
  x: number;
  y: number;
  label: string;
  value: number;
  series: string;
  color: string;
  tooltip: string;
}

/** One projected line series. */
export interface LineSeries {
  name: string;
  color: string;
  points: PlotPoint[];
  path: string;
  area_path: string;
}

/** A normalised radar spoke. */
export interface RadarAxis {
  label: string;
  value: number;
  ratio: number;
  angle: number;
  x: number;
  y: number;
}

/** A radar polygon. */
export interface RadarShape {
  name: string;
  color: string;
  points: number[][];
  path: string;
}

/** A positioned Sankey node. */
export interface SankeyNode {
  id: string;
  label: string;
  value: number;
  depth: number;
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
}

/** A positioned Sankey ribbon. */
export interface SankeyFlow {
  source: string;
  target: string;
  value: number;
  width: number;
  path: string;
  color: string;
}

/** A legend entry. */
export interface LegendItem {
  label: string;
  color: string;
  kind: string;
}

/** A row used by the accessible data table fallback. */
export interface GeometryDatum {
  label: string;
  category: string;
  series: string;
  value: number;
  color: string;
}

/** The complete SVG geometry returned by the backend. */
export interface ChartGeometry {
  chart_id: string;
  chart_type: ChartType;
  width: number;
  height: number;
  padding: number;
  palette: string;
  theme: ChartTheme;
  scale: ScaleType;
  domain_min: number;
  domain_max: number;
  ticks: Tick[];
  bars: Bar[];
  lines: LineSeries[];
  radar_axes: RadarAxis[];
  radar_shapes: RadarShape[];
  radar_rings: number[];
  sankey_nodes: SankeyNode[];
  sankey_flows: SankeyFlow[];
  sparkline_path: string;
  sparkline_area: string;
  legend: LegendItem[];
  data: GeometryDatum[];
  has_data: boolean;
  mark_count: number;
}

/** One row of a category aggregation. */
export interface AggregateRow {
  category: string;
  operation: AggregateOperation;
  value: number;
  count: number;
  color: string;
  display: string;
}

/** The result of a category aggregation. */
export interface AggregateResult {
  chart_id: string;
  operation: AggregateOperation;
  rows: AggregateRow[];
  total: number;
  categories: number;
  is_empty: boolean;
}

/** Query parameters accepted by the geometry endpoint. */
export interface GeometryQuery {
  scale?: ScaleType;
  theme?: ChartTheme;
  sort?: "label" | "value" | "category";
  direction?: SortDirection;
  tick_count?: number;
  limit?: number;
  width?: number;
  height?: number;
  padding?: number;
  radar_max?: number;
}

/** Query parameters accepted by the aggregate endpoint. */
export interface AggregateQuery {
  operation?: AggregateOperation;
  category?: string;
  sort?: "label" | "value" | "category";
  direction?: SortDirection;
  limit?: number;
}

/** A parsed inline series used by previews. */
export interface ParsedSeries {
  name: string;
  points: DataPointInput[];
}

/** Human readable metadata for the chart type switcher. */
export interface ChartTypeOption {
  value: ChartType;
  label: string;
  hint: string;
}
