/** Bookmark toggle with optimistic visual state. */

import { Bookmark } from "lucide-react";
import { cn } from "../../../lib/utils";
import styles from "./BookmarkButton.module.css";

/** Props accepted by {@link BookmarkButton}. */
export interface BookmarkButtonProps {
  /** Whether the writeup is currently bookmarked. */
  bookmarked: boolean;
  /** Number of members who bookmarked the writeup. */
  count?: number;
  /** Called when the button is pressed. */
  onToggle: () => void;
  /** Disable interaction while a request is in flight. */
  busy?: boolean;
  /** Compact presentation for dense cards. */
  compact?: boolean;
}

/**
 * Render an accessible bookmark toggle.
 *
 * @param props - The component props.
 * @returns The bookmark button.
 */
export function BookmarkButton({
  bookmarked,
  count,
  onToggle,
  busy = false,
  compact = false,
}: BookmarkButtonProps) {
  return (
    <button
      type="button"
      className={cn(
        styles.button,
        bookmarked && styles.saved,
        compact && styles.compact,
      )}
      aria-pressed={bookmarked}
      aria-label={bookmarked ? "Remove bookmark" : "Bookmark this writeup"}
      title={bookmarked ? "Remove bookmark" : "Save for later"}
      disabled={busy}
      onClick={onToggle}
    >
      <Bookmark size={compact ? 15 : 17} aria-hidden="true" />
      {!compact ? <span>{bookmarked ? "Saved" : "Save"}</span> : null}
      {count !== undefined && count > 0 ? (
        <span className={styles.count} aria-label={`${count} bookmarks`}>
          {count}
        </span>
      ) : null}
    </button>
  );
}
