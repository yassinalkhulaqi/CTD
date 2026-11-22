/**
 * Tier, criterion and search controls for the badge gallery.
 */

import { Search } from "lucide-react";
import { cn } from "../../../lib/utils";
import {
  CRITERIA_ORDER,
  TIER_ORDER,
  tierColor,
  type BadgeTier,
  type CriteriaKind,
} from "../types";
import styles from "./TierFilter.module.css";

/** Props accepted by {@link TierFilter}. */
export interface TierFilterProps {
  /** Currently selected tier filter. */
  tier: BadgeTier | "all";
  /** Currently selected criterion filter. */
  kind: CriteriaKind | "all";
  /** Current search query. */
  query: string;
  /** Number of badges in each tier. */
  counts?: Partial<Record<BadgeTier | "all", number>>;
  /** Called when the tier filter changes. */
  onTierChange: (tier: BadgeTier | "all") => void;
  /** Called when the criterion filter changes. */
  onKindChange: (kind: CriteriaKind | "all") => void;
  /** Called when the search query changes. */
  onQueryChange: (query: string) => void;
  /** Additional class name. */
  className?: string;
}

/**
 * Render the gallery filter bar.
 *
 * @param props - The component props.
 * @returns The filter element.
 */
export function TierFilter({
  tier,
  kind,
  query,
  counts,
  onTierChange,
  onKindChange,
  onQueryChange,
  className,
}: TierFilterProps) {
  const options: Array<BadgeTier | "all"> = ["all", ...TIER_ORDER];

  return (
    <div className={cn(styles.filter, className)}>
      <div
        className={styles.tiers}
        role="group"
        aria-label="Filter badges by tier"
      >
        {options.map((option) => {
          const active = tier === option;
          return (
            <button
              key={option}
              type="button"
              className={cn(styles.tier, active && styles.active)}
              style={
                option === "all" ? undefined : { color: tierColor(option) }
              }
              aria-pressed={active}
              onClick={() => onTierChange(option)}
            >
              <span>{option === "all" ? "All tiers" : option}</span>
              {counts?.[option] !== undefined ? (
                <span className={styles.count}>{counts[option]}</span>
              ) : null}
            </button>
          );
        })}
      </div>

      <div className={styles.controls}>
        <label className={styles.search}>
          <Search size={15} aria-hidden="true" />
          <span className={styles.srOnly}>Search badges</span>
          <input
            type="search"
            value={query}
            placeholder="Search badges"
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </label>
        <label className={styles.selectWrap}>
          <span className={styles.srOnly}>Filter by criterion</span>
          <select
            value={kind}
            onChange={(event) =>
              onKindChange(event.target.value as CriteriaKind | "all")
            }
          >
            <option value="all">All criteria</option>
            {CRITERIA_ORDER.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
      </div>
    </div>
  );
}
