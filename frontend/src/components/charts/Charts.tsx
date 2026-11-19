/**
 * Chart primitives rendering SVG based visualisations.
 */

import { useId, useMemo, useState } from "react";
import { cn, formatNumber } from "../../lib/utils";
import {
  buildAreaPath,
  buildBands,
  buildSmoothPath,
  heatColour,
  hourLabel,
  linearTicks,
  maxOf,
  niceCeiling,
  percent,
  scaleY,
  weekdayLabel,
  type Point,
} from "./chartUtils";
import styles from "./Charts.module.css";

/** Props accepted by {@link BarChart}. */
export interface BarChartProps {
  /** The values rendered as bars. */
  values: number[];
  /** The labels of the bars. */
  labels?: string[];
  /** The height of the drawing area, in pixels. */
  height?: number;
  /** The colour of the bars. */
  color?: string;
  /** The suffix appended to the tooltip value. */
  unit?: string;
  /** Accessible label of the chart. */
  label: string;
  /** Additional class applied to the container. */
  className?: string;
}

/**
 * Render an animated bar chart.
 *
 * @param props - The component props.
 * @returns The chart element.
 */
export function BarChart({
  values,
  labels = [],
  height = 180,
  color = "var(--accent-base)",
  unit = "",
  label,
  className,
}: BarChartProps) {
  const [hovered, setHovered] = useState<number | null>(null);
  const gradientId = useId();

  const max = useMemo(() => niceCeiling(maxOf(values, 1)), [values]);
  const bands = useMemo(() => buildBands(values.length, 100), [values.length]);
  const ticks = useMemo(() => linearTicks(max, 4), [max]);
  const total = values.reduce((sum, value) => sum + value, 0);

  if (values.length === 0) {
    return (
      <div className={cn(styles.empty, className)}>No data to display</div>
    );
  }

  return (
    <figure className={cn(styles.chart, className)}>
      <svg
        viewBox={`0 0 100 ${height + 28}`}
        preserveAspectRatio="none"
        className={styles.svg}
        role="img"
        aria-label={`${label}. Total ${formatNumber(total)}.`}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.95" />
            <stop offset="100%" stopColor={color} stopOpacity="0.35" />
          </linearGradient>
        </defs>

        {ticks.map((tick) => (
          <line
            key={tick}
            x1="0"
            x2="100"
            y1={scaleY(tick, max, height)}
            y2={scaleY(tick, max, height)}
            className={styles.grid}
          />
        ))}

        {values.map((value, index) => {
          const band = bands[index];
          const barHeight = Math.max(
            value > 0 ? 1.5 : 0,
            height - scaleY(value, max, height),
          );
          return (
            <g key={index}>
              <rect
                x={band.start}
                y={height - barHeight}
                width={band.width}
                height={barHeight}
                rx={1.2}
                fill={`url(#${gradientId})`}
                className={cn(
                  styles.bar,
                  hovered === index && styles.barActive,
                )}
                onMouseEnter={() => setHovered(index)}
                onMouseLeave={() => setHovered(null)}
              />
            </g>
          );
        })}
      </svg>

      <div className={styles.axis}>
        {values.map((_value, index) => (
          <button
            key={index}
            type="button"
            className={cn(
              styles.axisLabel,
              hovered === index && styles.axisLabelActive,
            )}
            onMouseEnter={() => setHovered(index)}
            onMouseLeave={() => setHovered(null)}
            onFocus={() => setHovered(index)}
            onBlur={() => setHovered(null)}
          >
            {labels[index] !== undefined ? labels[index] : index}
          </button>
        ))}
      </div>

      {hovered !== null ? (
        <figcaption className={styles.caption}>
          <strong>{formatNumber(values[hovered])}</strong>
          {unit ? ` ${unit}` : ""}
          {labels[hovered] !== undefined ? ` · ${labels[hovered]}` : ""}
        </figcaption>
      ) : null}
    </figure>
  );
}

/** Props accepted by {@link AreaChart}. */
export interface AreaChartProps {
  /** The values of the series. */
  values: number[];
  /** The labels of the points. */
  labels?: string[];
  /** The height of the drawing area, in pixels. */
  height?: number;
  /** The colour of the line. */
  color?: string;
  /** Accessible label of the chart. */
  label: string;
  /** Additional class applied to the container. */
  className?: string;
}

/**
 * Render a smooth area chart.
 *
 * @param props - The component props.
 * @returns The chart element.
 */
