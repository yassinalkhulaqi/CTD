/** Deterministic geometry fixtures used by the feature's component tests. */

import type { Bar, ChartGeometry, LegendItem, Palette, Tick } from "./types";

/** A palette fixture with light and dark variants. */
export const testPalette: Palette = {
  id: "aurora",
  name: "Aurora",
  description: "Test palette",
  colors: ["#4f46e5", "#0891b2"],
  dark_colors: ["#818cf8", "#22d3ee"],
  size: 2,
};

const ticks: Tick[] = [
  { value: 0, label: "0", position: 0 },
  { value: 5, label: "5", position: 0.5 },
  { value: 10, label: "10", position: 1 },
];

const bars: Bar[] = [
  {
    label: "Mon",
    category: "web",
    series: "Team A",
    value: 4,
    color: "#4f46e5",
    x: 40,
    y: 180,
    width: 30,
    height: 80,
    tooltip: "Mon · 4",
  },
  {
    label: "Tue",
    category: "crypto",
    series: "Team A",
    value: 8,
    color: "#0891b2",
    x: 100,
    y: 100,
    width: 30,
    height: 160,
    tooltip: "Tue · 8",
  },
];

const legend: LegendItem[] = [
  { label: "Team A", color: "#4f46e5", kind: "series" },
];

/** Build a geometry payload with sensible defaults for renderer tests. */
export function makeGeometry(
  overrides: Partial<ChartGeometry> = {},
): ChartGeometry {
  return {
    chart_id: "chart-1",
    chart_type: "bar",
    width: 320,
    height: 260,
    padding: 20,
    palette: "aurora",
    theme: "light",
    scale: "linear",
    domain_min: 0,
    domain_max: 10,
    ticks,
    bars,
    lines: [],
    radar_axes: [],
    radar_shapes: [],
    radar_rings: [0.25, 0.5, 0.75, 1],
    sankey_nodes: [],
    sankey_flows: [],
    sparkline_path: "M 20 220 L 300 40",
    sparkline_area: "M 20 220 L 300 40 L 300 240 L 20 240 Z",
    legend,
    data: bars.map((bar) => ({
      label: bar.label,
      category: bar.category,
      series: bar.series,
      value: bar.value,
      color: bar.color,
    })),
    has_data: true,
    mark_count: 2,
    ...overrides,
  };
}
