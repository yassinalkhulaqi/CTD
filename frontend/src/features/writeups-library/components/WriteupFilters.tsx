/** Filter bar for the magazine library grid. */

import { Search, SlidersHorizontal, X } from "lucide-react";
import { Button, Input, Select } from "../../../components/ui";
import { cn } from "../../../lib/utils";
import {
  CATEGORIES,
  CATEGORY_LABELS,
  DEFAULT_FILTERS,
  type LibraryFilters,
  type SortKey,
  type WriteupCategory,
  type WriteupStatus,
} from "../types";
import styles from "./WriteupFilters.module.css";

/** Props accepted by {@link WriteupFilters}. */
export interface WriteupFiltersProps {
  /** Currently active filters. */
  filters: LibraryFilters;
  /** Called with the complete next filter state. */
  onChange: (filters: LibraryFilters) => void;
  /** Tags available in the library. */
  tags: { tag: string; count: number }[];
  /** Number of results after filtering. */
  resultCount: number;
}

const STATUSES: Array<WriteupStatus | "all"> = [
  "published",
  "review",
  "draft",
  "all",
];
const STATUS_LABELS: Record<WriteupStatus | "all", string> = {
  published: "Published",
  review: "In review",
  draft: "Drafts",
  all: "All",
};
const SORTS: SortKey[] = ["date", "rating", "views", "title"];
const SORT_LABELS: Record<SortKey, string> = {
  date: "Newest first",
  rating: "Highest rated",
  views: "Most viewed",
  title: "Title A–Z",
};

/**
 * Render search, category, status and sorting controls.
 *
 * @param props - The component props.
 * @returns The filter bar.
 */
export function WriteupFilters({
  filters,
  onChange,
  tags,
  resultCount,
}: WriteupFiltersProps) {
  const patch = (next: Partial<LibraryFilters>) =>
    onChange({ ...filters, ...next });
  const isDefault =
    filters.status === DEFAULT_FILTERS.status &&
    filters.category === DEFAULT_FILTERS.category &&
    filters.sort === DEFAULT_FILTERS.sort &&
    !filters.search &&
    !filters.tag;

  return (
    <section className={styles.bar} aria-label="Library filters">
      <div className={styles.mainRow}>
        <div className={styles.search}>
          <Input
            label="Search library"
            hideLabel
            type="search"
            placeholder="Search titles, summaries and tags…"
            value={filters.search}
            icon={<Search size={16} />}
            onChange={(event) => patch({ search: event.target.value })}
          />
        </div>
        <div className={styles.category}>
          <Select
            label="Category"
            hideLabel
            value={filters.category}
            onChange={(event) =>
              patch({ category: event.target.value as WriteupCategory | "all" })
            }
            options={[
              { value: "all", label: "All categories" },
              ...CATEGORIES.map((item) => ({
                value: item,
                label: CATEGORY_LABELS[item],
              })),
            ]}
          />
        </div>
        <div className={styles.sort}>
          <Select
            label="Sort by"
            hideLabel
            value={filters.sort}
            onChange={(event) => patch({ sort: event.target.value as SortKey })}
            options={SORTS.map((item) => ({
              value: item,
              label: SORT_LABELS[item],
            }))}
          />
        </div>
      </div>

      <div className={styles.bottomRow}>
        <div
          className={styles.statuses}
          role="group"
          aria-label="Publication status"
        >
          {STATUSES.map((status) => (
            <button
              key={status}
              type="button"
              className={cn(
                styles.status,
                filters.status === status && styles.statusActive,
              )}
              aria-pressed={filters.status === status}
              onClick={() => patch({ status })}
            >
              {STATUS_LABELS[status]}
            </button>
          ))}
        </div>
        <span className={styles.count} aria-live="polite">
          {resultCount} writeup{resultCount === 1 ? "" : "s"}
        </span>
        <Button
          variant="ghost"
          size="sm"
          icon={<X size={14} />}
          disabled={isDefault}
          onClick={() => onChange({ ...DEFAULT_FILTERS })}
        >
          Reset
        </Button>
      </div>

      {tags.length > 0 ? (
        <div className={styles.tagRow} role="group" aria-label="Filter by tag">
          <span className={styles.tagIcon} aria-hidden="true">
            <SlidersHorizontal size={14} />
          </span>
          {tags.slice(0, 12).map(({ tag, count }) => (
            <button
              key={tag}
              type="button"
              className={cn(
                styles.tag,
                filters.tag === tag && styles.tagActive,
              )}
              aria-pressed={filters.tag === tag}
              onClick={() => patch({ tag: filters.tag === tag ? "" : tag })}
            >
              #{tag} <span>{count}</span>
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}
