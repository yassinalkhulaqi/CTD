/**
 * Compact achievement leaderboard rendered beside the badge gallery.
 */

import { Crown, Medal, Trophy } from "lucide-react";
import { cn } from "../../../lib/utils";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  Skeleton,
} from "../../../components/ui";
import type { LeaderboardEntry } from "../types";
import styles from "./LeaderboardPanel.module.css";

/** Props accepted by {@link LeaderboardPanel}. */
export interface LeaderboardPanelProps {
  /** Leaderboard rows. */
  entries: LeaderboardEntry[] | undefined;
  /** Whether data is loading. */
  loading?: boolean;
  /** Member identifier to highlight. */
  highlightedMemberId?: string | null;
  /** Additional class name. */
  className?: string;
}

/**
 * Render the achievement leaderboard.
 *
 * @param props - The component props.
 * @returns The leaderboard card.
 */
export function LeaderboardPanel({
  entries,
  loading = false,
  highlightedMemberId,
  className,
}: LeaderboardPanelProps) {
  return (
    <Card className={cn(styles.panel, className)} as="section" bare>
      <CardHeader>
        <CardTitle level={3}>Hall of fame</CardTitle>
        <CardDescription>Ranked by achievement points</CardDescription>
      </CardHeader>
      <div className={styles.body}>
        {loading ? (
          <div className={styles.skeletons} aria-hidden="true">
            {[0, 1, 2, 3].map((index) => (
              <Skeleton key={index} height={42} />
            ))}
          </div>
        ) : !entries || entries.length === 0 ? (
          <EmptyState
            title="No awards yet"
            description="Evaluate member metrics to fill the leaderboard."
            icon={<Trophy size={18} />}
          />
        ) : (
          <ol className={styles.list}>
            {entries.map((entry) => (
              <li
                key={entry.member_id}
                className={cn(
                  styles.row,
                  entry.member_id === highlightedMemberId && styles.highlighted,
                  entry.rank === 1 && styles.first,
                )}
              >
                <span className={styles.rank} aria-label={`Rank ${entry.rank}`}>
                  {entry.rank === 1 ? (
                    <Crown size={16} aria-hidden="true" />
                  ) : entry.rank <= 3 ? (
                    <Medal size={15} aria-hidden="true" />
                  ) : (
                    `#${entry.rank}`
                  )}
                </span>
                <span className={styles.identity}>
                  <span className={styles.name}>{entry.label}</span>
                  <span className={styles.meta}>
                    {entry.awards} badge{entry.awards === 1 ? "" : "s"}
                  </span>
                </span>
                <span className={styles.score}>
                  <span className={styles.points}>{entry.points}</span>
                  <span className={styles.rarity}>{entry.rarity} rarity</span>
                </span>
              </li>
            ))}
          </ol>
        )}
      </div>
    </Card>
  );
}
