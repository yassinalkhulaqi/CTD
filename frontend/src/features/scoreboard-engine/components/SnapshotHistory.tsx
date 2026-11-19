/**
 * Snapshot history timeline with an SVG sparkline.
 */

import { History } from "lucide-react";
import { Badge, Card, EmptyState, Skeleton } from "../../../components/ui";
import { cn } from "../../../lib/utils";
import { formatScore, sparklinePoints } from "../scoring";
import type { ScoreSnapshot } from "../types";
import styles from "./SnapshotHistory.module.css";

/** Props accepted by {@link SnapshotHistory}. */
export interface SnapshotHistoryProps {
  /** Snapshots, newest first. */
  snapshots: ScoreSnapshot[];
  /** Show loading placeholders instead of content. */
  loading?: boolean;
  /** Additional class applied to the container. */
  className?: string;
}

const WIDTH = 260;
const HEIGHT = 64;

/**
 * Render the snapshot sparkline and timeline.
 *
 * @param props - The component props.
 * @returns The history card.
 */
export function SnapshotHistory({
  snapshots,
  loading = false,
  className,
}: SnapshotHistoryProps) {
  if (loading) {
    return (
      <Card as="section" className={cn(styles.card, className)}>
        <Skeleton height={180} />
      </Card>
    );
  }

  if (snapshots.length === 0) {
    return (
      <Card as="section" className={cn(styles.card, className)}>
        <h2 className={styles.title}>Snapshot history</h2>
        <EmptyState
          title="No snapshots recorded"
          description="Capture a snapshot to start tracking rank movement over time."
          icon={<History size={22} />}
        />
      </Card>
    );
  }

  const series = [...snapshots].reverse().map((item) => item.points);
  const points = sparklinePoints(series, WIDTH, HEIGHT);
  const delta = series.length > 1 ? series[series.length - 1] - series[0] : 0;

  return (
    <Card as="section" className={cn(styles.card, className)}>
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>Snapshot history</h2>
          <p className={styles.subtitle}>
            {snapshots.length} recorded point{snapshots.length === 1 ? "" : "s"}
          </p>
        </div>
        <Badge tone={delta >= 0 ? "success" : "danger"}>
          {delta >= 0 ? "+" : ""}
          {formatScore(delta)} pts
        </Badge>
      </div>

      <svg
        className={styles.sparkline}
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={`Points trend from ${formatScore(series[0])} to ${formatScore(series[series.length - 1])}`}
      >
        <polyline
          className={styles.area}
          points={`0,${HEIGHT} ${points} ${WIDTH},${HEIGHT}`}
        />
        <polyline className={styles.line} points={points} />
      </svg>

      <ol className={styles.timeline}>
        {snapshots.slice(0, 5).map((snapshot) => (
          <li key={snapshot.id} className={styles.item}>
            <span className={styles.marker} aria-hidden="true" />
            <span className={styles.itemRank}>#{snapshot.rank}</span>
            <span className={styles.itemPoints}>
              {formatScore(snapshot.points)} pts
            </span>
            <span className={styles.itemMeta}>
              {snapshot.solves} solves · {snapshot.rule_name}
            </span>
            <time className={styles.time} dateTime={snapshot.recorded_at}>
              {new Date(snapshot.recorded_at).toLocaleDateString()}
            </time>
          </li>
        ))}
      </ol>
    </Card>
  );
}
