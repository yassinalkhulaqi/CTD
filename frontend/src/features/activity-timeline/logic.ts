/**
 * Pure helpers for the activity timeline screen.
 *
 * The functions in this module mirror the backend domain rules so the UI can
 * group, rank and summarise events without extra round trips. They are kept
 * free of React and network concerns and are covered by dedicated tests.
 */

import type {
  EventCluster,
  Importance,
  KindOption,
  TimelineBucket,
  TimelineEvent,
  TimelineQuery,
  TimelineRow,
} from "./types";

/** Importance tiers ordered from least to most urgent. */
export const IMPORTANCE_ORDER: Importance[] = [
  "low",
  "normal",
  "high",
  "critical",
];

/** Kind metadata used to build the filter chips and event icons. */
export const KIND_OPTIONS: KindOption[] = [
  { value: "solve", label: "Solves", color: "#34d399" },
  { value: "challenge", label: "Challenges", color: "#38bdf8" },
  { value: "member", label: "Members", color: "#a78bfa" },
  { value: "team", label: "Team", color: "#6366f1" },
  { value: "note", label: "Notes", color: "#fbbf24" },
  { value: "hint", label: "Hints", color: "#f472b6" },
  { value: "submission", label: "Submissions", color: "#fb923c" },
  { value: "achievement", label: "Achievements", color: "#facc15" },
  { value: "system", label: "System", color: "#94a3b8" },
];

/** Default window used when collapsing consecutive identical events. */
export const DEFAULT_DEDUPE_WINDOW = 120;

/** The labels used for each importance tier. */
const IMPORTANCE_LABELS: Record<Importance, string> = {
  low: "Low",
  normal: "Normal",
  high: "High",
  critical: "Critical",
};

/** The semantic badge tone used for each importance tier. */
export const IMPORTANCE_TONES: Record<Importance, string> = {
  low: "neutral",
  normal: "info",
  high: "warning",
  critical: "danger",
};

/**
 * Format an ISO timestamp as a compact relative label.
 *
 * @param iso - The ISO-8601 timestamp.
 * @param now - Optional reference date, useful for deterministic tests.
 * @returns A label such as `just now`, `4h ago`, `yesterday` or `Jan 05`.
 */
