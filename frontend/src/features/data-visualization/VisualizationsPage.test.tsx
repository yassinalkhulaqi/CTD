/** Route-level tests for the visualisation gallery page. */

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AggregateResult, ChartSpec } from "./types";

const mocks = vi.hoisted(() => ({
  theme: vi.fn(() => "light"),
  useVisualizations: vi.fn(),
  state: {
    specs: [] as ChartSpec[],
    palettes: [],
    selected: null as ChartSpec | null,
    geometry: null,
    aggregate: null as AggregateResult | null,
    loading: false,
    analysisLoading: false,
    error: null as string | null,
    viewMode: "chart" as "chart" | "table",
    select: vi.fn(),
    setViewMode: vi.fn(),
    refresh: vi.fn(),
    create: vi.fn(),
    createSamples: vi.fn(),
    update: vi.fn(),
    ingest: vi.fn(),
  },
}));

vi.mock("./hooks", () => ({
  useInterfaceTheme: mocks.theme,
  useVisualizations: mocks.useVisualizations,
}));

import { makeGeometry } from "./fixtures";
import { VisualizationsPage } from "./VisualizationsPage";

const spec: ChartSpec = {
  id: "chart-1",
  team_id: "team-1",
  title: "Solves by day",
  chart_type: "bar",
  series_json: "[]",
  options_json: "{}",
  palette: "aurora",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  point_count: 2,
  is_empty: false,
};

const aggregate: AggregateResult = {
  chart_id: "chart-1",
  operation: "sum",
  rows: [
    {
      category: "web",
      operation: "sum",
      value: 6,
      count: 2,
      color: "#4f46e5",
      display: "6",
    },
  ],
  total: 6,
  categories: 1,
  is_empty: false,
};

function renderPage(overrides: Record<string, unknown> = {}) {
  const state = {
    ...mocks.state,
    specs: [spec],
    selected: spec,
    geometry: makeGeometry(),
    aggregate,
    ...overrides,
  };
  mocks.useVisualizations.mockReturnValue(state);
  return { state, ...render(<VisualizationsPage />) };
}

describe("VisualizationsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows a loading state while metadata is fetched", () => {
    renderPage({
      loading: true,
      specs: [],
      selected: null,
      geometry: null,
      aggregate: null,
    });
    expect(screen.getByText("Loading charts…")).toBeInTheDocument();
    expect(screen.getByLabelText("Loading visualisations")).toBeInTheDocument();
  });

  it("offers sample creation when the gallery is empty", () => {
    const { state } = renderPage({
      specs: [],
      selected: null,
      geometry: null,
      aggregate: null,
    });
    expect(screen.getByText("No charts yet")).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Create sample gallery" }),
    );
    expect(state.createSamples).toHaveBeenCalledOnce();
  });

  it("renders gallery, geometry and the chart type switcher", () => {
    const { state } = renderPage();
    expect(
      screen.getByRole("heading", { name: "Visualizations" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Solves by day")).toHaveLength(2);
    expect(
      screen.getByRole("img", { name: "Bar chart with 2 bars" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Category aggregation")).toHaveTextContent(
      "web",
    );
    fireEvent.click(screen.getByRole("button", { name: "Line" }));
    expect(state.update).toHaveBeenCalledWith("chart-1", {
      chart_type: "line",
    });
  });

  it("renders the accessible table fallback", () => {
    renderPage({ viewMode: "table" });
    const table = screen.getByRole("table", { name: "Chart source data" });
    expect(table).toHaveTextContent("Label");
    expect(table).toHaveTextContent("Mon");
    expect(table).toHaveTextContent("4");
  });

  it("ingests sample observations for the selected chart", () => {
    const { state } = renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Add sample data" }));
    expect(state.ingest).toHaveBeenCalledWith("chart-1", expect.any(Array));
  });

  it("surfaces load errors with a retry action", () => {
    const { state } = renderPage({
      error: "Service unavailable",
      specs: [],
      selected: null,
      geometry: null,
      aggregate: null,
    });
    expect(screen.getByText("Visualisations unavailable")).toBeInTheDocument();
    expect(screen.getByText("Service unavailable")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(state.refresh).toHaveBeenCalledOnce();
  });
});
