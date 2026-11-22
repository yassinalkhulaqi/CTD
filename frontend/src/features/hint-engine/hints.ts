/** Pure calculations shared by the hint cards, budget meter and cost chart. */

import type { BadgeTone } from "../../components/ui";
import type { CostPoint, HintBudget, HintState, HintView } from "./types";

/** Maximum number of tiers on a hint ladder. */
export const MAX_HINT_TIER = 3;

/** Default number of characters left visible on a locked hint. */
export const DEFAULT_TEASER_LENGTH = 28;

/**
 * Round a positive number half up to the nearest integer.
 *
 * `Math.round` already rounds halves towards positive infinity, which matches
 * the backend's decimal ROUND_HALF_UP rule for the prices used here.
 *
 * @param value - The raw price.
 * @returns The rounded whole credit price.
 */
export function roundCredits(value: number): number {
  if (!Number.isFinite(value) || value < 0) return 0;
  return Math.round(value + Number.EPSILON);
}

/**
 * Return the price of one tier on a geometric cost curve.
 *
 * @param baseCost - Price of tier one.
 * @param multiplier - Growth factor between tiers.
 * @param tier - Ladder position, clamped to the supported range.
 * @returns The rounded price in credits.
 */
export function tierCost(
  baseCost: number,
  multiplier: number,
  tier: number,
): number {
  const safeBase = Math.max(1, Math.floor(baseCost));
  const safeMultiplier = Math.max(1, multiplier);
  const safeTier = Math.min(MAX_HINT_TIER, Math.max(1, Math.floor(tier)));
  return roundCredits(safeBase * safeMultiplier ** (safeTier - 1));
}

/**
 * Build the cumulative cost curve for a hint ladder.
 *
 * @param baseCost - Price of tier one.
 * @param multiplier - Growth factor between tiers.
 * @param tiers - Number of tiers to render.
 * @returns One point per tier, including running totals.
 */
export function costCurve(
  baseCost: number,
  multiplier: number,
  tiers: number = MAX_HINT_TIER,
): CostPoint[] {
  const count = Math.min(MAX_HINT_TIER, Math.max(1, Math.floor(tiers)));
  let cumulative = 0;
  const points: CostPoint[] = [];
  for (let tier = 1; tier <= count; tier += 1) {
    const cost = tierCost(baseCost, multiplier, tier);
    cumulative += cost;
    points.push({ tier, cost, cumulative, label: `T${tier}: ${cost}` });
  }
  return points;
}

/**
 * Produce the teaser displayed for a locked hint.
 *
 * @param content - The full hint text.
 * @param visible - Number of leading characters left in the clear.
 * @returns The teaser with one asterisk for every hidden character.
 */
export function maskHintContent(
  content: string,
  visible: number = DEFAULT_TEASER_LENGTH,
): string {
  if (visible < 0) return content;
  if (content.length <= visible) return content;
  return `${content.slice(0, visible)}${"*".repeat(content.length - visible)}`;
}

/**
 * Compute the geometry of a progress ring.
 *
 * @param utilization - Fraction of the budget spent, clamped to 0..1.
 * @param size - Diameter of the ring in pixels.
 * @param strokeWidth - Thickness of the ring stroke.
 * @returns Radius, circumference and dash offset for the SVG circles.
 */
export function ringGeometry(
  utilization: number,
  size: number,
  strokeWidth: number,
) {
  const ratio = Math.min(1, Math.max(0, utilization));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  return {
    radius,
    circumference,
    offset: circumference * (1 - ratio),
    percent: Math.round(ratio * 100),
  };
}

/**
 * Derive display values from a budget.
 *
 * @param budget - The budget returned by the API.
 * @returns Remaining credits and a clamped utilization ratio.
 */
export function budgetUsage(budget: HintBudget | null) {
  if (!budget) return { remaining: 0, spent: 0, total: 0, utilization: 0 };
  const remaining = Math.max(0, budget.total - budget.spent);
  const utilization =
    budget.total > 0 ? Math.min(1, budget.spent / budget.total) : 0;
  return { remaining, spent: budget.spent, total: budget.total, utilization };
}

/**
 * Return whether a hint can be unlocked right now.
 *
 * @param hint - The hint view model.
 * @param budget - The team's budget.
 * @returns `true` when the hint is eligible and affordable.
 */
export function canUnlock(hint: HintView, budget: HintBudget | null): boolean {
  return hint.eligible && budget !== null && budget.remaining >= hint.cost;
}

/**
 * Map a hint state to a design-system badge tone.
 *
 * @param state - The hint state.
 * @returns The matching badge tone.
 */
export function stateTone(state: HintState): BadgeTone {
  switch (state) {
    case "unlocked":
      return "success";
    case "eligible":
      return "accent";
    case "exhausted":
      return "danger";
    default:
      return "neutral";
  }
}

/**
 * Format seconds as a compact countdown label.
 *
 * @param seconds - Seconds remaining.
 * @returns A label such as `4m 12s` or `Ready`.
 */
export function formatCountdown(seconds: number): string {
  if (seconds <= 0) return "Ready";
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  if (minutes < 60)
    return remainder > 0 ? `${minutes}m ${remainder}s` : `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

/**
 * Format a number of credits with thousands separators.
 *
 * @param value - The credit amount.
 * @returns A stable, locale-independent label.
 */
export function formatCredits(value: number): string {
  return Math.round(value).toLocaleString("en-US");
}

/**
 * Format an ISO timestamp as a short local time.
 *
 * @param iso - The ISO timestamp.
 * @returns A readable time, or an em dash for missing values.
 */
export function formatTimestamp(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
