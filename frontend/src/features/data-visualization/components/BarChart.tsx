/** Accessible grouped bar chart rendered from backend geometry. */

import { useState } from "react";
import type { ChartGeometry } from "../types";
import { ChartLegend } from "./ChartLegend";
import { ChartTooltip, type TooltipState } from "./ChartTooltip";
import styles from "./chartStyles.module.css";

/** Props accepted by {@link BarChart}. */
export interface BarChartProps {
  geometry: ChartGeometry;
}

function normalizedPosition(
  value: number,
  minimum: number,
  maximum: number,
): number {
  if (maximum <= minimum) return 0;
  return Math.max(0, Math.min(1, (value - minimum) / (maximum - minimum)));
}

/** Render bars, grid lines, axis labels and an optional legend. */
export function BarChart({ geometry }: BarChartProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const top = geometry.padding;
  const bottom = geometry.height - geometry.padding;
  const plotHeight = Math.max(1, bottom - top);
  const zero = normalizedPosition(0, geometry.domain_min, geometry.domain_max);
  const baseline = bottom - zero * plotHeight;
  const labels = [...new Set(geometry.data.map((datum) => datum.label))];

  if (geometry.bars.length === 0) {
    return <div className={styles.empty}>No bar data to display</div>;
  }

  const show = (bar: { x: number; y: number; tooltip: string }) =>
    setTooltip({ x: bar.x + 12, y: bar.y, text: bar.tooltip });

  return (
    <div className={styles.wrapper}>
      <svg
        className={styles.svg}
        viewBox={`0 0 ${geometry.width} ${geometry.height}`}
        role="img"
        aria-label={`Bar chart with ${geometry.bars.length} bars`}
      >
        <title>Bar chart</title>
        {geometry.ticks.map((tick) => {
          const yCoord = bottom - tick.position * plotHeight;
          return (
            <g key={tick.value}>
              <line
                className={styles.gridLine}
                x1={geometry.padding}
                x2={geometry.width - geometry.padding}
                y1={yCoord}
                y2={yCoord}
              />
              <text className={styles.tickLabel} x={4} y={yCoord - 4}>
                {tick.label}
              </text>
            </g>
          );
        })}
        <line
          className={styles.axisLine}
          x1={geometry.padding}
          x2={geometry.width - geometry.padding}
          y1={baseline}
          y2={baseline}
        />
        {geometry.bars.map((bar, index) => (
          <rect
            className={styles.bar}
            key={`${bar.series}-${bar.label}-${index}`}
            x={bar.x}
            y={bar.y}
            width={bar.width}
            height={bar.height}
            rx={2}
            fill={bar.color}
            tabIndex={0}
            role="img"
            aria-label={bar.tooltip}
            onMouseEnter={() => show(bar)}
            onFocus={() => show(bar)}
            onMouseLeave={() => setTooltip(null)}
            onBlur={() => setTooltip(null)}
          />
        ))}
        {labels.map((label) => {
          const matching = geometry.bars.filter((bar) => bar.label === label);
          const xCoord =
            matching.reduce((total, bar) => total + bar.x + bar.width / 2, 0) /
            Math.max(1, matching.length);
          return (
            <text
              className={styles.axisLabel}
              key={label}
              x={xCoord}
              y={bottom + 18}
              textAnchor="middle"
            >
              {label}
            </text>
          );
        })}
        {tooltip ? (
          <ChartTooltip tooltip={tooltip} maxX={geometry.width} />
        ) : null}
      </svg>
      <ChartLegend items={geometry.legend} />
    </div>
  );
}
