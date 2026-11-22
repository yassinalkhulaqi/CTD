/**
 * Statistic strip summarising the achievement programme.
 */

import { Award, Coins, Medal, Users } from "lucide-react";
import { StatCard } from "../../../components/ui";
import { cn, formatNumber } from "../../../lib/utils";
import type { AchievementStats } from "../types";
import styles from "./AchievementStats.module.css";

/** Props accepted by {@link AchievementStatsPanel}. */
export interface AchievementStatsPanelProps {
  /** The statistics to render. */
  stats: AchievementStats | undefined;
  /** Whether statistics are still loading. */
  loading?: boolean;
  /** Additional class name. */
  className?: string;
}

/**
 * Render the achievement overview cards.
 *
 * @param props - The component props.
 * @returns The statistics strip.
 */
export function AchievementStatsPanel({
  stats,
  loading = false,
  className,
}: AchievementStatsPanelProps) {
  return (
    <div className={cn(styles.grid, className)} aria-busy={loading}>
      <StatCard
        label="Badges unlocked"
        value={stats ? formatNumber(stats.awards) : "-"}
        meta={stats ? `${stats.badges} in catalogue` : "Loading"}
        icon={<Award size={17} />}
        accent="#f5c451"
        loading={loading}
      />
      <StatCard
        label="Achievement points"
        value={stats ? formatNumber(stats.points) : "-"}
        meta={stats ? `${stats.points_per_member} per member` : "Loading"}
        icon={<Coins size={17} />}
        accent="#a855f7"
        loading={loading}
      />
      <StatCard
        label="Participation"
        value={stats ? `${stats.participation_rate}%` : "-"}
        meta={
          stats
            ? `${stats.members_with_awards} of ${stats.members} members`
            : "Loading"
        }
        icon={<Users size={17} />}
        accent="#38bdf8"
        loading={loading}
      />
      <StatCard
        label="Average rarity"
        value={stats ? `${stats.average_rarity}%` : "-"}
        meta={stats ? `${stats.gold_badges} gold badges` : "Loading"}
        icon={<Medal size={17} />}
        accent="#34d399"
        loading={loading}
      />
    </div>
  );
}
