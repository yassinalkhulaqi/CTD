/** SVG visualisation of the geometric hint cost curve. */

import { useMemo } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../../components/ui";
import { formatCredits } from "../hints";
import type { CostPoint } from "../types";
import styles from "./CostCurve.module.css";

/** Props accepted by {@link CostCurve}. */
export interface CostCurveProps {
  points: CostPoint[];
  currentTier?: number;
  compact?: boolean;
}

const WIDTH = 320;
const HEIGHT = 132;
const PAD = { left: 12, right: 12, top: 12, bottom: 26 };

/**
 * Render bars for tier prices and a line for cumulative spend.
 *
 * @param props - The component props.
 * @returns The cost curve card.
 */
export function CostCurve({
  points,
  currentTier,
  compact = false,
}: CostCurveProps) {
  const geometry = useMemo(() => {
    if (points.length === 0) return null;
    const maximum = Math.max(1, ...points.map((point) => point.cumulative));
    const step =
      points.length > 1
        ? (WIDTH - PAD.left - PAD.right) / (points.length - 1)
        : 0;
    const x = (index: number) => PAD.left + index * step;
    const y = (value: number) =>
      HEIGHT - PAD.bottom - (value / maximum) * (HEIGHT - PAD.top - PAD.bottom);
    const line = points
      .map(
        (point, index) =>
          `${index === 0 ? "M" : "L"}${x(index)},${y(point.cumulative)}`,
      )
      .join(" ");
    const area = `${line} L${x(points.length - 1)},${HEIGHT - PAD.bottom} L${x(0)},${HEIGHT - PAD.bottom} Z`;
    return { x, y, line, area, baseline: HEIGHT - PAD.bottom };
  }, [points]);

  return (
    <Card className={compact ? styles.compact : undefined}>
      <CardHeader>
        <CardTitle level={3}>Cost curve</CardTitle>
      </CardHeader>
      <CardContent>
        {!geometry ? (
          <p className={styles.empty}>Author hints to see their price curve.</p>
        ) : (
          <>
            <svg
              className={styles.chart}
              viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
              role="img"
              aria-label="Hint prices grow geometrically across the three tiers"
              preserveAspectRatio="xMidYMid meet"
            >
              <title>Hint cost curve</title>
              <line
                className={styles.axis}
                x1={PAD.left}
                x2={WIDTH - PAD.right}
                y1={geometry.baseline}
                y2={geometry.baseline}
              />
              <path className={styles.area} d={geometry.area} />
              {points.map((point, index) => (
                <g key={point.tier} className={styles.group}>
                  <rect
                    className={
                      point.tier === currentTier ? styles.barActive : styles.bar
                    }
                    x={geometry.x(index) - 13}
                    y={geometry.y(point.cost)}
                    width={26}
                    height={Math.max(
                      2,
                      geometry.baseline - geometry.y(point.cost),
                    )}
                    rx={4}
                  />
                  <circle
                    className={styles.node}
                    cx={geometry.x(index)}
                    cy={geometry.y(point.cumulative)}
                    r={4}
                  />
                  <text
                    className={styles.label}
                    x={geometry.x(index)}
                    y={HEIGHT - 6}
                    textAnchor="middle"
                  >
                    T{point.tier}
                  </text>
                </g>
              ))}
              <path className={styles.line} d={geometry.line} />
            </svg>
            <ul className={styles.legend}>
              {points.map((point) => (
                <li key={point.tier} className={styles.legendItem}>
                  <span className={styles.legendTier}>Tier {point.tier}</span>
                  <span className={styles.legendValue}>
                    {formatCredits(point.cost)} credits
                  </span>
                  <span className={styles.legendTotal}>
                    {formatCredits(point.cumulative)} total
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </CardContent>
    </Card>
  );
}
