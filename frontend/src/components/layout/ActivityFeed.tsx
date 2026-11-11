/**
 * Live activity feed driven by the activity store.
 */

import { useMemo } from "react";
import { Flag, Pause, Play, RefreshCw, TriangleAlert } from "lucide-react";
import { cn, formatRelativeTime } from "../../lib/utils";
import { useActivityStore, useFilteredActivity } from "../../stores/activityStore";
import type { ActivityEvent, EventKind } from "../../types";
import { Badge, Button, EmptyState, IconButton, Skeleton } from "../ui";
import styles from "./ActivityFeed.module.css";

const KIND_TONES: Record<EventKind, "accent" | "success" | "warning" | "danger" | "info" | "neutral"> = {
  "solve.created": "success",
  "solve.removed": "warning",
  "challenge.created": "accent",
  "challenge.updated": "info",
  "challenge.deleted": "danger",
  "member.updated": "neutral",
  "team.updated": "neutral",
  "presence.changed": "info",
  heartbeat: "neutral",
};

const KIND_LABELS: Record<EventKind, string> = {
  "solve.created": "Solve recorded",
  "solve.removed": "Solve withdrawn",
  "challenge.created": "Challenge created",
  "challenge.updated": "Challenge updated",
  "challenge.deleted": "Challenge deleted",
  "member.updated": "Member updated",
  "team.updated": "Team updated",
  "presence.changed": "Presence changed",
  heartbeat: "Heartbeat",
};

/**
 * Describe an event in a human readable way.
 *
 * @param event - The event to describe.
 * @returns The description.
 */
export function describeEvent(event: ActivityEvent): string {
  const payload = event.payload as Record<string, unknown>;
  const title = typeof payload.title === "string" ? payload.title : undefined;
  const handle = typeof payload.handle === "string" ? payload.handle : undefined;
  const points = typeof payload.points === "number" ? payload.points : undefined;

  if (event.kind === "solve.created") {
    const parts = [title ? `“${title}”` : "a challenge"];
    if (handle) parts.push(`by ${handle}`);
    if (points !== undefined) parts.push(`for ${points} points`);
    return parts.join(" ");
  }
  if (event.kind === "challenge.created" && title) return `“${title}”`;
  if (event.kind === "member.updated" && handle) return `${handle}`;
  return KIND_LABELS[event.kind];
}

/** Props accepted by {@link ActivityFeed}. */
export interface ActivityFeedProps {
  /** The maximum number of events rendered. */
  limit?: number;
  /** Render the feed while the data is loading. */
  loading?: boolean;
  /** Additional class applied to the container. */
  className?: string;
}

/**
 * Render the live activity feed.
 *
 * @param props - The component props.
 * @returns The feed element.
 */
export function ActivityFeed({ limit = 12, loading = false, className }: ActivityFeedProps) {
  const events = useFilteredActivity();
  const paused = useActivityStore((state) => state.paused);
  const togglePaused = useActivityStore((state) => state.togglePaused);
  const clear = useActivityStore((state) => state.clear);

  const visible = useMemo(() => events.slice(0, limit), [events, limit]);

  if (loading) {
    return (
      <div className={cn(styles.feed, className)}>
        <Skeleton height={44} />
        <Skeleton height={44} />
        <Skeleton height={44} />
      </div>
    );
  }

  if (visible.length === 0) {
    return (
      <div className={cn(styles.feed, className)}>
        <EmptyState
          icon={<TriangleAlert size={20} />}
          title="No activity yet"
          description="Solves, challenges and member updates will appear here in real time."
        />
      </div>
    );
  }

  return (
    <div className={cn(styles.feed, className)}>
      <div className={styles.toolbar}>
        <span className={styles.count}>{visible.length} events</span>
        <div className={styles.actions}>
          <Button
            variant="ghost"
            size="sm"
            icon={paused ? <Play size={13} /> : <Pause size={13} />}
            onClick={togglePaused}
          >
            {paused ? "Resume" : "Pause"}
          </Button>
          <IconButton icon={<RefreshCw size={14} />} label="Clear the feed" onClick={clear} />
        </div>
      </div>

      <ol className={styles.list}>
        {visible.map((event) => (
          <li key={event.id} className={styles.item}>
            <span className={cn(styles.icon, styles[`icon-${event.kind.replace(".", "-")}`])} aria-hidden="true">
              <Flag size={13} />
            </span>
            <div className={styles.body}>
              <p className={styles.title}>{describeEvent(event)}</p>
              <p className={styles.meta}>
                <Badge tone={KIND_TONES[event.kind]}>{KIND_LABELS[event.kind]}</Badge>
                <time dateTime={event.occurred_at}>{formatRelativeTime(event.occurred_at)}</time>
              </p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
