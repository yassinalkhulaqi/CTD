/** Headline statistics strip for the event catalogue. */

import {
  CalendarRange,
  ClipboardCheck,
  Hourglass,
  UsersRound,
} from "lucide-react";
import { StatCard } from "../../../components/ui";
import { aggregateStats } from "../utils";
import type { EventStats } from "../types";
import styles from "./EventStats.module.css";

/** Props accepted by {@link EventStatsView}. */
export interface EventStatsViewProps {
  stats: EventStats[];
  loading?: boolean;
}

/**
 * Render the aggregate figures of every loaded event.
 *
 * @param props - The component props.
 * @returns The statistics strip.
 */
export function EventStatsView({
  stats,
  loading = false,
}: EventStatsViewProps) {
  const totals = aggregateStats(stats);
  return (
    <section className={styles.strip} aria-label="Event statistics">
      <StatCard
        label="Events"
        value={totals.events}
        meta="in view"
        icon={<CalendarRange size={17} />}
        accent="var(--accent-base)"
        loading={loading}
      />
      <StatCard
        label="Confirmed"
        value={totals.confirmed}
        meta="teams registered"
        icon={<ClipboardCheck size={17} />}
        accent="var(--success-base)"
        loading={loading}
      />
      <StatCard
        label="Waitlisted"
        value={totals.waitlisted}
        meta="awaiting a slot"
        icon={<Hourglass size={17} />}
        accent="var(--warning-base)"
        loading={loading}
      />
      <StatCard
        label="Fill rate"
        value={`${totals.fill}%`}
        meta="of available capacity"
        icon={<UsersRound size={17} />}
        accent="var(--info-base)"
        loading={loading}
      />
    </section>
  );
}
