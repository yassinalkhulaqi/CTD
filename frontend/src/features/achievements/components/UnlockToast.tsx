/**
 * Celebration toast shown when new badges are unlocked.
 */

import { Sparkles, X } from "lucide-react";
import { cn } from "../../../lib/utils";
import { IconButton } from "../../../components/ui";
import { tierColor, type BadgeView } from "../types";
import { BadgeIcon } from "./BadgeIcon";
import styles from "./UnlockToast.module.css";

/** Props accepted by {@link UnlockToast}. */
export interface UnlockToastProps {
  /** Badges unlocked by the latest evaluation. */
  badges: BadgeView[];
  /** Called when the toast is dismissed. */
  onDismiss: () => void;
  /** Additional class name. */
  className?: string;
}

/**
 * Render a celebration notification for newly unlocked badges.
 *
 * @param props - The component props.
 * @returns The toast element, or `null` when nothing was unlocked.
 */
export function UnlockToast({
  badges,
  onDismiss,
  className,
}: UnlockToastProps) {
  if (badges.length === 0) return null;

  return (
    <div
      className={cn(styles.toast, className)}
      role="status"
      aria-live="polite"
      aria-label={`${badges.length} new badge${badges.length === 1 ? "" : "s"} unlocked`}
    >
      <div className={styles.icon} aria-hidden="true">
        <Sparkles size={20} />
      </div>
      <div className={styles.body}>
        <p className={styles.title}>
          {badges.length === 1
            ? "New badge unlocked!"
            : `${badges.length} badges unlocked!`}
        </p>
        <ul className={styles.list}>
          {badges.slice(0, 3).map((view) => (
            <li key={view.badge.id} className={styles.item}>
              <span style={{ color: tierColor(view.badge.tier) }}>
                <BadgeIcon token={view.display_icon} size={16} />
              </span>
              {view.display_name}
            </li>
          ))}
        </ul>
        {badges.length > 3 ? (
          <p className={styles.more}>+{badges.length - 3} more</p>
        ) : null}
      </div>
      <IconButton
        icon={<X size={15} />}
        label="Dismiss unlock notification"
        onClick={onDismiss}
        size="sm"
      />
    </div>
  );
}
