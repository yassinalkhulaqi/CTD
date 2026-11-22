/** Shared legend for every visualisation type. */

import type { LegendItem } from "../types";
import styles from "./chartStyles.module.css";

/** Props accepted by {@link ChartLegend}. */
export interface ChartLegendProps {
  items: LegendItem[];
}

/** Render a compact, wrapping legend beneath a chart. */
export function ChartLegend({ items }: ChartLegendProps) {
  if (items.length === 0) return null;
  return (
    <ul className={styles.legend} aria-label="Chart legend">
      {items.map((item) => (
        <li className={styles.legendItem} key={`${item.kind}-${item.label}`}>
          <span
            className={styles.legendSwatch}
            style={{ background: item.color }}
            aria-hidden="true"
          />
          <span>{item.label}</span>
        </li>
      ))}
    </ul>
  );
}
