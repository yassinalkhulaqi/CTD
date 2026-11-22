/** Typed API adapter for the visualisation endpoints. */

import {
  buildQuery,
  get,
  post,
  put,
  type RequestOptions,
} from "../../api/client";
import type {
  AggregateQuery,
  AggregateResult,
  ChartGeometry,
  ChartSpec,
  ChartSpecCreate,
  ChartSpecUpdate,
  DataIngestRequest,
  DataPoint,
  GeometryQuery,
  Palette,
} from "./types";

const BASE_PATH = "/api/visualizations";

function chartPath(chartId: string, suffix = ""): string {
  return `${BASE_PATH}/${encodeURIComponent(chartId)}${suffix}`;
}

/** Endpoints exposed by the visualisation feature. */
export const visualizationsApi = {
  /** List chart specifications with optional filters. */
  list(
    params: {
      teamId?: string;
      chartType?: string;
      limit?: number;
      offset?: number;
    } = {},
    options?: RequestOptions,
  ): Promise<ChartSpec[]> {
    const query = buildQuery({
      team_id: params.teamId,
      chart_type: params.chartType,
      limit: params.limit,
      offset: params.offset,
    });
    return get<ChartSpec[]>(`${BASE_PATH}${query}`, options);
  },

  /** Create a chart specification. */
  create(
    payload: ChartSpecCreate,
    options?: RequestOptions,
  ): Promise<ChartSpec> {
    return post<ChartSpec>(BASE_PATH, payload, options);
  },

  /** Return every categorical palette. */
  palettes(options?: RequestOptions): Promise<Palette[]> {
    return get<Palette[]>(`${BASE_PATH}/palettes`, options);
  },

  /** Return one chart specification. */
  get(chartId: string, options?: RequestOptions): Promise<ChartSpec> {
    return get<ChartSpec>(chartPath(chartId), options);
  },

  /** Update a chart specification. */
  update(
    chartId: string,
    payload: ChartSpecUpdate,
    options?: RequestOptions,
  ): Promise<ChartSpec> {
    return put<ChartSpec>(chartPath(chartId), payload, options);
  },

  /** Replace or append observations on a chart. */
  ingest(
    chartId: string,
    payload: DataIngestRequest,
    options?: RequestOptions,
  ): Promise<DataPoint[]> {
    return post<DataPoint[]>(chartPath(chartId, "/data"), payload, options);
  },

  /** Return the observations stored for a chart. */
  data(chartId: string, options?: RequestOptions): Promise<DataPoint[]> {
    return get<DataPoint[]>(chartPath(chartId, "/data"), options);
  },

  /** Compute render geometry with optional overrides. */
  geometry(
    chartId: string,
    params: GeometryQuery = {},
    options?: RequestOptions,
  ): Promise<ChartGeometry> {
    const query = buildQuery({ ...params });
    return get<ChartGeometry>(chartPath(chartId, `/geometry${query}`), options);
  },

  /** Reduce observations by category. */
  aggregate(
    chartId: string,
    params: AggregateQuery = {},
    options?: RequestOptions,
  ): Promise<AggregateResult> {
    const query = buildQuery({ ...params });
    return get<AggregateResult>(
      chartPath(chartId, `/aggregate${query}`),
      options,
    );
  },
};
