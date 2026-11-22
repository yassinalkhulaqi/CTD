/**
 * Filter bar for narrowing the visible notes by tag.
 */

import { Tag, X } from "lucide-react";
import { cn } from "../../../lib/utils";
import styles from "./TagFilter.module.css";

/** Props accepted by {@link TagFilter}. */
export interface TagFilterProps {
  /** Every tag available in the workspace. */
  tags: string[];
  /** The currently active tags. */
  activeTags: string[];
  /** Called when a tag chip is toggled. */
  onToggle: (tag: string) => void;
  /** Called when all filters are cleared. */
  onClear: () => void;
}

/**
 * Render toggleable tag chips.
 *
 * @param props - The component props.
 * @returns The tag filter element.
 */
export function TagFilter({
  tags,
  activeTags,
  onToggle,
  onClear,
}: TagFilterProps) {
  if (tags.length === 0) return null;
  return (
    <div
      className={styles.filter}
      role="group"
      aria-label="Filter notes by tag"
    >
      <span className={styles.label}>
        <Tag size={12} aria-hidden="true" /> Tags
      </span>
      <div className={styles.chips}>
        {tags.map((tag) => (
          <button
            key={tag}
            type="button"
            className={cn(
              styles.chip,
              activeTags.includes(tag) && styles.chipActive,
            )}
            aria-pressed={activeTags.includes(tag)}
            onClick={() => onToggle(tag)}
          >
            #{tag}
          </button>
        ))}
      </div>
      {activeTags.length > 0 ? (
        <button type="button" className={styles.clear} onClick={onClear}>
          <X size={12} aria-hidden="true" /> Clear
        </button>
      ) : null}
    </div>
  );
}
