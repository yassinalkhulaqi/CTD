/** Domain types mirroring the hint engine API. */

export type HintState = "locked" | "eligible" | "unlocked" | "exhausted";

/** One point of the geometric price curve. */
export interface CostPoint {
  tier: number;
  cost: number;
  cumulative: number;
  label: string;
}

/** A catalogue hint returned to authors. */
export interface Hint {
  id: string;
  challenge_id: string;
  tier: number;
  title: string;
  content: string;
  cost: number;
  base_cost: number;
  multiplier: number;
  reveal_after_seconds: number;
  is_active: boolean;
  teaser: string;
  curve: CostPoint[];
  created_at: string;
  updated_at: string;
}

/** A hint as seen by one team, with masking and eligibility applied. */
export interface HintView {
  hint_id: string;
  challenge_id: string;
  tier: number;
  title: string;
  content: string;
  cost: number;
  reveal_after_seconds: number;
  is_active: boolean;
  state: HintState;
  reason: string;
  remaining_seconds: number;
  required_tier: number | null;
  unlocked: boolean;
  eligible: boolean;
  badge_label: string;
  unlocked_at: string | null;
  unlocked_by: string | null;
}

/** A team's hint allowance. */
export interface HintBudget {
  team_id: string;
  total: number;
  spent: number;
  remaining: number;
  reset_at: string;
  created_at: string;
  utilization: number;
  is_exhausted: boolean;
}

/** The masked hint ladder for one challenge. */
export interface ChallengeHintView {
  challenge_id: string;
  team_id: string;
  hints: HintView[];
  budget: HintBudget;
  curve: CostPoint[];
  unlocked_count: number;
}

/** A single reveal history row. */
export interface LedgerEntry {
  id: string;
  hint_id: string;
  hint_title: string;
  tier: number;
  member_id: string;
  member_handle: string;
  team_id: string;
  cost_paid: number;
  unlocked_at: string;
  description: string;
}

/** Spend aggregated at one tier. */
export interface TierSpend {
  tier: number;
  unlocks: number;
  spent: number;
  average_cost: number;
}

/** A team's spend summary. */
export interface TeamSpendSummary {
  team_id: string;
  total: number;
  spent: number;
  remaining: number;
  unlock_count: number;
  utilization: number;
  average_cost: number;
  by_tier: TierSpend[];
}

/** Ledger response combining history and summary. */
export interface HintLedger {
  team_id: string;
  entries: LedgerEntry[];
  summary: TeamSpendSummary;
}

/** The result of spending budget on a hint. */
export interface HintUnlock {
  id: string;
  hint_id: string;
  member_id: string;
  team_id: string;
  cost_paid: number;
  unlocked_at: string;
}

/** Payload used to author or edit a hint. */
export interface HintDraft {
  challenge_id: string;
  tier: number;
  title: string;
  content: string;
  base_cost: number;
  multiplier: number;
  reveal_after_seconds: number;
  is_active: boolean;
}

/** Settings applied when a budget is reset. */
export interface BudgetResetInput {
  total?: number;
  reset_after_seconds?: number;
}

/** An interactive hint card plus its dialog state. */
export interface HintSelection {
  hint: HintView;
  origin: HTMLElement | null;
}
