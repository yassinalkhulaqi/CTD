/** Pure SVG and data helpers shared by the visualisation components. */

import type {
  AggregateOperation,
  AggregateRow,
  ChartTheme,
  DataPointInput,
  Palette,
  ParsedSeries,
  Tick,
} from "./types";

/** Default canvas width used by sparkline previews. */
export const SPARKLINE_WIDTH = 120;

/** Default canvas height used by sparkline previews. */
export const SPARKLINE_HEIGHT = 32;

/** Fallback colours used before the palette catalogue loads. */
export const FALLBACK_COLORS = [
  "#4f46e5",
  "#0891b2",
  "#059669",
  "#d97706",
  "#db2777",
  "#7c3aed",
];

/**
 * Format a number for compact axis labels and table cells.
 *
 * @param value - The raw number.
 * @returns A short human readable label.
 */
export function formatValue(value: number): string {
  if (!Number.isFinite(value)) return "—";
  const magnitude = Math.abs(value);
  if (magnitude >= 1_000_000) return `${trimZero(value / 1_000_000)}M`;
  if (magnitude >= 1_000) return `${trimZero(value / 1_000)}k`;
  if (magnitude === 0) return "0";
  if (magnitude < 0.01) return value.toExponential(2);
  return trimZero(Math.round(value * 100) / 100);
}

function trimZero(value: number): string {
  return value
    .toFixed(2)
    .replace(/\.00$/, "")
    .replace(/(\.\d)0$/, "$1");
}

/**
 * Round an axis step to a readable 1, 2, 5 or 10 multiple.
 *
 * @param raw - The raw step size.
 * @returns The rounded step.
 */
export function niceStep(raw: number): number {
  if (!Number.isFinite(raw) || raw <= 0) return 1;
  const exponent = Math.floor(Math.log10(raw));
  const base = 10 ** exponent;
  const fraction = raw / base;
  const chosen = [1, 2, 5, 10].find((candidate) => candidate >= fraction) ?? 10;
  return chosen * base;
}

/**
 * Build linear ticks for a set of values.
 *
 * @param values - Raw observations.
 * @param count - Requested number of ticks.
 * @returns Ticks with numeric values, labels and normal positions.
 */
export function axisTicks(values: number[], count = 5): Tick[] {
  const finite = values.filter(Number.isFinite);
  if (finite.length === 0) {
    return [0, 0.5, 1].map((position) => ({
      value: position,
      label: formatValue(position),
      position,
    }));
  }
  let low = Math.min(...finite);
  let high = Math.max(...finite);
  if (low === high) {
    const spread = Math.max(Math.abs(low) * 0.1, 1);
    low -= spread;
    high += spread;
  }
  const step = niceStep((high - low) / Math.max(1, count - 1));
  low = Math.floor(low / step) * step;
  high = Math.ceil(high / step) * step;
  const ticks: Tick[] = [];
  for (let value = low; value <= high + step * 1e-6; value += step) {
    const rounded = Math.round(value * 1e6) / 1e6;
    ticks.push({
      value: rounded,
      label: formatValue(rounded),
      position: (rounded - low) / (high - low || 1),
    });
  }
  return ticks;
}

/**
 * Project values into sparkline coordinates.
 *
 * @param values - Raw observations.
 * @param width - SVG viewport width.
 * @param height - SVG viewport height.
 * @param padding - Inner padding applied on every edge.
 * @returns Absolute coordinates in SVG user units.
 */
export function sparklineCoordinates(
  values: number[],
  width = SPARKLINE_WIDTH,
  height = SPARKLINE_HEIGHT,
  padding = 3,
): Array<[number, number]> {
  const finite = values.filter(Number.isFinite);
  if (finite.length === 0) return [];
  const innerWidth = Math.max(0, width - padding * 2);
  const innerHeight = Math.max(0, height - padding * 2);
  const minimum = Math.min(...finite);
  const maximum = Math.max(...finite);
  if (minimum === maximum) {
    return finite.map((_, index) => [
      padding + (index * innerWidth) / Math.max(1, finite.length - 1),
      padding + innerHeight / 2,
    ]);
  }
  const span = maximum - minimum;
  return finite.map((value, index) => [
    padding + (index * innerWidth) / Math.max(1, finite.length - 1),
    padding + innerHeight - ((value - minimum) / span) * innerHeight,
  ]);
}

