/** Accessible multi-series line chart rendered from backend geometry. */

import { useState } from "react";
import type { ChartGeometry, PlotPoint } from "../types";
import { ChartLegend } from "./ChartLegend";
import { ChartTooltip, type TooltipState } from "./ChartTooltip";
import styles from "./chartStyles.module.css";

/** Props accepted by {@link LineChart}. */
export interface LineChartProps {
  geometry: ChartGeometry;
}

/** Render projected line paths, area fills, markers and tooltips. */
export function LineChart({ geometry }: LineChartProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const top = geometry.padding;
  const bottom = geometry.height - geometry.padding;
  const plotHeight = Math.max(1, bottom - top);

  if (geometry.lines.length === 0) {
    return <div className={styles.empty}>No line data to display</div>;
  }

  const show = (point: PlotPoint) =>
    setTooltip({ x: point.x + 8, y: point.y - 8, text: point.tooltip });

  return (
    <div className={styles.wrapper}>
      <svg
        className={styles.svg}
        viewBox={`0 0 ${geometry.width} ${geometry.height}`}
        role="img"
        aria-label={`Line chart with ${geometry.lines.length} series`}
      >
        <title>Line chart</title>
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
        {geometry.lines.map((line) => (
          <g key={line.name}>
            {line.area_path ? (
              <path
                className={styles.lineArea}
                d={line.area_path}
                fill={line.color}
              />
            ) : null}
            <path className={styles.line} d={line.path} stroke={line.color} />
            {line.points.map((point, index) => (
              <circle
                className={styles.point}
                key={`${point.label}-${index}`}
                cx={point.x}
                cy={point.y}
                r={4}
                fill={point.color}
                tabIndex={0}
                role="img"
                aria-label={point.tooltip}
                onMouseEnter={() => show(point)}
                onFocus={() => show(point)}
                onMouseLeave={() => setTooltip(null)}
                onBlur={() => setTooltip(null)}
              />
            ))}
          </g>
        ))}
        {geometry.lines[0]?.points.map((point, index) => (
          <text
            className={styles.axisLabel}
            key={`${point.label}-${index}`}
            x={point.x}
            y={bottom + 18}
            textAnchor="middle"
          >
            {point.label}
          </text>
        ))}
        {tooltip ? (
          <ChartTooltip tooltip={tooltip} maxX={geometry.width} />
        ) : null}
      </svg>
      <ChartLegend items={geometry.legend} />
    </div>
  );
}
