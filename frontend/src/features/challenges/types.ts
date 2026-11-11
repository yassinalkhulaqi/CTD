/**
 * Types of the challenge tracking feature.
 */

import type { Challenge, Solve } from "../../types";

/** A note attached to a challenge. */
export interface Note {
  id: string;
  challenge_id: string;
  member_id: string;
  body: string;
  preview: string;
  created_at: string;
  updated_at: string;
}

/** A single entry of the solve timeline of a challenge. */
export interface TimelineEntry {
  solve_id: string;
  member_id: string;
  member_handle: string;
  points_awarded: number;
  solved_at: string;
  masked_flag: string;
}

/** The outcome of a flag submission. */
export interface FlagResult {
  accepted: boolean;
  message: string;
  points_awarded: number;
  solve_id: string | null;
}

/** The lifecycle of a challenge on the board. */
export type BoardColumn = "pending" | "active" | "solved" | "locked";

/** A column of the challenge board. */
export interface BoardColumnData {
  /** The identifier of the column. */
  id: BoardColumn;
  /** The label of the column. */
  label: string;
  /** The challenges of the column. */
  challenges: Challenge[];
}

/** A challenge paired with the solves it received. */
export interface ChallengeWithSolves {
  /** The challenge. */
  challenge: Challenge;
  /** The solves recorded for the challenge. */
  solves: Solve[];
}