function pathFromCoordinates(coordinates: Array<[number, number]>): string {
  return coordinates
    .map(([xCoord, yCoord], index) => {
      const command = index === 0 ? "M" : "L";
      return `${command} ${xCoord.toFixed(2)} ${yCoord.toFixed(2)}`;
    })
    .join(" ");
}

/**
 * Build a deterministic SVG line path for a sparkline.
 *
 * @param values - Raw observations.
 * @param width - SVG viewport width.
 * @param height - SVG viewport height.
 * @param padding - Inner padding applied on every edge.
 * @returns An SVG path string.
 */
export function sparklinePath(
  values: number[],
  width = SPARKLINE_WIDTH,
  height = SPARKLINE_HEIGHT,
  padding = 3,
): string {
  return pathFromCoordinates(
    sparklineCoordinates(values, width, height, padding),
  );
}

/**
 * Build a closed SVG area path for a sparkline.
 *
 * @param values - Raw observations.
 * @param width - SVG viewport width.
 * @param height - SVG viewport height.
 * @param padding - Inner padding applied on every edge.
 * @returns An SVG path string, or an empty string when there is no data.
 */
export function sparklineAreaPath(
  values: number[],
  width = SPARKLINE_WIDTH,
  height = SPARKLINE_HEIGHT,
  padding = 3,
): string {
  const coordinates = sparklineCoordinates(values, width, height, padding);
  if (coordinates.length === 0) return "";
  const baseline = Math.max(0, height - padding);
  const first = coordinates[0];
  const last = coordinates[coordinates.length - 1];
  return `${pathFromCoordinates(coordinates)} L ${last[0].toFixed(2)} ${baseline.toFixed(2)} L ${first[0].toFixed(2)} ${baseline.toFixed(2)} Z`;
}

/**
 * Return the colours of a palette for the active theme.
 *
 * @param palette - The palette descriptor, when loaded.
 * @param theme - The active interface theme.
 * @returns A colour sequence.
 */
export function paletteSequence(
  palette: Palette | undefined,
  theme: ChartTheme,
): string[] {
  if (!palette) return FALLBACK_COLORS;
  return theme === "dark" ? palette.dark_colors : palette.colors;
}

/**
 * Pick a colour from a sequence, cycling when the index overflows.
 *
 * @param index - Zero based series index.
 * @param colors - Available colours.
 * @returns A CSS colour string.
 */
export function colorAtIndex(index: number, colors: string[]): string {
  if (colors.length === 0) return FALLBACK_COLORS[0];
  return colors[((index % colors.length) + colors.length) % colors.length];
}

/**
 * Parse the compact inline series format used by chart specifications.
 *
 * @param raw - A JSON string containing a list of points or series.
 * @returns Parsed series with labelled points.
 */
export function parseSeries(raw: string): ParsedSeries[] {
  if (!raw.trim()) return [];
  let decoded: unknown;
  try {
    decoded = JSON.parse(raw) as unknown;
  } catch {
    return [];
  }
  if (Array.isArray(decoded)) {
    const hasSeries = decoded.some(
      (item) => typeof item === "object" && item !== null && "points" in item,
    );
    if (!hasSeries) {
      return [{ name: "Series", points: parsePoints(decoded) }];
    }
    return decoded.map((item, index) => {
      if (typeof item !== "object" || item === null || !("points" in item)) {
        return { name: `Series ${index + 1}`, points: [] };
      }
      const record = item as { name?: unknown; points?: unknown };
      const name =
        typeof record.name === "string" && record.name.trim()
          ? record.name
          : `Series ${index + 1}`;
      return {
        name,
        points: Array.isArray(record.points) ? parsePoints(record.points) : [],
      };
    });
  }
  if (typeof decoded === "object" && decoded !== null && "series" in decoded) {
    const record = decoded as { series?: unknown };
    return Array.isArray(record.series)
      ? parseSeries(JSON.stringify(record.series))
      : [];
  }
  return [];
}

