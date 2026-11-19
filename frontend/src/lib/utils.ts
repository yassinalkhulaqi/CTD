/**
 * Utility helpers shared by the dashboard UI.
 */

/**
 * Join conditional class names into a single string.
 *
 * Strings are appended verbatim, objects contribute the keys whose value is
 * truthy and every other falsy value is skipped.
 *
 * @param values - Class names, arrays or objects with truthy keys.
 * @returns The merged class string.
 */
export function cn(...values: unknown[]): string {
  const classes: string[] = [];

  for (const value of values) {
    if (!value) continue;

    if (typeof value === "string") {
      classes.push(value);
      continue;
    }

    if (typeof value === "object") {
      for (const [key, enabled] of Object.entries(
        value as Record<string, unknown>,
      )) {
        if (enabled) classes.push(key);
      }
    }
  }

  return classes.join(" ");
}

/**
 * Clamp a number into the inclusive range.
 *
 * @param value - The value to clamp.
 * @param min - Lower bound.
 * @param max - Upper bound.
 * @returns The clamped value.
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Format a number with locale aware thousands separators.
 *
 * @param value - The number to format.
 * @returns The formatted number.
 */
export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

/**
 * Format a duration expressed in seconds as `HH:MM:SS`.
 *
 * @param seconds - Duration in seconds.
 * @returns The formatted duration.
 */
export function formatDuration(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  const secs = safe % 60;
  return [hours, minutes, secs]
    .map((part) => String(part).padStart(2, "0"))
    .join(":");
}

/**
 * Format a duration expressed in seconds as a compact human readable string.
 *
 * @param seconds - Duration in seconds.
 * @returns The compact duration, e.g. `2h 14m`.
 */
export function formatCompactDuration(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds));
  if (safe < 60) return `${safe}s`;

  const minutes = Math.floor(safe / 60);
  if (minutes < 60) return `${minutes}m ${safe % 60}s`;

  const hours = Math.floor(minutes / 60);
  const remainderMinutes = minutes % 60;
  if (hours < 24) return `${hours}h ${remainderMinutes}m`;

  const days = Math.floor(hours / 24);
  return `${days}d ${hours % 24}h`;
}

/**
 * Format an ISO timestamp as a relative time such as `3m ago`.
 *
 * @param iso - The ISO-8601 timestamp.
 * @param now - Reference time, defaults to the current time.
 * @returns The relative time string.
 */
export function formatRelativeTime(
  iso: string,
  now: Date = new Date(),
): string {
  const timestamp = Date.parse(iso);
  if (Number.isNaN(timestamp)) return "—";

  const deltaSeconds = Math.round((timestamp - now.getTime()) / 1000);
  const absolute = Math.abs(deltaSeconds);

  if (absolute < 45) return "just now";

  const units: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ["year", 31_536_000],
    ["month", 2_592_000],
    ["day", 86_400],
    ["hour", 3_600],
    ["minute", 60],
    ["second", 1],
  ];

  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  for (const [unit, seconds] of units) {
    if (absolute >= seconds || unit === "second") {
      return formatter.format(Math.round(deltaSeconds / seconds), unit);
    }
  }
  return "just now";
}

/**
 * Format an ISO timestamp as a wall clock time.
 *
 * @param iso - The ISO-8601 timestamp.
 * @returns The formatted time.
 */
export function formatTime(iso: string): string {
  const timestamp = Date.parse(iso);
  if (Number.isNaN(timestamp)) return "—";
  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(timestamp);
}

/**
 * Format a ratio as a percentage string.
 *
 * @param ratio - A ratio between 0 and 1.
 * @param digits - Number of fraction digits.
 * @returns The percentage string.
 */
export function formatPercent(ratio: number, digits = 1): string {
  return `${(clamp(ratio, 0, 1) * 100).toFixed(digits)}%`;
}

/**
 * Create a deterministic pseudo-random identifier.
 *
 * @param prefix - Optional prefix for the identifier.
 * @returns The generated identifier.
 */
export function uniqueId(prefix = "id"): string {
  const random = Math.random().toString(36).slice(2, 10);
  return `${prefix}-${random}`;
}

/**
 * Return a promise that resolves after the given delay.
 *
 * @param ms - Delay in milliseconds.
 * @returns The resolved promise.
 */
export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}
