/** Compact indicator of a locale's writing direction. */

import { ArrowLeftRight, ArrowRight } from "lucide-react";
import { Badge } from "../../../components/ui";
import type { TextDirection } from "../types";
import styles from "./DirectionBadge.module.css";

/** Props accepted by {@link DirectionBadge}. */
export interface DirectionBadgeProps {
  /** The direction to display. */
  direction: TextDirection;
  /** Optional locale code appended to the label. */
  code?: string;
  /** Show only the direction abbreviation. */
  compact?: boolean;
}

/**
 * Render a labelled LTR or RTL badge.
 *
 * @param props - The badge props.
 * @returns The badge element.
 */
export function DirectionBadge({
  direction,
  code,
  compact = false,
}: DirectionBadgeProps) {
  const rtl = direction === "rtl";
  const label = rtl ? "Right to left" : "Left to right";
  return (
    <Badge
      tone={rtl ? "accent" : "info"}
      className={styles.badge}
      aria-label={label}
    >
      {rtl ? (
        <ArrowLeftRight size={13} aria-hidden="true" />
      ) : (
        <ArrowRight size={13} aria-hidden="true" />
      )}
      <span>{compact ? direction.toUpperCase() : label}</span>
      {code ? <span className={styles.code}>{code}</span> : null}
    </Badge>
  );
}
