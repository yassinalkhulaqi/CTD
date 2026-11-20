/**
 * Virtual-style list that flattens day/hour buckets into display rows.
 */

import { Button } from "../../../components/ui";
import { flattenBuckets } from "../logic";
import type { TimelineBucket } from "../types";
import { GroupHeader } from "./GroupHeader";
import { TimelineItem } from "./TimelineItem";
import styles from "./TimelineList.module.css";

/** Props accepted by {@link TimelineList}. */
export interface TimelineListProps {
  buckets: TimelineBucket[];
  loadingMore?: boolean;
  onDismiss?: (id: string) => void;
  onLoadMore?: () => void;
}

/**
 * Render the grouped timeline with sticky date headers and a vertical spine.
 *
 * @param props - Buckets and pagination callbacks.
 * @returns The list element.
 */
export function TimelineList({
  buckets,
  loadingMore = false,
  onDismiss,
  onLoadMore,
}: TimelineListProps) {
  const rows = flattenBuckets(buckets);
  return (
    <div className={styles.list} role="list" aria-label="Activity timeline">
      {rows.map((row) => {
        if (row.type === "day") {
          return (
            <div key={row.key} role="listitem" className={styles.dayRow}>
              <GroupHeader bucket={row.bucket} />
            </div>
          );
        }
        if (row.type === "hour") {
          return (
            <div key={row.key} role="listitem" className={styles.hourRow}>
              <GroupHeader bucket={row.bucket} compact />
            </div>
          );
        }
        return (
          <div key={row.key} role="listitem" className={styles.eventRow}>
            <TimelineItem cluster={row.cluster} onDismiss={onDismiss} />
          </div>
        );
      })}
      {onLoadMore ? (
        <div className={styles.more}>
          <Button
            variant="secondary"
            loading={loadingMore}
            onClick={onLoadMore}
          >
            Load older activity
          </Button>
        </div>
      ) : null}
    </div>
  );
}
