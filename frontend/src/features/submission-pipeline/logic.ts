/**
 * Pure validation and presentation logic for the submission console.
 *
 * These helpers mirror the backend domain rules so the browser can give
 * immediate feedback without waiting for a round trip. No function here
 * touches the network or the DOM.
 */

import {
  ERROR_MESSAGES,
  PIPELINE_STAGES,
  type ChallengeOption,
  type MemberOption,
  type SubmissionStatus,
  type ValidationResult,
  type ValidationRule,
} from "./types";

/** The default flag wrapper pattern used when no rules have been loaded. */
export const DEFAULT_FLAG_PATTERN = "^flag\\{[a-z0-9_]+\\}$";

/** Maximum accepted flag length. */
export const MAX_FLAG_LENGTH = 256;

/** Default retry budget used by the console. */
export const DEFAULT_MAX_ATTEMPTS = 3;

/** Fallback rules used before the API has returned the configured rules. */
export const FALLBACK_RULES: ValidationRule[] = [
  {
    id: "rule-format",
    name: "Flag wrapper",
    pattern: DEFAULT_FLAG_PATTERN,
    description:
      "Use the flag{...} wrapper with lower-case letters, digits and underscores.",
    enabled: true,
    priority: 10,
    kind: "format",
  },
  {
    id: "rule-length",
    name: "Flag length",
    pattern: "^.{8,256}$",
    description: "Flags must be between 8 and 256 characters long.",
    enabled: true,
    priority: 20,
    kind: "format",
  },
];

/** Static hints displayed underneath the flag input. */
export const VALIDATION_HINTS: string[] = [
  "Flags are trimmed and lower-cased automatically.",
  "Use the flag{...} wrapper with lower-case letters, digits and underscores.",
  "Duplicate flags for the same challenge are rejected.",
  "Rejected submissions can be retried with a corrected flag.",
];

/**
 * Normalise a raw flag into the canonical comparison form.
 *
 * @param raw - The flag as typed by a member.
 * @returns The trimmed, lower-cased canonical form.
 */
export function normalizeFlag(raw: string): string {
  let cleaned = raw.trim().toLowerCase();
  while (
    cleaned.length >= 2 &&
    "\"'`".includes(cleaned[0]) &&
    cleaned[0] === cleaned[cleaned.length - 1]
  ) {
    cleaned = cleaned.slice(1, -1).trim();
  }
  return cleaned.replace(/\s+/g, "_");
}

/**
 * Convert a rule pattern into a full-string regular expression.
 *
 * @param pattern - The stored pattern, optionally anchored.
 * @returns A source string that always anchors at both ends.
 */
function fullPattern(pattern: string): string {
  const body = pattern.replace(/^\^/, "").replace(/\$$/, "");
  return `^(?:${body})$`;
}

/**
 * Validate a flag against the enabled rules.
 *
 * @param raw - The raw flag as typed by a member.
 * @param rules - Rules supplied by the API; fallback rules are used when empty.
 * @returns A structured validation result with a hint message.
 */
export function validateFlag(
  raw: string,
  rules: ValidationRule[] = FALLBACK_RULES,
): ValidationResult {
  const candidate = normalizeFlag(raw);
  if (!candidate) {
    return {
      valid: false,
      code: "format_empty",
      message: ERROR_MESSAGES.format_empty,
    };
  }
  if (candidate.length > MAX_FLAG_LENGTH) {
    return {
      valid: false,
      code: "format_too_long",
      message: ERROR_MESSAGES.format_too_long,
    };
  }

  const active = (rules.length > 0 ? rules : FALLBACK_RULES)
    .filter((rule) => rule.enabled)
    .sort((a, b) => a.priority - b.priority || a.id.localeCompare(b.id));

  for (const rule of active) {
    let expression: RegExp;
    try {
      expression = new RegExp(fullPattern(rule.pattern));
    } catch {
      continue;
    }
    if (!expression.test(candidate)) {
      return {
        valid: false,
        code: "format_invalid",
        message: rule.description || `Flag must satisfy the ${rule.name} rule.`,
      };
    }
  }

  return {
    valid: true,
    code: "accepted",
    message: "The flag looks well formed.",
  };
}

/**
 * Return the visual stage reached by a status.
 *
 * @param status - The submission status.
 * @returns The stage index (0-2) and whether the final stage failed.
 */
export function stageFor(status: SubmissionStatus): {
  index: number;
  failed: boolean;
} {
  if (status === "queued") return { index: 0, failed: false };
  if (status === "validating" || status === "retrying")
    return { index: 1, failed: false };
  if (status === "rejected") return { index: 2, failed: true };
  return { index: PIPELINE_STAGES.length - 1, failed: false };
}

/**
 * Return whether a retry can be requested for a submission.
 *
 * @param status - The current status.
 * @param attempts - The number of attempts already consumed.
 * @param maxAttempts - The retry policy budget.
 * @returns Whether the retry affordance should be enabled.
 */
export function canRetry(
  status: SubmissionStatus,
  attempts: number,
  maxAttempts: number = DEFAULT_MAX_ATTEMPTS,
): boolean {
  return status === "rejected" && attempts > 0 && attempts < maxAttempts;
}

/**
 * Return a compact, display-safe representation of a flag.
 *
 * @param flag - The normalised flag.
 * @returns A masked string that never reveals the full answer.
 */
export function maskFlag(flag: string): string {
  const value = normalizeFlag(flag);
  if (value.length <= 8)
    return value.slice(0, 2) + "*".repeat(Math.max(0, value.length - 2));
  const stars = "*".repeat(Math.min(10, value.length - 9));
  return `${value.slice(0, 5)}${stars}${value.slice(-4)}`;
}

/**
 * Format an ISO timestamp as a relative age.
 *
 * @param iso - The ISO-8601 timestamp.
 * @param now - The current epoch milliseconds.
 * @returns A short relative label.
 */
export function formatRelative(iso: string, now: number = Date.now()): string {
  const timestamp = Date.parse(iso);
  if (Number.isNaN(timestamp)) return "—";
  const seconds = Math.max(0, Math.floor((now - timestamp) / 1000));
  if (seconds < 5) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

/**
 * Compute a success percentage.
 *
 * @param accepted - Number of accepted submissions.
 * @param total - Number of processed submissions.
 * @returns A percentage rounded to one decimal place.
 */
export function successPercent(accepted: number, total: number): number {
  if (total <= 0) return 0;
  return Math.round((accepted / total) * 1000) / 10;
}

/**
 * Resolve a challenge option label with a safe fallback.
 *
 * @param id - The challenge identifier.
 * @param options - Available challenges.
 * @returns A display label.
 */
export function challengeLabel(id: string, options: ChallengeOption[]): string {
  return options.find((option) => option.id === id)?.title ?? id;
}

/**
 * Resolve a member option label with a safe fallback.
 *
 * @param id - The member identifier.
 * @param options - Available members.
 * @returns A display label.
 */
export function memberLabel(id: string, options: MemberOption[]): string {
  const member = options.find((option) => option.id === id);
  if (!member) return id;
  return member.display_name || member.handle;
}
