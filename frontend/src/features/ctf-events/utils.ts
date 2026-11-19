/** Pure calculations shared by the event screens and their tests. */

import type { BadgeTone } from "../../components/ui";
import type { CtfEvent, EventStatus, EventStats } from "./types";

/** The minimum shape required to derive an event status. */
export interface EventSchedule {
  starts_at: string;
  ends_at: string;
  status: EventStatus;
}

/** Display labels for the four lifecycle states. */
export const STATUS_LABELS: Record<EventStatus, string> = {
  draft: "Draft",
  upcoming: "Upcoming",
  live: "Live now",
  archived: "Archived",
};

/** Display labels for the two scoring formats. */
export const FORMAT_LABELS: Record<CtfEvent["format"], string> = {
  jeopardy: "Jeopardy",
  attack_defence: "Attack / Defence",
};

/** Statuses that can accept teams when registration is enabled. */
export const OPEN_STATUSES: ReadonlySet<EventStatus> = new Set([
  "upcoming",
  "live",
]);

/**
 * Derive the effective status of an event at a given instant.
 *
 * Draft and archived events keep their stored state. Every other event is
 * upcoming before its window, live inside it and archived afterwards.
 *
 * @param event - The schedule of the event.
 * @param nowMs - The current time in epoch milliseconds.
 * @returns The derived lifecycle status.
 */
export function deriveEventStatus(
  event: EventSchedule,
  nowMs: number = Date.now(),
): EventStatus {
  if (event.status === "draft" || event.status === "archived") {
    return event.status;
  }
  if (nowMs < Date.parse(event.starts_at)) return "upcoming";
  if (nowMs < Date.parse(event.ends_at)) return "live";
  return "archived";
}

/**
 * Format a number of seconds as a compact countdown.
 *
 * @param seconds - Seconds remaining; negative values are clamped to zero.
 * @returns A string such as `02d 04h`, `05h 32m` or `12m 09s`.
 */
export function formatCountdown(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  const pad = (value: number) => String(value).padStart(2, "0");
  if (days > 0) return `${pad(days)}d ${pad(hours)}h`;
  if (hours > 0) return `${pad(hours)}h ${pad(minutes)}m`;
  return `${pad(minutes)}m ${pad(secs)}s`;
}

/**
 * Return the seconds relevant to an event's current lifecycle phase.
 *
 * @param event - The event schedule.
 * @param nowMs - The current time in epoch milliseconds.
 * @returns Seconds until the next transition, or zero for draft/archived.
 */
export function countdownSeconds(
  event: EventSchedule,
  nowMs: number = Date.now(),
): number {
  const status = deriveEventStatus(event, nowMs);
  if (status === "upcoming") {
    return Math.max(0, Math.ceil((Date.parse(event.starts_at) - nowMs) / 1000));
  }
  if (status === "live") {
    return Math.max(0, Math.ceil((Date.parse(event.ends_at) - nowMs) / 1000));
  }
  return 0;
}

/**
 * Compute the fraction of the countdown ring that should be filled.
 *
 * @param event - The event schedule.
 * @param nowMs - The current time in epoch milliseconds.
 * @returns A value between zero and one.
 */
export function ringProgress(
  event: EventSchedule,
  nowMs: number = Date.now(),
): number {
  const status = deriveEventStatus(event, nowMs);
  const duration = Math.max(
    1,
    Date.parse(event.ends_at) - Date.parse(event.starts_at),
  );
  if (status === "live") {
    return clamp01((nowMs - Date.parse(event.starts_at)) / duration);
  }
  if (status === "upcoming") {
    const lead = Math.min(duration, 86_400_000);
    const remaining = Date.parse(event.starts_at) - nowMs;
    return clamp01(1 - remaining / lead);
  }
  return 1;
}

/**
 * Clamp a number to the unit interval.
 *
 * @param value - The raw value.
 * @returns The clamped value.
 */
export function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

/**
 * Map a lifecycle status to the design system's badge tone.
 *
 * @param status - The lifecycle status.
 * @returns The semantic tone.
 */
export function statusTone(status: EventStatus): BadgeTone {
  switch (status) {
    case "draft":
      return "neutral";
    case "upcoming":
      return "info";
    case "live":
      return "success";
    case "archived":
      return "warning";
  }
}

/**
 * Render the competition window using the visitor's locale.
 *
 * @param event - The event whose window should be displayed.
 * @returns A human readable date range.
 */
export function formatEventWindow(event: EventSchedule): string {
  const options: Intl.DateTimeFormatOptions = {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  };
  const start = new Date(event.starts_at).toLocaleString(undefined, options);
  const end = new Date(event.ends_at).toLocaleString(undefined, options);
  return `${start} – ${end}`;
}

/**
 * Sum the headline figures of a set of events.
 *
 * @param stats - The per-event statistics returned by the API.
 * @returns Aggregate figures used by the stats strip.
 */
export function aggregateStats(stats: EventStats[]): {
  events: number;
  confirmed: number;
  waitlisted: number;
  fill: number;
} {
  if (stats.length === 0) {
    return { events: 0, confirmed: 0, waitlisted: 0, fill: 0 };
  }
  const confirmed = stats.reduce((total, item) => total + item.confirmed, 0);
  const capacity = stats.reduce((total, item) => total + item.capacity, 0);
  const waitlisted = stats.reduce((total, item) => total + item.waitlisted, 0);
  return {
    events: stats.length,
    confirmed,
    waitlisted,
    fill: capacity === 0 ? 0 : Math.round((confirmed / capacity) * 100),
  };
}

/**
 * Format a capacity label such as `3 / 8 teams`.
 *
 * @param event - The event.
 * @param stats - Its statistics, when loaded.
 * @returns The label.
 */
export function capacityLabel(event: CtfEvent, stats?: EventStats): string {
  const confirmed = stats?.confirmed ?? 0;
  return `${confirmed} / ${event.max_team_size} teams`;
}
