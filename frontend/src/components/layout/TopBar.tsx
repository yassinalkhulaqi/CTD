/**
 * Top bar with the search field, the filters and the view preferences.
 */

import { Filter, Search, X } from "lucide-react";
import { cn } from "../../lib/utils";
import { useDashboardStore } from "../../stores/dashboardStore";
import { usePreferencesStore } from "../../stores/preferencesStore";
import type { ChallengeCategory, ChallengeStatus } from "../../types";
import { Badge, Button, IconButton, Input, SegmentedControl } from "../ui";
import styles from "./TopBar.module.css";

const CATEGORY_OPTIONS: Array<{ value: ChallengeCategory | "all"; label: string }> = [
  { value: "all", label: "All" },
  { value: "web", label: "Web" },
  { value: "crypto", label: "Crypto" },
  { value: "pwn", label: "Binary" },
  { value: "reverse", label: "Reverse" },
  { value: "forensics", label: "Forensics" },
  { value: "osint", label: "OSINT" },
  { value: "misc", label: "Misc" },
];

const STATUS_OPTIONS: Array<{ value: ChallengeStatus | "all"; label: string }> = [
  { value: "all", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "active", label: "Active" },
  { value: "solved", label: "Solved" },
  { value: "locked", label: "Locked" },
];

const DENSITY_OPTIONS = [
  { value: "comfortable", label: "Comfortable" },
  { value: "compact", label: "Compact" },
] as const;

/** Props accepted by {@link TopBar}. */
export interface TopBarProps {
  /** The title displayed next to the search field. */
  title: string;
  /** Optional class applied to the container. */
  className?: string;
}

/**
 * Render the dashboard top bar.
 *
 * @param props - The component props.
 * @returns The top bar element.
 */
export function TopBar({ title, className }: TopBarProps) {
  const searchQuery = useDashboardStore((state) => state.searchQuery);
  const setSearchQuery = useDashboardStore((state) => state.setSearchQuery);
  const categoryFilter = useDashboardStore((state) => state.categoryFilter);
  const setCategoryFilter = useDashboardStore((state) => state.setCategoryFilter);
  const statusFilter = useDashboardStore((state) => state.statusFilter);
  const setStatusFilter = useDashboardStore((state) => state.setStatusFilter);
  const resetFilters = useDashboardStore((state) => state.resetFilters);

  const density = usePreferencesStore((state) => state.density);
  const setDensity = usePreferencesStore((state) => state.setDensity);

  const hasFilters =
    categoryFilter !== "all" || statusFilter !== "all" || searchQuery.trim().length > 0;

  return (
    <header className={cn(styles.topBar, className)}>
      <div className={styles.heading}>
        <h1 className={styles.title}>{title}</h1>
        {hasFilters ? (
          <Badge tone="accent" dot>
            Filtered
          </Badge>
        ) : null}
      </div>

      <div className={styles.controls}>
        <Input
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder="Search challenges…"
          icon={<Search size={14} />}
          hideLabel
          aria-label="Search challenges"
          className={styles.search}
        />

        <SegmentedControl
          options={CATEGORY_OPTIONS}
          value={categoryFilter}
          onValueChange={setCategoryFilter}
          label="Category filter"
        />

        <SegmentedControl
          options={STATUS_OPTIONS}
          value={statusFilter}
          onValueChange={setStatusFilter}
          label="Status filter"
        />

        <SegmentedControl
          options={DENSITY_OPTIONS}
          value={density}
          onValueChange={setDensity}
          label="Information density"
        />

        {hasFilters ? (
          <Button variant="ghost" size="sm" icon={<X size={13} />} onClick={resetFilters}>
            Clear
          </Button>
        ) : (
          <IconButton icon={<Filter size={15} />} label="No active filter" disabled />
        )}
      </div>
    </header>
  );
}
