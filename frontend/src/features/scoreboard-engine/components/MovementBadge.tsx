/**
 * A compact badge describing a team's rank movement.
 */

import { Badge } from "../../../components/ui";
import type { BadgeTone } from "../../../components/ui";
import { cn } from "../../../lib/utils";
import type { Movement } from "../types";
import { movementDescription, movementLabel } from "../scoring";
import styles from "./MovementBadge.module.css";

/** Props accepted by {@link MovementBadge}. */
export interface MovementBadgeProps {
  /** The movement direction. */
  movement: Movement;
  /** The number of positions moved. */
  steps?: number;
  /** Hide the textual label and only show the arrow. */
  compact?: boolean;
  /** Additional class applied to the badge. */
  className?: string;
}

/** Map movement directions to semantic badge tones. */
const TONES: Record<Movement, BadgeTone> = {
  up: "success",
  down: "danger",
  stable: "neutral",
  new: "info",
};

/**
 * Render a movement indicator with an accessible description.
 *
 * @param props - The component props.
 * @returns The badge element.
 */
export function MovementBadge({
  movement,
  steps = 0,
  compact = false,
  className,
}: MovementBadgeProps) {
  const description = movementDescription(movement, steps);
  const label = movementLabel(movement, steps);
  return (
    <Badge
      tone={TONES[movement]}
      outline={movement === "stable"}
      className={cn(
        styles.badge,
        styles[movement],
        compact && styles.compact,
        className,
      )}
      aria-label={description}
      title={description}
    >
      <span className={styles.glyph} aria-hidden="true">
        {label}
      </span>
      {!compact && movement !== "stable" ? (
        <span className={styles.text} aria-hidden="true">
          {movement === "new" ? "Entry" : `${steps}`}
        </span>
      ) : null}
    </Badge>
  );
}