export function relativeTime(iso: string, now: Date = new Date()): string {
  const timestamp = Date.parse(iso);
  if (Number.isNaN(timestamp)) return "—";
  const seconds = Math.max(0, (now.getTime() - timestamp) / 1000);
  if (seconds < 45) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${Math.max(1, minutes)}m ago`;
  const hours = Math.floor(seconds / 3600);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(seconds / 86_400);
  if (days === 1) return "yesterday";
  if (days < 7) return `${days}d ago`;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    timeZone: "UTC",
  }).format(timestamp);
}

/**
 * Return the stable day key of a timestamp.
 *
 * @param value - The timestamp.
 * @returns A `YYYY-MM-DD` key.
 */
export function dayKey(value: string | Date): string {
  return toDate(value).toISOString().slice(0, 10);
}

/**
 * Return the stable hour key of a timestamp.
 *
 * @param value - The timestamp.
 * @returns A `YYYY-MM-DDTHH:00` key.
 */
export function hourKey(value: string | Date): string {
  return `${dayKey(value)}T${String(toDate(value).getUTCHours()).padStart(2, "0")}:00`;
}

/**
 * Format the display label of an hour bucket.
 *
 * @param value - A timestamp within the hour.
 * @returns A `HH:00` label.
 */
export function hourLabel(value: string | Date): string {
  return `${String(toDate(value).getUTCHours()).padStart(2, "0")}:00`;
}

/**
 * Format the display label of a day bucket.
 *
 * @param value - A timestamp within the day.
 * @param now - Optional reference date for relative labels.
 * @returns `Today`, `Yesterday` or a weekday/date label.
 */
export function dayLabel(value: string | Date, now: Date = new Date()): string {
  const key = dayKey(value);
  if (key === dayKey(now)) return "Today";
  const yesterday = new Date(now.getTime() - 86_400_000);
  if (key === dayKey(yesterday)) return "Yesterday";
  return new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "2-digit",
    timeZone: "UTC",
  }).format(toDate(value));
}

/**
 * Return the numeric rank of an importance tier.
 *
 * @param importance - The tier.
 * @returns A rank from 0 to 3.
 */
export function importanceRank(importance: Importance): number {
  const index = IMPORTANCE_ORDER.indexOf(importance);
  return index < 0 ? 1 : index;
}

/**
 * Return the human readable label of an importance tier.
 *
 * @param importance - The tier.
 * @returns The display label.
 */
export function importanceLabel(importance: Importance): string {
  return IMPORTANCE_LABELS[importance] ?? "Normal";
}

/**
 * Return the badge tone for an importance tier.
 *
 * @param importance - The tier.
 * @returns A design-system badge tone.
 */
export function toneForImportance(
  importance: Importance,
): "neutral" | "info" | "warning" | "danger" {
  const tone = IMPORTANCE_TONES[importance];
  if (
    tone === "neutral" ||
    tone === "info" ||
    tone === "warning" ||
    tone === "danger"
  ) {
    return tone;
  }
  return "neutral";
}

/**
 * Build a cluster from a representative event.
 *
 * @param event - The event to wrap.
 * @returns A single-item cluster.
 */
export function singleCluster(event: TimelineEvent): EventCluster {
  return {
    id: event.id,
    event,
    count: 1,
    first_at: event.occurred_at,
    last_at: event.occurred_at,
    is_merged: false,
    count_label: "",
    importance_rank: event.importance_rank,
  };
}

/**
 * Collapse consecutive identical events for display.
 *
 * An event is grouped with its predecessor when the kind, actor and summary
 * match and the timestamps are within the configured window. The most
 * important event becomes the representative of the cluster.
 *
 * @param events - Events ordered from newest to oldest.
 * @param windowSeconds - Maximum separation for a merge, in seconds.
 * @returns The deduplicated clusters.
 */
export function clusterEvents(
  events: TimelineEvent[],
  windowSeconds: number = DEFAULT_DEDUPE_WINDOW,
): EventCluster[] {
  const result: EventCluster[] = [];
  for (const event of events) {
    const previous = result[result.length - 1];
    const same =
      previous !== undefined &&
      previous.event.kind === event.kind &&
      previous.event.actor_id === event.actor_id &&
      previous.event.summary === event.summary;
    const gap = previous
      ? Math.abs(
          Date.parse(previous.first_at) - Date.parse(event.occurred_at),
        ) / 1000
      : Number.POSITIVE_INFINITY;
    if (previous && same && gap <= windowSeconds) {
      const winner =
        event.importance_rank > previous.event.importance_rank
          ? event
          : previous.event;
      result[result.length - 1] = {
        ...previous,
        id: winner.id,
        event: winner,
        count: previous.count + 1,
        last_at: event.occurred_at,
        is_merged: true,
        count_label: `×${previous.count + 1}`,
        importance_rank: winner.importance_rank,
      };
      continue;
    }
    result.push(singleCluster(event));
  }
  return result;
}

/**
 * Order clusters by time with importance as a tie breaker.
 *
 * @param clusters - The clusters to sort.
 * @returns A new sorted list.
 */
export function sortClusters(clusters: EventCluster[]): EventCluster[] {
  return [...clusters].sort((a, b) => {
    const timeDelta = Date.parse(b.first_at) - Date.parse(a.first_at);
    if (timeDelta !== 0) return timeDelta;
    if (b.importance_rank !== a.importance_rank) {
      return b.importance_rank - a.importance_rank;
    }
    return a.id.localeCompare(b.id);
  });
}

/**
 * Group clusters into nested day and hour buckets.
 *
 * @param clusters - Deduplicated clusters.
 * @param now - Optional reference date for relative day labels.
 * @returns Day buckets ordered newest first.
 */
export function groupClusters(
  clusters: EventCluster[],
  now: Date = new Date(),
): TimelineBucket[] {
  const days = new Map<string, EventCluster[]>();
  for (const cluster of clusters) {
    const key = dayKey(cluster.first_at);
    const list = days.get(key) ?? [];
    list.push(cluster);
    days.set(key, list);
  }
  return [...days.entries()]
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([key, items]) => {
      const hours = new Map<string, EventCluster[]>();
      for (const cluster of items) {
        const hour = hourKey(cluster.first_at);
        const list = hours.get(hour) ?? [];
        list.push(cluster);
        hours.set(hour, list);
      }
      const children: TimelineBucket[] = [...hours.entries()]
        .sort(([a], [b]) => b.localeCompare(a))
        .map(([hour, hourItems]) => {
          const sorted = sortClusters(hourItems);
          return {
            key: hour,
            label: hourLabel(hourItems[0].first_at),
            level: "hour",
            events: sorted,
            children: [],
            count: sorted.reduce((total, item) => total + item.count, 0),
            item_count: sorted.length,
            critical_count: sorted.filter(
              (item) => item.event.importance === "critical",
            ).length,
            peak_importance: peakImportance(sorted),
          };
        });
      return {
        key,
        label: dayLabel(items[0].first_at, now),
        level: "day",
        events: [],
        children,
        count: children.reduce((total, child) => total + child.count, 0),
        item_count: children.reduce(
          (total, child) => total + child.item_count,
          0,
        ),
        critical_count: children.reduce(
          (total, child) => total + child.critical_count,
          0,
        ),
        peak_importance: peakImportance(
          children.flatMap((child) => child.events),
        ),
      };
    });
}

/**
 * Return the highest importance tier present in a set of clusters.
 *
 * @param clusters - The clusters to inspect.
 * @returns The peak tier, or `low` for an empty input.
 */
export function peakImportance(clusters: EventCluster[]): Importance {
  return clusters.reduce<Importance>((peak, cluster) => {
    return importanceRank(cluster.event.importance) > importanceRank(peak)
      ? cluster.event.importance
      : peak;
  }, "low");
}

/**
 * Flatten a bucket hierarchy into rows for a virtual-style list.
 *
 * @param buckets - Day buckets with hourly children.
 * @returns A flat sequence of day headers, hour headers and event rows.
 */
export function flattenBuckets(buckets: TimelineBucket[]): TimelineRow[] {
  const rows: TimelineRow[] = [];
  for (const bucket of buckets) {
    rows.push({ type: "day", key: `day:${bucket.key}`, bucket });
    for (const child of bucket.children) {
      rows.push({ type: "hour", key: `hour:${child.key}`, bucket: child });
      for (const cluster of child.events) {
        rows.push({ type: "event", key: `event:${cluster.id}`, cluster });
      }
    }
    for (const cluster of bucket.events) {
      rows.push({ type: "event", key: `event:${cluster.id}`, cluster });
    }
  }
  return rows;
}

/**
 * Apply local filters to a list of events.
 *
 * @param events - The candidate events.
 * @param query - The filter values.
 * @returns The matching events.
 */
export function filterEvents(
  events: TimelineEvent[],
  query: TimelineQuery,
): TimelineEvent[] {
  const kinds = new Set(query.kinds ?? []);
  const actors = new Set(query.actors ?? []);
  const importance = new Set(query.importance ?? []);
  const from = query.from ? Date.parse(query.from) : Number.NEGATIVE_INFINITY;
  const to = query.to ? Date.parse(query.to) : Number.POSITIVE_INFINITY;
  return events.filter((event) => {
    const moment = Date.parse(event.occurred_at);
    if (kinds.size > 0 && !kinds.has(event.kind)) return false;
    if (actors.size > 0 && !actors.has(event.actor_id)) return false;
    if (importance.size > 0 && !importance.has(event.importance)) return false;
    if (query.teamId && event.team_id !== query.teamId) return false;
    if (moment < from || moment > to) return false;
    return true;
  });
}

/**
 * Return events that arrived after a previously seen identifier.
 *
 * @param events - Events ordered newest first.
 * @param lastSeenId - The newest event id from the previous load.
 * @returns The events that were not previously visible.
 */
export function newEventsSince(
  events: TimelineEvent[],
  lastSeenId: string | null,
): TimelineEvent[] {
  if (lastSeenId === null) return [];
  const index = events.findIndex((event) => event.id === lastSeenId);
  if (index < 0) return events;
  return events.slice(0, index);
}

/**
 * Merge a newly loaded page into previously loaded clusters.
 *
 * @param existing - Already visible clusters.
 * @param incoming - Clusters from the next page.
 * @returns Distinct clusters in their original order.
 */
export function mergeClusters(
  existing: EventCluster[],
  incoming: EventCluster[],
): EventCluster[] {
  const seen = new Set(existing.map((cluster) => cluster.id));
  return [...existing, ...incoming.filter((cluster) => !seen.has(cluster.id))];
}

/**
 * Count how many active filter groups are applied.
 *
 * @param query - The filter values.
 * @returns The number of active groups.
 */
export function activeFilterCount(query: TimelineQuery): number {
  let count = 0;
  if (query.kinds?.length) count += 1;
  if (query.actors?.length) count += 1;
  if (query.importance?.length) count += 1;
  if (query.teamId) count += 1;
  if (query.from || query.to) count += 1;
  return count;
}

/**
 * Convert an unknown input into a date.
 *
 * @param value - An ISO string or date.
 * @returns The corresponding date, or the Unix epoch for invalid input.
 */
function toDate(value: string | Date): Date {
  if (value instanceof Date) return value;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? new Date(0) : parsed;
}
