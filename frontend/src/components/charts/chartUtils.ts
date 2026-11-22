/**
 * Geometry helpers shared by the chart components.
 */

/** A point expressed in the user space of a chart. */
export interface Point {
  /** The horizontal position. */
  x: number;
  /** The vertical position. */
  y: number;
}

/** A band of the horizontal scale. */
export interface Band {
  /** The left edge of the band. */
  start: number;
  /** The width of the band. */
  width: number;
  /** The centre of the band. */
  center: number;
}

/**
 * Return the largest value of a series.
 *
 * @param values - The values of the series.
 * @param fallback - The value returned for an empty series.
 * @returns The maximum value.
 */
export function maxOf(values: readonly number[], fallback = 0): number {
  if (values.length === 0) return fallback;
  return values.reduce(
    (max, value) => (value > max ? value : max),
    Number.NEGATIVE_INFINITY,
  );
}

/**
 * Return the smallest value of a series.
 *
 * @param values - The values of the series.
 * @param fallback - The value returned for an empty series.
 * @returns The minimum value.
 */
export function minOf(values: readonly number[], fallback = 0): number {
  if (values.length === 0) return fallback;
  return values.reduce(
    (min, value) => (value < min ? value : min),
    Number.POSITIVE_INFINITY,
  );
}

/**
 * Return a "nice" upper bound for a chart axis.
 *
 * @param value - The raw maximum of the series.
 * @returns The rounded upper bound.
 */
export function niceCeiling(value: number): number {
  if (value <= 0) return 1;
  const exponent = Math.floor(Math.log10(value));
  const magnitude = 10 ** exponent;
  const normalised = value / magnitude;
  const step =
    normalised <= 1 ? 1 : normalised <= 2 ? 2 : normalised <= 5 ? 5 : 10;
  return step * magnitude;
}

/**
 * Build the ticks of a linear axis.
 *
 * @param max - The upper bound of the axis.
 * @param count - The desired number of ticks.
 * @returns The tick values, including the bounds.
 */
export function linearTicks(max: number, count = 4): number[] {
  if (max <= 0) return [0];
  const step = max / count;
  return Array.from({ length: count + 1 }, (_, index) =>
    Number((step * index).toFixed(6)),
  );
}

/**
 * Map a value onto the vertical scale of a chart.
 *
 * @param value - The value to map.
 * @param max - The upper bound of the scale.
 * @param height - The height of the drawing area.
 * @param padding - The padding reserved at the bottom of the chart.
 * @returns The vertical position.
 */
export function scaleY(
  value: number,
  max: number,
  height: number,
  padding = 0,
): number {
  if (max <= 0) return height - padding;
  const usable = Math.max(1, height - padding);
  return height - padding - (value / max) * usable;
}

/**
 * Build the bands of a categorical horizontal scale.
 *
 * @param count - The number of categories.
 * @param width - The width of the drawing area.
 * @param gapRatio - The ratio of the band occupied by the gap.
 * @returns The bands of the scale.
 */
export function buildBands(
  count: number,
  width: number,
  gapRatio = 0.3,
): Band[] {
  if (count <= 0) return [];
  const band = width / count;
  const gap = band * gapRatio;
  const inner = band - gap;
  return Array.from({ length: count }, (_, index) => {
    const start = index * band + gap / 2;
    return { start, width: inner, center: start + inner / 2 };
  });
}

/**
 * Build an SVG path describing a smooth line.
 *
 * @param points - The points of the series.
 * @returns The path data.
 */
export function buildSmoothPath(points: readonly Point[]): string {
  if (points.length === 0) return "";
  if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;

  let path = `M ${points[0].x} ${points[0].y}`;
  for (let index = 1; index < points.length; index += 1) {
    const previous = points[index - 1];
    const current = points[index];
    const controlX = (previous.x + current.x) / 2;
    path += ` C ${controlX} ${previous.y}, ${controlX} ${current.y}, ${current.x} ${current.y}`;
  }
  return path;
}

/**
 * Build an SVG path describing the area below a line.
 *
 * @param points - The points of the series.
 * @param baseline - The vertical position of the baseline.
 * @returns The path data.
 */
export function buildAreaPath(
  points: readonly Point[],
  baseline: number,
): string {
  if (points.length === 0) return "";
  const line = buildSmoothPath(points);
  const first = points[0];
  const last = points[points.length - 1];
  return `${line} L ${last.x} ${baseline} L ${first.x} ${baseline} Z`;
}

/**
 * Return the hour label of a bucket of a daily timeline.
 *
 * @param index - The index of the bucket.
 * @param total - The total number of buckets.
 * @param reference - The most recent hour of the timeline.
 * @returns The label of the bucket.
 */
export function hourLabel(
  index: number,
  total: number,
  reference: number,
): string {
  const offset = total - 1 - index;
  const hour = (reference - offset + 24) % 24;
  return `${String(hour).padStart(2, "0")}:00`;
}

/**
 * Return the short label of a weekday.
 *
 * @param index - The index of the weekday, starting at Monday.
 * @returns The label of the weekday.
 */
export function weekdayLabel(index: number): string {
  const labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  return labels[((index % 7) + 7) % 7];
}

/**
 * Format a ratio as a compact percentage.
 *
 * @param ratio - The ratio between 0 and 1.
 * @returns The percentage string.
 */
export function percent(ratio: number): string {
  return `${Math.round(Math.max(0, Math.min(1, ratio)) * 100)}%`;
}

/**
 * Return the colour of a heatmap cell for the given intensity.
 *
 * @param intensity - The ratio between 0 and 1.
 * @param accent - The accent colour of the chart.
 * @returns A CSS colour.
 */
export function heatColour(intensity: number, accent = "99, 102, 241"): string {
  const clamped = Math.max(0, Math.min(1, intensity));
  if (clamped === 0) return "var(--surface-sunken)";
  const alpha = 0.12 + clamped * 0.78;
  return `rgba(${accent}, ${alpha.toFixed(3)})`;
}
