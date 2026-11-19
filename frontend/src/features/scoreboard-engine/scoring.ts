/**
 * Pure scoring arithmetic shared by the page, the preview and the tests.
 *
 * These helpers mirror the backend domain rules so the editor can show the
 * consequences of a change before it is saved.
 */

import { clamp, formatNumber } from "../../lib/utils";
import type { DifficultyTier, Movement, ScoreRuleDraft } from "./types";

/** Inclusive bounds enforced by the API and by the editor. */
export const RULE_LIMITS = {
  base_points: { min: 0, max: 100000, step: 10 },
  difficulty_multiplier: { min: 0.1, max: 10, step: 0.1 },
  first_blood_bonus: { min: 0, max: 100000, step: 5 },
  hint_penalty: { min: 0, max: 100000, step: 5 },
  decay_factor: { min: 0.05, max: 1, step: 0.05 },
} as const;

/** Maximum score awarded for a single solve. */
export const MAX_SCORE = 1_000_000;

/** Numeric weight of every difficulty tier. */
export const DIFFICULTY_WEIGHTS: Record<DifficultyTier, number> = {
  trivial: 0.5,
  easy: 1,
  medium: 1.75,
  hard: 3,
  insane: 5,
};

/**
 * Return the decay coefficient applied at a solve index.
 *
 * @param rule - The scoring policy.
 * @param index - The zero based chronological solve index.
 * @returns The coefficient, always between zero and one.
 */
export function decayFor(rule: ScoreRuleDraft, index: number): number {
  if (!rule.decay_enabled || index <= 0) return 1;
  return clamp(Math.pow(rule.decay_factor, index), 0, 1);
}

/**
 * Compute the integer points awarded for one solve.
 *
 * @param rule - The scoring policy.
 * @param difficulty - The difficulty tier of the solved challenge.
 * @param solveIndex - The chronological index of the solve for the team.
 * @param firstBlood - Whether the solve earned the first blood bonus.
 * @param hintCount - Number of hints consumed while solving.
 * @returns The clamped, rounded point award.
 */
export function computeSolvePoints(
  rule: ScoreRuleDraft,
  difficulty: DifficultyTier,
  solveIndex = 0,
  firstBlood = false,
  hintCount = 0,
): number {
  const base = rule.base_points * DIFFICULTY_WEIGHTS[difficulty];
  const weighted =
    base * rule.difficulty_multiplier * decayFor(rule, solveIndex);
  const bonus = firstBlood ? rule.first_blood_bonus : 0;
  const penalty = rule.hint_penalty * Math.max(0, hintCount);
  return clamp(Math.round(weighted + bonus - penalty), 0, MAX_SCORE);
}

/**
 * Return the projected points of an entire solve streak.
 *
 * @param rule - The scoring policy.
 * @param difficulties - The difficulty tiers in chronological order.
 * @returns One point award per solve.
 */
export function projectStreak(
  rule: ScoreRuleDraft,
  difficulties: DifficultyTier[],
): number[] {
  return difficulties.map((difficulty, index) =>
    computeSolvePoints(rule, difficulty, index, index === 0),
  );
}

/**
 * Validate an editable rule draft.
 *
 * @param rule - The draft to validate.
 * @returns A mapping of field names to human readable errors.
 */
export function validateRule(rule: ScoreRuleDraft): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!rule.name.trim()) errors.name = "Give this policy a name.";
  if (!Number.isFinite(rule.base_points) || rule.base_points < 0)
    errors.base_points = "Base points cannot be negative.";
  if (
    !Number.isFinite(rule.difficulty_multiplier) ||
    rule.difficulty_multiplier < 0.1
  )
    errors.difficulty_multiplier = "Multiplier must be at least 0.1.";
  if (rule.difficulty_multiplier > 10)
    errors.difficulty_multiplier = "Multiplier cannot exceed 10.";
  if (rule.first_blood_bonus < 0)
    errors.first_blood_bonus = "First blood bonus cannot be negative.";
  if (rule.hint_penalty < 0)
    errors.hint_penalty = "Hint penalty cannot be negative.";
  if (rule.decay_factor < 0.05)
    errors.decay_factor = "Decay must be at least 0.05.";
  if (rule.decay_factor > 1) errors.decay_factor = "Decay cannot exceed 1.";
  return errors;
}

/**
 * Format a movement badge label.
 *
 * @param movement - The movement direction.
 * @param steps - The number of ranks moved.
 * @returns A compact label such as `↑2` or `NEW`.
 */
export function movementLabel(movement: Movement, steps = 0): string {
  if (movement === "new") return "NEW";
  if (movement === "stable") return "—";
  const glyph = movement === "up" ? "↑" : "↓";
  return `${glyph}${steps}`;
}

/**
 * Describe a movement for assistive technology.
 *
 * @param movement - The movement direction.
 * @param steps - The number of ranks moved.
 * @returns A sentence describing the movement.
 */
export function movementDescription(movement: Movement, steps = 0): string {
  if (movement === "new") return "New entry";
  if (movement === "stable") return "Rank unchanged";
  if (movement === "up")
    return `Climbed ${steps} position${steps === 1 ? "" : "s"}`;
  return `Fell ${steps} position${steps === 1 ? "" : "s"}`;
}

/**
 * Build SVG polyline coordinates for a sparkline.
 *
 * @param values - The chronological point totals.
 * @param width - The viewBox width.
 * @param height - The viewBox height.
 * @param padding - Vertical padding in viewBox units.
 * @returns A space separated list of `x,y` pairs.
 */
export function sparklinePoints(
  values: number[],
  width = 240,
  height = 60,
  padding = 6,
): string {
  if (values.length === 0) return "";
  if (values.length === 1) return `${width / 2},${height / 2}`;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const innerHeight = Math.max(1, height - padding * 2);
  return values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width;
      const y = height - padding - ((value - min) / span) * innerHeight;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

/**
 * Format a score with thousands separators.
 *
 * @param value - The raw points.
 * @returns A formatted score string.
 */
export function formatScore(value: number): string {
  return formatNumber(Math.round(value));
}

/**
 * Return the medal colour of a podium position.
 *
 * @param rank - The one based rank.
 * @returns A CSS colour token name.
 */
export function podiumTone(rank: number): string {
  if (rank === 1) return "gold";
  if (rank === 2) return "silver";
  if (rank === 3) return "bronze";
  return "neutral";
}
