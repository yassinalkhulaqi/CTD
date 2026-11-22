/** Sample chart definitions used by the gallery's empty state. */

import type { ChartSpecCreate, ChartType, DataPointInput } from "./types";

/** Metadata shown by the chart type switcher. */
export const CHART_TYPE_OPTIONS: Array<{
  value: ChartType;
  label: string;
  hint: string;
}> = [
  { value: "bar", label: "Bar", hint: "Compare categories" },
  { value: "line", label: "Line", hint: "Track change over time" },
  { value: "radar", label: "Radar", hint: "Profile several axes" },
  { value: "sankey", label: "Sankey", hint: "Follow flows between stages" },
  { value: "sparkline", label: "Sparkline", hint: "Spot a trend at a glance" },
];

const TREND = [4, 7, 5, 12, 9, 15, 11];
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const CATEGORIES = ["web", "crypto", "pwn", "reverse", "forensics"];
const AXES = ["Speed", "Depth", "Breadth", "Accuracy", "Teamwork"];
const STAGES = ["Start", "Triage", "Exploit", "Flag"];

/** Generate deterministic sample observations for a chart type. */
export function samplePoints(chartType: ChartType): DataPointInput[] {
  if (chartType === "radar") {
    return AXES.map((label, index) => ({
      label,
      value: [8, 5, 7, 9, 6][index],
      category: "team",
    }));
  }
  if (chartType === "sankey") {
    return STAGES.slice(0, 3).map((label, index) => ({
      label,
      value: [12, 9, 6][index],
      category: STAGES[index],
    }));
  }
  return DAYS.map((label, index) => ({
    label,
    value: TREND[index],
    category: CATEGORIES[index % CATEGORIES.length],
  }));
}

/** Build the inline payload for a sample chart. */
export function sampleSeriesJson(chartType: ChartType): string {
  if (chartType === "sankey") {
    return JSON.stringify({
      series: [],
      links: [
        { source: "Start", target: "Triage", value: 12 },
        { source: "Triage", target: "Exploit", value: 9 },
        { source: "Exploit", target: "Flag", value: 6 },
        { source: "Triage", target: "Flag", value: 3 },
      ],
    });
  }
  return JSON.stringify([
    { name: "Team A", points: samplePoints(chartType) },
    {
      name: "Team B",
      points: samplePoints(chartType).map((point, index) => ({
        ...point,
        value: Math.max(1, Math.round(point.value * 0.6) + (index % 2)),
      })),
    },
  ]);
}

/** Build a complete sample specification creation payload. */
export function sampleSpec(chartType: ChartType): ChartSpecCreate {
  return {
    title: `${chartType.charAt(0).toUpperCase()}${chartType.slice(1)} overview`,
    chart_type: chartType,
    series_json: sampleSeriesJson(chartType),
    options_json: JSON.stringify({
      tick_count: 5,
      sort: "label",
      direction: "asc",
      show_legend: true,
      theme: "light",
    }),
    palette: "aurora",
  };
}