export function AreaChart({
  values,
  labels = [],
  height = 180,
  color = "var(--accent-base)",
  label,
  className,
}: AreaChartProps) {
  const [hovered, setHovered] = useState<number | null>(null);
  const gradientId = useId();

  const max = useMemo(() => niceCeiling(maxOf(values, 1)), [values]);
  const points = useMemo<Point[]>(
    () =>
      values.map((value, index) => ({
        x: values.length === 1 ? 50 : (index / (values.length - 1)) * 100,
        y: scaleY(value, max, height),
      })),
    [height, max, values],
  );

  if (values.length === 0) {
    return (
      <div className={cn(styles.empty, className)}>No data to display</div>
    );
  }

  return (
    <figure className={cn(styles.chart, className)}>
      <svg
        viewBox={`0 0 100 ${height}`}
        preserveAspectRatio="none"
        className={styles.svg}
        role="img"
        aria-label={`${label}. Peak ${formatNumber(maxOf(values))}.`}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.35" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>

        {linearTicks(max, 4).map((tick) => (
          <line
            key={tick}
            x1="0"
            x2="100"
            y1={scaleY(tick, max, height)}
            y2={scaleY(tick, max, height)}
            className={styles.grid}
          />
        ))}

        <path
          d={buildAreaPath(points, height)}
          fill={`url(#${gradientId})`}
          className={styles.area}
        />
        <path
          d={buildSmoothPath(points)}
          fill="none"
          stroke={color}
          strokeWidth="1.6"
          vectorEffect="non-scaling-stroke"
          className={styles.line}
        />

        {points.map((point, index) => (
          <circle
            key={index}
            cx={point.x}
            cy={point.y}
            r={hovered === index ? 2.4 : 1.4}
            className={cn(styles.dot, hovered === index && styles.dotActive)}
            onMouseEnter={() => setHovered(index)}
            onMouseLeave={() => setHovered(null)}
          />
        ))}
      </svg>

      <div className={styles.axis}>
        {values.map((_value, index) => (
          <span
            key={index}
            className={cn(
              styles.axisLabel,
              hovered === index && styles.axisLabelActive,
            )}
            onMouseEnter={() => setHovered(index)}
            onMouseLeave={() => setHovered(null)}
          >
            {labels[index] ?? ""}
          </span>
        ))}
      </div>

      {hovered !== null ? (
        <figcaption className={styles.caption}>
          <strong>{formatNumber(values[hovered])}</strong>
          {labels[hovered] !== undefined ? ` · ${labels[hovered]}` : ""}
        </figcaption>
      ) : null}
    </figure>
  );
}

/** A slice of a donut chart. */
export interface DonutSlice {
  /** The label of the slice. */
  label: string;
  /** The value of the slice. */
  value: number;
  /** The colour of the slice. */
  color: string;
}

/** Props accepted by {@link DonutChart}. */
export interface DonutChartProps {
  /** The slices of the chart. */
  slices: DonutSlice[];
  /** The size of the chart, in pixels. */
  size?: number;
  /** The thickness of the ring. */
  thickness?: number;
  /** The content rendered in the centre of the ring. */
  centreLabel?: string;
  /** Accessible label of the chart. */
  label: string;
  /** Additional class applied to the container. */
  className?: string;
}

/**
 * Render a donut chart.
 *
 * @param props - The component props.
 * @returns The chart element.
 */
export function DonutChart({
  slices,
  size = 160,
  thickness = 18,
  centreLabel,
  label,
  className,
}: DonutChartProps) {
  const total = slices.reduce((sum, slice) => sum + slice.value, 0);
  const radius = (size - thickness) / 2;
  const circumference = 2 * Math.PI * radius;

  let offset = 0;

  if (total === 0) {
    return (
      <div className={cn(styles.empty, className)}>No data to display</div>
    );
  }

  return (
    <figure className={cn(styles.donut, className)}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        role="img"
        aria-label={`${label}. ${formatNumber(total)} in total.`}
      >
        <g transform={`rotate(-90 ${size / 2} ${size / 2})`}>
          {slices.map((slice) => {
            const fraction = slice.value / total;
            const dash = fraction * circumference;
            const element = (
              <circle
                key={slice.label}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke={slice.color}
                strokeWidth={thickness}
                strokeDasharray={`${dash} ${circumference - dash}`}
                strokeDashoffset={-offset}
                className={styles.donutSlice}
              />
            );
            offset += dash;
            return element;
          })}
        </g>
      </svg>
      {centreLabel ? (
        <span className={styles.donutCentre}>{centreLabel}</span>
      ) : null}
      <figcaption className={styles.legend}>
        {slices.map((slice) => (
          <span key={slice.label} className={styles.legendItem}>
            <span
              className={styles.legendSwatch}
              style={{ background: slice.color }}
            />
            {slice.label}
            <span className={styles.legendValue}>
              {percent(slice.value / total)}
            </span>
          </span>
        ))}
      </figcaption>
    </figure>
  );
}

