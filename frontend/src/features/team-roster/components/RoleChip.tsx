/**
 * A compact role badge used across the roster table and member cards.
 */

import { cn } from "../../../lib/utils";
import { Badge } from "../../../components/ui";
import { ROLE_META } from "../domain";
import type { RosterRole } from "../types";
import styles from "./RoleChip.module.css";

/** Props accepted by {@link RoleChip}. */
export interface RoleChipProps {
  /** The role to display. */
  role: RosterRole;
  /** Render the badge without its dot. */
  compact?: boolean;
  /** Additional class applied to the badge. */
  className?: string;
}

/**
 * Render a role with its semantic colour and an accessible label.
 *
 * @param props - The component props.
 * @returns The badge element.
 */
export function RoleChip({ role, compact = false, className }: RoleChipProps) {
  const meta = ROLE_META[role];
  return (
    <Badge
      tone={meta.tone}
      className={cn(styles.chip, compact && styles.compact, className)}
      aria-label={`Role: ${meta.label}`}
      title={`${meta.label} · rank ${meta.rank}`}
    >
      <span className={styles.dot} aria-hidden="true" />
      {meta.label}
    </Badge>
  );
}
