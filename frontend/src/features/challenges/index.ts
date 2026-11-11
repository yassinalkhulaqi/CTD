/**
 * Barrel export for the challenge tracking feature.
 */

export { ChallengeBoard } from "./ChallengeBoard";
export type { ChallengeBoardProps } from "./ChallengeBoard";

export { ChallengeDrawer } from "./ChallengeDrawer";
export type { ChallengeDrawerProps } from "./ChallengeDrawer";

export {
  useAddNote,
  useChallengeNotes,
  useChallengeTimeline,
  useDeleteNote,
  useSubmitFlag,
} from "./hooks";
export type { AddNoteInput, SubmitFlagInput } from "./hooks";

export { challengeDetailsApi } from "./api";

export type {
  BoardColumn,
  BoardColumnData,
  ChallengeWithSolves,
  FlagResult,
  Note,
  TimelineEntry,
} from "./types";
