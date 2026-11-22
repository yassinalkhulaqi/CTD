/**
 * Capacity bar showing how much of a member's hour budget is reserved.
 */

import { cn } from "../../../lib/utils";
import { formatHours, utilisation } from "../domain";
import styles from "./CapacityBar.module.css";

/** Props accepted by {@link CapacityBar}. */
export interface CapacityBarProps {
  /** Hours already assigned to the member. */
  assignedHours: number;
  /** The member's total hour budget. */
  capacityHours: number;
  /** Accessible label of the bar. */
  label?: string;
  /** Hide the numeric meta line. */
  compact?: boolean;
  /** Additional class applied to the wrapper. */
  className?: string;
}

/**
 * Render an accessible, theme-aware capacity meter.
 *
 * @param props - The component props.
 * @returns The capacity bar element.
 */
export function CapacityBar({
  assignedHours,
  capacityHours,
  label = "Capacity utilisation",
  compact = false,
  className,
}: CapacityBarProps) {
  const ratio = utilisation(assignedHours, capacityHours);
  const percent = Math.round(ratio * 100);
  const tone =
    percent >= 100 ? "danger" : percent >= 70 ? "warning" : "success";
  const valueText = `${formatHours(assignedHours)} of ${formatHours(capacityHours)} reserved`;

  return (
    <div className={cn(styles.wrap, compact && styles.compact, className)}>
      {!compact ? (
        <div className={styles.meta}>
          <span className={styles.value}>{formatHours(assignedHours)}</span>
          <span className={styles.capacity}>
            / {formatHours(capacityHours)}
          </span>
          <span className={styles.percent}>{percent}%</span>
        </div>
      ) : null}
      <div
        className={styles.track}
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-valuetext={valueText}
        title={valueText}
      >
        <div
          className={cn(styles.fill, styles[tone])}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
