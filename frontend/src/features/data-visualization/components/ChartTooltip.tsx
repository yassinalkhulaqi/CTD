/** Reusable tooltip drawn inside an SVG chart. */

import styles from "./chartStyles.module.css";

/** Tooltip state shared by the chart components. */
export interface TooltipState {
  x: number;
  y: number;
  text: string;
}

/** Props accepted by {@link ChartTooltip}. */
export interface ChartTooltipProps {
  tooltip: TooltipState;
  maxX?: number;
}

/** Render a compact SVG tooltip anchored to a mark. */
export function ChartTooltip({ tooltip, maxX }: ChartTooltipProps) {
  const width = Math.max(66, tooltip.text.length * 6 + 16);
  const rightEdge = maxX ?? tooltip.x + width + 4;
  const left = Math.max(
    2,
    Math.min(tooltip.x - width / 2, rightEdge - width - 2),
  );
  return (
    <g
      className={styles.tooltip}
      transform={`translate(${left} ${tooltip.y - 12})`}
    >
      <rect
        className={styles.tooltipBackground}
        width={width}
        height={24}
        rx={6}
      />
      <text className={styles.tooltipText} x={8} y={16}>
        {tooltip.text}
      </text>
    </g>
  );
}
