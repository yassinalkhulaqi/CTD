/** Compact sparkline trend rendered from pure SVG path geometry. */

import type { ChartGeometry } from "../types";
import { sparklineCoordinates } from "../geometry";
import styles from "./chartStyles.module.css";

/** Props accepted by {@link Sparkline}. */
export interface SparklineProps {
  geometry: ChartGeometry;
}

/** Render the sparkline area, line and last-value marker. */
export function Sparkline({ geometry }: SparklineProps) {
  const values = geometry.data.map((datum) => datum.value);
  const coordinates = sparklineCoordinates(
    values,
    geometry.width,
    geometry.height,
    geometry.padding,
  );
  const last = coordinates[coordinates.length - 1];

  if (!geometry.sparkline_path) {
    return <div className={styles.empty}>No trend data to display</div>;
  }

  return (
    <div className={styles.wrapper}>
      <svg
        className={styles.svg}
        viewBox={`0 0 ${geometry.width} ${geometry.height}`}
        role="img"
        aria-label={`Sparkline trend across ${values.length} points`}
      >
        <title>Sparkline trend</title>
        {geometry.sparkline_area ? (
          <path
            className={styles.sparkArea}
            d={geometry.sparkline_area}
            fill={geometry.data[0]?.color ?? "var(--accent-base)"}
          />
        ) : null}
        <path
          className={styles.sparkLine}
          d={geometry.sparkline_path}
          stroke={geometry.data[0]?.color ?? "var(--accent-base)"}
        />
        {last ? (
          <circle
            className={styles.sparkDot}
            cx={last[0]}
            cy={last[1]}
            r={3.5}
            fill={geometry.data[0]?.color ?? "var(--accent-base)"}
          />
        ) : null}
      </svg>
    </div>
  );
}