/** Props accepted by {@link Heatmap}. */
export interface HeatmapProps {
  /** The matrix of the heatmap, indexed by row then column. */
  matrix: number[][];
  /** The labels of the rows. */
  rowLabels?: string[];
  /** The labels of the columns. */
  columnLabels?: string[];
  /** The accent colour of the cells. */
  accent?: string;
  /** Accessible label of the chart. */
  label: string;
  /** Additional class applied to the container. */
  className?: string;
}

/**
 * Render a weekday and hour activity heatmap.
 *
 * @param props - The component props.
 * @returns The chart element.
 */
export function Heatmap({
  matrix,
  rowLabels,
  columnLabels,
  accent = "99, 102, 241",
  label,
  className,
}: HeatmapProps) {
  const [hovered, setHovered] = useState<{
    row: number;
    column: number;
  } | null>(null);

  const max = useMemo(() => maxOf(matrix.flat(), 1), [matrix]);

  if (matrix.length === 0) {
    return (
      <div className={cn(styles.empty, className)}>No data to display</div>
    );
  }

  return (
    <figure className={cn(styles.heatmap, className)}>
      <div className={styles.heatmapGrid} role="img" aria-label={label}>
        {matrix.map((row, rowIndex) => (
          <div key={rowIndex} className={styles.heatmapRow}>
            {row.map((value, columnIndex) => (
              <button
                key={columnIndex}
                type="button"
                className={cn(
                  styles.heatmapCell,
                  hovered?.row === rowIndex &&
                    hovered?.column === columnIndex &&
                    styles.heatmapCellActive,
                )}
                style={{ background: heatColour(value / max, accent) }}
                onMouseEnter={() =>
                  setHovered({ row: rowIndex, column: columnIndex })
                }
                onMouseLeave={() => setHovered(null)}
                aria-label={`${formatNumber(value)} solves`}
              />
            ))}
          </div>
        ))}
      </div>

      <div className={styles.heatmapLabels}>
        {matrix.map((_, rowIndex) => (
          <span key={rowIndex} className={styles.heatmapRowLabel}>
            {rowLabels?.[rowIndex] ?? weekdayLabel(rowIndex)}
          </span>
        ))}
      </div>

      {hovered ? (
        <figcaption className={styles.caption}>
          <strong>{formatNumber(matrix[hovered.row][hovered.column])}</strong>{" "}
          solves · {rowLabels?.[hovered.row] ?? weekdayLabel(hovered.row)}{" "}
          {columnLabels?.[hovered.column] ?? `${hovered.column}:00`}
        </figcaption>
      ) : null}
    </figure>
  );
}

/** Props accepted by {@link Sparkline}. */
export interface SparklineProps {
  /** The values of the series. */
  values: number[];
  /** The width of the sparkline, in pixels. */
  width?: number;
  /** The height of the sparkline, in pixels. */
  height?: number;
  /** The colour of the line. */
  color?: string;
  /** Accessible label of the sparkline. */
  label: string;
  /** Additional class applied to the container. */
  className?: string;
}

/**
 * Render a compact inline trend line.
 *
 * @param props - The component props.
 * @returns The sparkline element.
 */
export function Sparkline({
  values,
  width = 96,
  height = 28,
  color = "var(--accent-base)",
  label,
  className,
}: SparklineProps) {
  const max = useMemo(() => Math.max(1, maxOf(values, 1)), [values]);
  const points = useMemo<Point[]>(
    () =>
      values.map((value, index) => ({
        x:
          values.length === 1
            ? width / 2
            : (index / (values.length - 1)) * width,
        y: height - (value / max) * height,
      })),
    [height, max, values, width],
  );

  if (values.length === 0) {
    return <span className={cn(styles.empty, className)}>—</span>;
  }

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={cn(styles.sparkline, className)}
      role="img"
      aria-label={label}
    >
      <path
        d={buildSmoothPath(points)}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
      />
      <circle
        cx={points[points.length - 1].x}
        cy={points[points.length - 1].y}
        r="1.8"
        fill={color}
      />
    </svg>
  );
}

/**
 * Return the labels of the trailing hours of a timeline.
 *
 * @param total - The number of buckets.
 * @param reference - The most recent hour.
 * @returns The labels of the buckets.
 */
export function timelineLabels(
  total: number,
  reference = new Date().getHours(),
): string[] {
  return Array.from({ length: total }, (_, index) =>
    hourLabel(index, total, reference),
  );
}
