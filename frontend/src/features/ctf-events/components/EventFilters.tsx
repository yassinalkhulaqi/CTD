/** Filter bar for the event catalogue. */

import { Search } from "lucide-react";
import { Input, Select } from "../../../components/ui";
import type { EventFormat, EventWindow } from "../types";
import styles from "./EventFilters.module.css";

/** The windows offered by the filter bar. */
export const WINDOW_OPTIONS: ReadonlyArray<{
  value: EventWindow;
  label: string;
}> = [
  { value: "all", label: "All" },
  { value: "upcoming", label: "Upcoming" },
  { value: "live", label: "Live" },
  { value: "archived", label: "Archived" },
];

/** Props accepted by {@link EventFilters}. */
export interface EventFiltersProps {
  value: EventWindow;
  format: EventFormat | "all";
  search: string;
  counts: Record<EventWindow, number>;
  onWindowChange: (next: EventWindow) => void;
  onFormatChange: (next: EventFormat | "all") => void;
  onSearchChange: (next: string) => void;
}

/**
 * Render the event catalogue controls.
 *
 * @param props - The component props.
 * @returns The filter bar.
 */
export function EventFilters({
  value,
  format,
  search,
  counts,
  onWindowChange,
  onFormatChange,
  onSearchChange,
}: EventFiltersProps) {
  return (
    <section className={styles.bar} aria-label="Event filters">
      <div
        className={styles.windows}
        role="group"
        aria-label="Filter by status"
      >
        {WINDOW_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={styles.windowButton}
            aria-pressed={value === option.value}
            onClick={() => onWindowChange(option.value)}
          >
            {option.label}
            <span className={styles.count}>{counts[option.value] ?? 0}</span>
          </button>
        ))}
      </div>
      <div className={styles.controls}>
        <Input
          label="Search events"
          hideLabel
          icon={<Search size={15} />}
          placeholder="Search events…"
          value={search}
          onChange={(change) => onSearchChange(change.target.value)}
        />
        <Select
          label="Format"
          hideLabel
          value={format}
          onChange={(change) =>
            onFormatChange(change.target.value as EventFormat | "all")
          }
          options={[
            { value: "all", label: "All formats" },
            { value: "jeopardy", label: "Jeopardy" },
            { value: "attack_defence", label: "Attack / Defence" },
          ]}
        />
      </div>
    </section>
  );
}