function parsePoints(values: unknown[]): DataPointInput[] {
  return values
    .flatMap((item) => {
      if (typeof item !== "object" || item === null) return [];
      const record = item as {
        label?: unknown;
        name?: unknown;
        value?: unknown;
        category?: unknown;
      };
      const label = record.label ?? record.name;
      const value = Number(record.value);
      if (typeof label !== "string" || !Number.isFinite(value)) return [];
      return [
        {
          label,
          value,
          category:
            typeof record.category === "string" ? record.category : "default",
        },
      ];
    })
    .map((point, index) => ({
      ...point,
      label: point.label || `Point ${index + 1}`,
    }));
}

/**
 * Aggregate points by category for the optimistic UI fallback.
 *
 * @param points - Raw observations.
 * @param operation - Reduction to apply.
 * @param colors - Colours assigned in category order.
 * @returns Aggregate rows sorted by descending value.
 */
export function aggregatePoints(
  points: DataPointInput[],
  operation: AggregateOperation,
  colors: string[] = FALLBACK_COLORS,
): AggregateRow[] {
  const grouped = new Map<string, number[]>();
  for (const point of points) {
    const category = point.category?.trim() || "default";
    grouped.set(category, [...(grouped.get(category) ?? []), point.value]);
  }
  return [...grouped.entries()]
    .map(([category, values], index) => {
      let value = values.length;
      if (operation === "sum")
        value = values.reduce((total, item) => total + item, 0);
      if (operation === "avg") {
        value = values.reduce((total, item) => total + item, 0) / values.length;
      }
      if (operation === "max") value = Math.max(...values);
      if (operation === "min") value = Math.min(...values);
      return {
        category,
        operation,
        value,
        count: values.length,
        color: colorAtIndex(index, colors),
        display: formatValue(value),
      };
    })
    .sort(
      (left, right) =>
        right.value - left.value || left.category.localeCompare(right.category),
    );
}

/**
 * Build a radar polygon path from normalised ratios.
 *
 * @param ratios - Values in the interval `[0, 1]`.
 * @param radius - Radius of the outer ring in SVG units.
 * @returns A closed SVG path string.
 */
export function radarPolygonPath(ratios: number[], radius = 1): string {
  if (ratios.length === 0) return "";
  const coordinates = ratios.map((ratio, index) => {
    const angle = -Math.PI / 2 + (index * 2 * Math.PI) / ratios.length;
    const bounded = Math.max(0, Math.min(1, ratio));
    return [
      Math.cos(angle) * bounded * radius,
      Math.sin(angle) * bounded * radius,
    ] as [number, number];
  });
  return `${pathFromCoordinates(coordinates)} Z`;
}

/**
 * Build a smooth Sankey ribbon curve between two node edges.
 *
 * @param startX - Source node right edge.
 * @param startY - Source vertical anchor.
 * @param endX - Target node left edge.
 * @param endY - Target vertical anchor.
 * @returns A cubic SVG path string.
 */
export function sankeyCurve(
  startX: number,
  startY: number,
  endX: number,
  endY: number,
): string {
  const control = (endX - startX) * 0.45;
  return (
    `M ${startX.toFixed(2)} ${startY.toFixed(2)} ` +
    `C ${(startX + control).toFixed(2)} ${startY.toFixed(2)}, ` +
    `${(endX - control).toFixed(2)} ${endY.toFixed(2)}, ` +
    `${endX.toFixed(2)} ${endY.toFixed(2)}`
  );
}
