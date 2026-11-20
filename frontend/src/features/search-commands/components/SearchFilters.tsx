/** Result-kind and result-count controls for the search page. */

import { SlidersHorizontal } from "lucide-react";
import { KIND_OPTIONS, type SearchKind, type SearchStats } from "../types";
import styles from "./SearchFilters.module.css";

/** Props accepted by {@link SearchFilters}. */
export interface SearchFiltersProps {
  /** Currently selected kinds. */
  kinds: SearchKind[];
  /** Invoked when a kind chip is activated. */
  onToggle: (kind: SearchKind) => void;
  /** Invoked when all filters should be cleared. */
  onClear: () => void;
  /** Maximum number of results requested. */
  limit: number;
  /** Invoked when the result limit changes. */
  onLimitChange: (limit: number) => void;
  /** Optional index counters used for chip badges. */
  stats?: SearchStats | null;
}

/**
 * Render the filter bar.
 *
 * @param props - The component props.
 * @returns The filter element.
 */
export function SearchFilters({
  kinds,
  onToggle,
  onClear,
  limit,
  onLimitChange,
  stats,
}: SearchFiltersProps) {
  return (
    <div className={styles.filters} role="group" aria-label="Search filters">
      <span className={styles.lead} aria-hidden="true">
        <SlidersHorizontal size={15} />
      </span>
      <div className={styles.chips}>
        {KIND_OPTIONS.map((option) => {
          const active = kinds.includes(option.value);
          const count = stats?.documents_by_kind[option.value];
          return (
            <button
              type="button"
              key={option.value}
              className={active ? styles.chipActive : styles.chip}
              aria-pressed={active}
              onClick={() => onToggle(option.value)}
              data-kind={option.value}
            >
              <span className={styles.dot} data-accent={option.accent} />
              {option.label}
              {count !== undefined ? (
                <span className={styles.count}>{count}</span>
              ) : null}
            </button>
          );
        })}
        {kinds.length > 0 ? (
          <button type="button" className={styles.clear} onClick={onClear}>
            Clear
          </button>
        ) : null}
      </div>
      <label className={styles.limit}>
        <span>Show</span>
        <select
          value={limit}
          onChange={(event) => onLimitChange(Number(event.target.value))}
          aria-label="Results per search"
        >
          <option value={10}>10</option>
          <option value={20}>20</option>
          <option value={50}>50</option>
        </select>
      </label>
    </div>
  );
}
