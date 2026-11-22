/**
 * A single timeline display item backed by a deduplicated event cluster.
 */

import {
  Award,
  FileText,
  Flag,
  Lightbulb,
  Send,
  Settings,
  Target,
  User,
  Users,
  X,
} from "lucide-react";
import type { CSSProperties } from "react";
import { Avatar, Badge } from "../../../components/ui";
import { cn } from "../../../lib/utils";
import { importanceLabel, relativeTime, toneForImportance } from "../logic";
import type { EventCluster } from "../types";
import styles from "./TimelineItem.module.css";

const ICONS = {
  solve: Flag,
  challenge: Target,
  member: User,
  team: Users,
  note: FileText,
  hint: Lightbulb,
  submission: Send,
  achievement: Award,
  system: Settings,
} as const;

/**
 * Extract a compact preview of the structured event payload.
 *
 * @param raw - The JSON payload string.
 * @returns A short key/value summary, or `null` when unavailable.
 */
function payloadSummary(raw: string): string | null {
  try {
    const decoded: unknown = JSON.parse(raw);
    if (decoded === null || typeof decoded !== "object") return null;
    const entries = Object.entries(decoded as Record<string, unknown>).slice(
      0,
      2,
    );
    if (entries.length === 0) return null;
    return entries
      .map(([key, value]) => `${key}: ${String(value)}`)
      .join(" · ");
  } catch {
    return null;
  }
}

/** Props accepted by {@link TimelineItem}. */
export interface TimelineItemProps {
  cluster: EventCluster;
  now?: Date;
  onDismiss?: (id: string) => void;
}

/**
 * Render one activity event with avatar, kind, importance and timestamp.
 *
 * @param props - The cluster and optional callbacks.
 * @returns The list item element.
 */
export function TimelineItem({ cluster, now, onDismiss }: TimelineItemProps) {
  const event = cluster.event;
  const Icon = ICONS[event.kind as keyof typeof ICONS] ?? Settings;
  const detail = payloadSummary(event.payload_json);
  return (
    <article
      className={cn(
        styles.item,
        event.importance === "critical" && styles.critical,
      )}
      style={{ "--kind-color": event.kind_color } as CSSProperties}
      data-kind={event.kind}
    >
      <span className={styles.spine} aria-hidden="true">
        <span className={styles.node}>
          <Icon size={12} aria-hidden="true" />
        </span>
      </span>
      <Avatar name={event.actor_name} size="sm" className={styles.avatar} />
      <div className={styles.content}>
        <div className={styles.top}>
          <span className={styles.actor}>{event.actor_name}</span>
          <span className={styles.kind}>{event.kind_label}</span>
          {detail ? <span className={styles.detail}>{detail}</span> : null}
        </div>
        <p className={styles.summary}>{event.summary}</p>
        <div className={styles.meta}>
          <Badge tone={toneForImportance(event.importance)} dot>
            {importanceLabel(event.importance)}
          </Badge>
          {cluster.is_merged ? (
            <span
              className={styles.merged}
              aria-label={`${cluster.count} similar events`}
            >
              {cluster.count_label} similar
            </span>
          ) : null}
          <time className={styles.time} dateTime={event.occurred_at}>
            {now ? relativeTime(event.occurred_at, now) : event.relative_label}
          </time>
        </div>
      </div>
      {onDismiss ? (
        <button
          type="button"
          className={styles.dismiss}
          aria-label={`Dismiss event ${event.id}`}
          onClick={() => onDismiss(cluster.id)}
        >
          <X size={14} aria-hidden="true" />
        </button>
      ) : null}
    </article>
  );
}
