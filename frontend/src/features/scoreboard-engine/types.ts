/**
 * Domain types of the configurable scoreboard feature.
 */

/** Direction a team moved between two ranking snapshots. */
export type Movement = "up" | "down" | "stable" | "new";

/** Difficulty tiers that influence solve scoring. */
export type DifficultyTier = "trivial" | "easy" | "medium" | "hard" | "insane";

/** A stored scoring policy for one team. */
export interface ScoreRule {
  id: string;
  team_id: string;
  name: string;
  base_points: number;
  difficulty_multiplier: number;
  first_blood_bonus: number;
  hint_penalty: number;
  decay_factor: number;
  decay_enabled: boolean;
  updated_at: string;
  summary: string;
}

/** Editable values of a scoring policy. */
export interface ScoreRuleDraft {
  name: string;
  base_points: number;
  difficulty_multiplier: number;
  first_blood_bonus: number;
  hint_penalty: number;
  decay_factor: number;
  decay_enabled: boolean;
}

/** A frozen snapshot of a team's score and rank. */
export interface ScoreSnapshot {
  id: string;
  team_id: string;
  recorded_at: string;
  points: number;
  solves: number;
  rank: number;
  details_json: string;
  details: Record<string, unknown>;
  label: string;
  rule_name: string;
}

/** One row of the live ranking table. */
export interface RankingEntry {
  team_id: string;
  team_name: string;
  points: number;
  solves: number;
  rank: number;
  previous_rank: number | null;
  movement: Movement;
  movement_label: string;
  last_solve_at: string | null;
}

/** The full live ranking response. */
export interface RankingResponse {
  entries: RankingEntry[];
  team_count: number;
  generated_at: string;
  leader_points: number;
  total_points: number;
}

/** An itemised solve score. */
export interface SolveScore {
  solve_id: string;
  challenge_id: string;
  title: string;
  category: string;
  category_label: string;
  difficulty: DifficultyTier;
  solve_index: number;
  solved_at: string;
  base_points: number;
  difficulty_weight: number;
  difficulty_multiplier: number;
  decay: number;
  first_blood: boolean;
  bonus_points: number;
  hint_count: number;
  penalty_points: number;
  points: number;
  formula: string;
}

/** Aggregated scoring statistics for one challenge category. */
export interface CategoryScore {
  category: string;
  label: string;
  accent: string;
  points: number;
  solves: number;
  challenges: number;
  solve_rate: number;
  share: number;
}

/** Everything needed to explain a team's total. */
export interface ScoreBreakdown {
  team_id: string;
  team_name: string;
  rule: ScoreRule;
  total_points: number;
  total_solves: number;
  first_bloods: number;
  hint_penalties: number;
  decay_loss: number;
  average_points: number;
  challenges: number;
  generated_at: string;
  categories: CategoryScore[];
  solves: SolveScore[];
}

/** Minimal team information used by the team selector. */
export interface TeamOption {
  id: string;
  name: string;
  slug: string;
  color: string;
}

/** Create an editable draft from a stored rule. */
export function draftFromRule(rule: ScoreRule): ScoreRuleDraft {
  return {
    name: rule.name,
    base_points: rule.base_points,
    difficulty_multiplier: rule.difficulty_multiplier,
    first_blood_bonus: rule.first_blood_bonus,
    hint_penalty: rule.hint_penalty,
    decay_factor: rule.decay_factor,
    decay_enabled: rule.decay_enabled,
  };
}
