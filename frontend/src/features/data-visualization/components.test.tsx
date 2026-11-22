/** Rendered interaction tests for the chart components. */

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BarChart } from "./components/BarChart";
import { ChartCard } from "./components/ChartCard";
import { LineChart } from "./components/LineChart";
import { RadarChart } from "./components/RadarChart";
import { SankeyDiagram } from "./components/SankeyDiagram";
import { Sparkline } from "./components/Sparkline";
import { makeGeometry } from "./fixtures";
import type { ChartSpec } from "./types";

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

describe("chart renderers", () => {
  it("renders bars with accessible tooltips and a legend", () => {
    const { container } = render(<BarChart geometry={makeGeometry()} />);
    expect(
      screen.getByRole("img", { name: "Bar chart with 2 bars" }),
    ).toBeInTheDocument();
    expect(container.querySelectorAll("rect[role='img']")).toHaveLength(2);
    fireEvent.focus(screen.getByLabelText("Mon · 4"));
    expect(screen.getByText("Mon · 4")).toBeInTheDocument();
    expect(screen.getByLabelText("Chart legend")).toHaveTextContent("Team A");
  });

  it("renders line paths, markers and point tooltips", () => {
    const geometry = makeGeometry({
      chart_type: "line",
      bars: [],
      lines: [
        {
          name: "Team A",
          color: "#4f46e5",
          path: "M 40 220 L 100 100",
          area_path: "M 40 220 L 100 100 L 100 240 L 40 240 Z",
          points: [
            {
              x: 40,
              y: 220,
              label: "Mon",
              value: 4,
              series: "Team A",
              color: "#4f46e5",
              tooltip: "Mon · 4",
            },
          ],
        },
      ],
    });
    const { container } = render(<LineChart geometry={geometry} />);
    expect(
      screen.getByRole("img", { name: "Line chart with 1 series" }),
    ).toBeInTheDocument();
    expect(container.querySelector("path[stroke='#4f46e5']")).toHaveAttribute(
      "d",
      "M 40 220 L 100 100",
    );
    fireEvent.mouseEnter(screen.getByLabelText("Mon · 4"));
    expect(screen.getByText("Mon · 4")).toBeInTheDocument();
  });

  it("renders radar polygons and normalised axis labels", () => {
    const geometry = makeGeometry({
      chart_type: "radar",
      bars: [],
      radar_axes: [
        { label: "Speed", value: 8, ratio: 0.8, angle: -90, x: 0, y: 1.18 },
        { label: "Depth", value: 5, ratio: 0.5, angle: -18, x: 1.12, y: 0.36 },
      ],
      radar_shapes: [
        {
          name: "Team A",
          color: "#4f46e5",
          points: [
            [0, -0.8],
            [0.56, 0.18],
          ],
          path: "M 0.00 -0.80 L 0.56 0.18 Z",
        },
      ],
    });
    render(<RadarChart geometry={geometry} />);
    expect(
      screen.getByRole("img", { name: "Radar chart with 2 axes" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Speed")).toBeInTheDocument();
    expect(screen.getByText("Depth")).toBeInTheDocument();
    expect(screen.getByText("Team A radar profile")).toBeInTheDocument();
  });

  it("renders Sankey ribbons and labelled nodes", () => {
    const geometry = makeGeometry({
      chart_type: "sankey",
      bars: [],
      sankey_nodes: [
        {
          id: "start",
          label: "Start",
          value: 12,
          depth: 0,
          x: 20,
          y: 40,
          width: 14,
          height: 60,
          color: "#4f46e5",
        },
        {
          id: "flag",
          label: "Flag",
          value: 6,
          depth: 1,
          x: 260,
          y: 60,
          width: 14,
          height: 40,
          color: "#0891b2",
        },
      ],
      sankey_flows: [
        {
          source: "Start",
          target: "Flag",
          value: 6,
          width: 12,
          path: "M 34 50 C 136 50, 144 70, 260 70",
          color: "#4f46e5",
        },
      ],
    });
    render(<SankeyDiagram geometry={geometry} />);
    expect(
      screen.getByRole("img", { name: "Sankey diagram with 1 flows" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Start")).toBeInTheDocument();
    expect(screen.getByText("Flag")).toBeInTheDocument();
    expect(screen.getByText("Start → Flag: 6")).toBeInTheDocument();
  });

  it("renders sparkline paths and the last value marker", () => {
    const { container } = render(
      <Sparkline geometry={makeGeometry({ chart_type: "sparkline" })} />,
    );
    expect(
      screen.getByRole("img", { name: "Sparkline trend across 2 points" }),
    ).toBeInTheDocument();
    expect(container.querySelector("path[stroke='#4f46e5']")).toHaveAttribute(
      "d",
      "M 20 220 L 300 40",
    );
    expect(container.querySelector("circle")).toBeInTheDocument();
  });

  it("reports chart card selection through its button", () => {
    const onSelect = vi.fn();
    render(<ChartCard spec={spec} selected={false} onSelect={onSelect} />);
    fireEvent.click(screen.getByRole("button", { name: "Open chart" }));
    expect(onSelect).toHaveBeenCalledWith("chart-1");
    expect(screen.getByText("2 points")).toBeInTheDocument();
  });
});
