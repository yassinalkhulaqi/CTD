/**
 * Sticky header for a day or hour bucket.
 */

import { Badge } from "../../../components/ui";
import { cn } from "../../../lib/utils";
import type { TimelineBucket } from "../types";
import styles from "./GroupHeader.module.css";

/** Props accepted by {@link GroupHeader}. */
export interface GroupHeaderProps {
  bucket: TimelineBucket;
  compact?: boolean;
}

/**
 * Render a bucket label with its event count and critical indicator.
 *
 * @param props - The bucket and display mode.
 * @returns The header element.
 */
export function GroupHeader({ bucket, compact = false }: GroupHeaderProps) {
  const Title = compact ? "h3" : "h2";
  return (
    <div
      className={cn(styles.header, compact ? styles.compact : styles.day)}
      data-level={bucket.level}
    >
      <Title className={styles.title}>{bucket.label}</Title>
      <span className={styles.count}>
        {bucket.count} {bucket.count === 1 ? "event" : "events"}
      </span>
      {bucket.critical_count > 0 ? (
        <Badge tone="danger" className={styles.critical}>
          {bucket.critical_count} critical
        </Badge>
      ) : null}
    </div>
  );
}
