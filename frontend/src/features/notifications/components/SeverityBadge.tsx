/** Severity pill with a consistent visual language across the centre. */

import { Badge } from "../../../components/ui";
import { severityClass, severityTone } from "../logic";
import type { Severity } from "../types";
import styles from "./SeverityBadge.module.css";

/** Props accepted by {@link SeverityBadge}. */
export interface SeverityBadgeProps {
  /** The severity to display. */
  severity: Severity;
  /** Show the severity dot. */
  dot?: boolean;
  /** Additional class name. */
  className?: string;
}

/**
 * Render a severity badge.
 *
 * @param props - The component props.
 * @returns The badge element.
 */
export function SeverityBadge({
  severity,
  dot = true,
  className,
}: SeverityBadgeProps) {
  return (
    <Badge
      tone={severityTone(severity)}
      dot={dot}
      className={`${styles.badge} ${styles[severityClass(severity)]} ${className ?? ""}`}
      aria-label={`Severity ${severity}`}
    >
      {severity}
    </Badge>
  );
}
