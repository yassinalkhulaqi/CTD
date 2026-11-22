/**
 * Public exports of the team roster feature.
 */

export { plugin } from "./plugin";
export { rosterApi } from "./api";
export { useRoster } from "./hooks";
export { RosterPage } from "./RosterPage";
export { RosterTable } from "./components/RosterTable";
export { MemberCard } from "./components/MemberCard";
export { InviteDialog } from "./components/InviteDialog";
export { RoleChip } from "./components/RoleChip";
export { CapacityBar } from "./components/CapacityBar";
export { RosterStatsView } from "./components/RosterStats";
export type {
  AcceptanceResult,
  AssignmentInput,
  Availability,
  Invitation,
  InvitationInput,
  InvitationStatus,
  MemberFilters,
  MemberSortKey,
  RosterAssignment,
  RosterMember,
  RosterMemberInput,
  RosterMemberPatch,
  RosterPermission,
  RosterRole,
  RosterSnapshot,
  RosterStats,
  RosterSummary,
  RosterTone,
  RosterView,
} from "./types";
