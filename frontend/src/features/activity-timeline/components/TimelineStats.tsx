/**
 * Compact statistics strip shown above the timeline.
 */

import { Activity, Flame, Radio, Users } from "lucide-react";
import { Badge } from "../../../components/ui";
import type { TimelineStats } from "../types";
import styles from "./TimelineStats.module.css";

/** Props accepted by {@link TimelineStatsView}. */
export interface TimelineStatsProps {
  stats: TimelineStats | null;
}

/**
 * Render the headline timeline counters and a per-kind distribution.
 *
 * @param props - The aggregated statistics.
 * @returns The stats strip element.
 */
export function TimelineStatsView({ stats }: TimelineStatsProps) {
  const peak = stats ? Math.max(1, ...Object.values(stats.by_kind)) : 1;
  return (
    <section className={styles.strip} aria-label="Timeline statistics">
      <div className={styles.metric}>
        <Activity size={16} aria-hidden="true" />
        <span className={styles.value}>{stats?.total ?? 0}</span>
        <span className={styles.caption}>events</span>
      </div>
      <div className={styles.metric}>
        <Flame size={16} aria-hidden="true" />
        <span className={styles.value}>{stats?.critical_count ?? 0}</span>
        <span className={styles.caption}>critical</span>
      </div>
      <div className={styles.metric}>
        <Users size={16} aria-hidden="true" />
        <span className={styles.value}>{stats?.unique_actors ?? 0}</span>
        <span className={styles.caption}>actors</span>
      </div>
      <div className={styles.metric}>
        <Radio size={16} aria-hidden="true" />
        <span className={styles.value}>{stats?.average_per_hour ?? 0}</span>
        <span className={styles.caption}>per active hour</span>
      </div>
      <div className={styles.distribution}>
        {stats && stats.top_kinds.length > 0 ? (
          stats.top_kinds.map(([kind, count]) => (
            <div key={kind} className={styles.barRow}>
              <span className={styles.barLabel}>{kind}</span>
              <span className={styles.barTrack}>
                <span
                  className={styles.barFill}
                  style={{ width: `${Math.round((count / peak) * 100)}%` }}
                />
              </span>
              <span className={styles.barCount}>{count}</span>
            </div>
          ))
        ) : (
          <Badge tone="neutral">No activity recorded</Badge>
        )}
      </div>
    </section>
  );
}
