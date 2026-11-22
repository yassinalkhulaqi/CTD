/**
 * Top bar with the search field, the filters and the view preferences.
 */

import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, Filter, Menu, Search, X } from "lucide-react";
import { cn } from "../../lib/utils";
import { useDashboardStore } from "../../stores/dashboardStore";
import { usePreferencesStore } from "../../stores/preferencesStore";
import { useActivityStore } from "../../stores/activityStore";
import { useAuth } from "../../features/auth/useAuth";
import type { ChallengeCategory, ChallengeStatus } from "../../types";
import {
  Avatar,
  Badge,
  Button,
  Input,
  Popover,
  SegmentedControl,
  StatusDot,
  ThemeToggle,
} from "../ui";
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
  /** A short line describing the current view. */
  subtitle?: string;
  /** Called when the mobile navigation should open. */
  onOpenNavigation?: () => void;
  /** Optional class applied to the container. */
  className?: string;
}

/**
 * Render the dashboard top bar.
 *
 * @param props - The component props.
 * @returns The top bar element.
 */
export function TopBar({ title, subtitle, onOpenNavigation, className }: TopBarProps) {
  const navigate = useNavigate();
  const searchQuery = useDashboardStore((state) => state.searchQuery);
  const setSearchQuery = useDashboardStore((state) => state.setSearchQuery);
  const categoryFilter = useDashboardStore((state) => state.categoryFilter);
  const setCategoryFilter = useDashboardStore((state) => state.setCategoryFilter);
  const statusFilter = useDashboardStore((state) => state.statusFilter);
  const setStatusFilter = useDashboardStore((state) => state.setStatusFilter);
  const resetFilters = useDashboardStore((state) => state.resetFilters);

  const density = usePreferencesStore((state) => state.density);
  const setDensity = usePreferencesStore((state) => state.setDensity);

  const eventCount = useActivityStore((state) => state.events.length);
  const { user, status } = useAuth();

  const [filtersOpen, setFiltersOpen] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);

  const activeFilterCount =
    (categoryFilter !== "all" ? 1 : 0) + (statusFilter !== "all" ? 1 : 0);
  const hasFilters = activeFilterCount > 0 || searchQuery.trim().length > 0;

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const typing =
        target?.tagName === "INPUT" || target?.tagName === "TEXTAREA" || target?.isContentEditable;
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchRef.current?.focus();
      } else if (event.key === "/" && !typing) {
        event.preventDefault();
        searchRef.current?.focus();
      }
      if (event.key === "Escape") setFiltersOpen(false);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <header className={cn(styles.topBar, className)}>
      <div className={styles.heading}>
        {onOpenNavigation ? (
          <button
            type="button"
            className={styles.menuButton}
            onClick={onOpenNavigation}
            aria-label="Open navigation"
          >
            <Menu size={18} aria-hidden="true" />
          </button>
        ) : null}
        <div className={styles.headingText}>
          <h1 className={styles.title}>{title}</h1>
          {subtitle ? <p className={styles.subtitle}>{subtitle}</p> : null}
        </div>
        {hasFilters ? (
          <Badge tone="accent" dot size="sm">
            Filtered
          </Badge>
        ) : null}
      </div>

      <div className={styles.controls}>
        <div className={styles.search}>
          <Input
            ref={searchRef}
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Search challenges…"
            icon={<Search size={14} />}
            hideLabel
            aria-label="Search challenges"
            trailing={<kbd className={styles.kbd}>⌘K</kbd>}
          />
        </div>

        <Popover
          open={filtersOpen}
          align="end"
          onClose={() => setFiltersOpen(false)}
          trigger={
            <Button
              variant={activeFilterCount > 0 ? "secondary" : "ghost"}
              size="sm"
              icon={<Filter size={14} />}
              onClick={() => setFiltersOpen((open) => !open)}
              aria-haspopup="dialog"
            >
              Filters
              {activeFilterCount > 0 ? <span className={styles.filterCount}>{activeFilterCount}</span> : null}
            </Button>
          }
        >
          <div className={styles.filterPanel}>
            <div className={styles.filterGroup}>
              <p className={styles.filterLabel}>Category</p>
              <SegmentedControl
                options={CATEGORY_OPTIONS}
                value={categoryFilter}
                onValueChange={setCategoryFilter}
                label="Category filter"
                className={styles.filterSegments}
              />
            </div>
            <div className={styles.filterGroup}>
              <p className={styles.filterLabel}>Status</p>
              <SegmentedControl
                options={STATUS_OPTIONS}
                value={statusFilter}
                onValueChange={setStatusFilter}
                label="Status filter"
                className={styles.filterSegments}
              />
            </div>
            <div className={styles.filterGroup}>
              <p className={styles.filterLabel}>Density</p>
              <SegmentedControl
                options={DENSITY_OPTIONS}
                value={density}
                onValueChange={setDensity}
                label="Information density"
                className={styles.filterSegments}
              />
            </div>
            <div className={styles.filterFooter}>
              <Button
                variant="ghost"
                size="sm"
                icon={<X size={13} />}
                onClick={resetFilters}
                disabled={!hasFilters}
              >
                Clear filters
              </Button>
            </div>
          </div>
        </Popover>

        <button
          type="button"
          className={styles.bell}
          onClick={() => navigate("/activity")}
          aria-label={`Activity feed${eventCount > 0 ? `, ${eventCount} events` : ""}`}
        >
          <Bell size={16} aria-hidden="true" />
          {eventCount > 0 ? <span className={styles.bellDot} aria-hidden="true" /> : null}
        </button>

        <ThemeToggle className={styles.theme} />

        <div className={styles.account}>
          <Avatar name={user?.username ?? "Open mode"} size="sm" presence={status === "authenticated" ? "online" : "away"} />
          <div className={styles.accountText}>
            <span className={styles.accountName}>{user?.username ?? "Open mode"}</span>
            <span className={styles.accountMeta}>
              <StatusDot tone={status === "authenticated" ? "success" : "warning"} />
              {user?.role ?? "local session"}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
