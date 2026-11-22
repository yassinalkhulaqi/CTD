/**
 * Barrel exports for the scoreboard engine feature.
 */

export { plugin } from "./plugin";
export { ScoreboardPage } from "./ScoreboardPage";
export { scoreboardApi } from "./api";
export {
  useScoreboardActions,
  useScoreboardOverview,
  useTeamScoreboard,
} from "./hooks";
export type {
  ScoreboardActionsState,
  ScoreboardOverviewState,
  TeamScoreboardState,
} from "./hooks";
export { MovementBadge } from "./components/MovementBadge";
export type { MovementBadgeProps } from "./components/MovementBadge";
export { Podium } from "./components/Podium";
export type { PodiumProps } from "./components/Podium";
export { RankTable } from "./components/RankTable";
export type { RankTableProps } from "./components/RankTable";
export { RuleEditor } from "./components/RuleEditor";
export type { RuleEditorProps } from "./components/RuleEditor";
export { ScoreBreakdownChart } from "./components/ScoreBreakdown";
export type { ScoreBreakdownProps } from "./components/ScoreBreakdown";
export { SnapshotHistory } from "./components/SnapshotHistory";
export type { SnapshotHistoryProps } from "./components/SnapshotHistory";
export {
  computeSolvePoints,
  decayFor,
  formatScore,
  movementDescription,
  movementLabel,
  podiumTone,
  projectStreak,
  sparklinePoints,
  validateRule,
} from "./scoring";
export type {
  CategoryScore,
  DifficultyTier,
  Movement,
  RankingEntry,
  RankingResponse,
  ScoreBreakdown,
  ScoreRule,
  ScoreRuleDraft,
  ScoreSnapshot,
  SolveScore,
  TeamOption,
} from "./types";
