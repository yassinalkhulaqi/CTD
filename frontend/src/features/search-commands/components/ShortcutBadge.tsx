/** Render a keyboard shortcut as a row of key caps. */

import { formatShortcut } from "../searchUtils";
import styles from "./ShortcutBadge.module.css";

/** Props accepted by {@link ShortcutBadge}. */
export interface ShortcutBadgeProps {
  /** The shortcut, for example `Mod+K` or `G C`. */
  shortcut: string;
  /** Hide the badge when no shortcut is available. */
  hideWhenEmpty?: boolean;
}

/**
 * Render a compact shortcut badge.
 *
 * @param props - The component props.
 * @returns The badge element, or `null` when empty and hidden.
 */
export function ShortcutBadge({
  shortcut,
  hideWhenEmpty = true,
}: ShortcutBadgeProps) {
  const formatted = formatShortcut(shortcut);
  if (!formatted && hideWhenEmpty) return null;
  const keys = formatted.split(/\s+/).filter(Boolean);
  return (
    <span className={styles.badge} aria-label={`Shortcut ${formatted}`}>
      {keys.map((key, index) => (
        <kbd className={styles.key} key={`${key}-${index}`}>
          {key}
        </kbd>
      ))}
    </span>
  );
}
