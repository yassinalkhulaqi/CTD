/**
 * Dashboard store: the shared state of the competition overview.
 */

import { create } from "zustand";
import { useShallow } from "zustand/react/shallow";
import type {
  ChallengeCategory,
  ChallengeStatus,
  Member,
  Team,
} from "../types";

/** The granularity of the information shown on the dashboard. */
export type Density = "comfortable" | "compact";

/** The time window used by the analytics panels. */
export type TimeWindow = "6h" | "12h" | "24h" | "7d";

/** The state managed by the dashboard store. */
export interface DashboardState {
  /** The team currently being inspected. */
  selectedTeamId: string | null;
  /** The teams loaded from the API. */
  teams: Team[];
  /** The members loaded from the API. */
  members: Member[];
  /** The identifier of the selected member. */
  selectedMemberId: string | null;
  /** The category filter applied to the challenge board. */
  categoryFilter: ChallengeCategory | "all";
  /** The status filter applied to the challenge board. */
  statusFilter: ChallengeStatus | "all";
  /** The free text query applied to the challenge board. */
  searchQuery: string;
  /** The analytics window. */
  timeWindow: TimeWindow;
  /** The information density of the tables and boards. */
  density: Density;
  /** Whether the sidebar is collapsed. */
  sidebarCollapsed: boolean;
  /** Set the team being inspected. */
  setSelectedTeam: (teamId: string | null) => void;
  /** Replace the loaded teams. */
  setTeams: (teams: Team[]) => void;
  /** Replace the loaded members. */
  setMembers: (members: Member[]) => void;
  /** Set the member being inspected. */
  setSelectedMember: (memberId: string | null) => void;
  /** Set the category filter. */
  setCategoryFilter: (category: ChallengeCategory | "all") => void;
  /** Set the status filter. */
  setStatusFilter: (status: ChallengeStatus | "all") => void;
  /** Set the free text query. */
  setSearchQuery: (query: string) => void;
  /** Set the analytics window. */
  setTimeWindow: (window: TimeWindow) => void;
  /** Set the information density. */
  setDensity: (density: Density) => void;
  /** Toggle the collapsed state of the sidebar. */
  toggleSidebar: () => void;
  /** Reset every filter to its default value. */
  resetFilters: () => void;
}

/**
 * Return the number of hours covered by a time window.
 *
 * @param window - The selected window.
 * @returns The number of hours.
 */
export function windowToHours(window: TimeWindow): number {
  switch (window) {
    case "6h":
      return 6;
    case "12h":
      return 12;
    case "24h":
      return 24;
    case "7d":
      return 168;
    default:
      return 24;
  }
}

export const useDashboardStore = create<DashboardState>()((set) => ({
  selectedTeamId: null,
  teams: [],
  members: [],
  selectedMemberId: null,
  categoryFilter: "all",
  statusFilter: "all",
  searchQuery: "",
  timeWindow: "24h",
  density: "comfortable",
  sidebarCollapsed: false,

  setSelectedTeam: (teamId) => set({ selectedTeamId: teamId }),
  setTeams: (teams) => set({ teams }),
  setMembers: (members) => set({ members }),
  setSelectedMember: (memberId) => set({ selectedMemberId: memberId }),
  setCategoryFilter: (category) => set({ categoryFilter: category }),
  setStatusFilter: (status) => set({ statusFilter: status }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setTimeWindow: (timeWindow) => set({ timeWindow }),
  setDensity: (density) => set({ density }),
  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  resetFilters: () =>
    set({
      categoryFilter: "all",
      statusFilter: "all",
      searchQuery: "",
      selectedMemberId: null,
    }),
}));

/**
 * Return the team currently being inspected.
 *
 * @returns The selected team or `null`.
 */
export function useSelectedTeam(): Team | null {
  return useDashboardStore(
    useShallow(
      (state) =>
        state.teams.find((team) => team.id === state.selectedTeamId) ?? null,
    ),
  );
}

/**
 * Return the members of the currently selected team.
 *
 * @returns The members of the selected team.
 */
export function useSelectedTeamMembers(): Member[] {
  return useDashboardStore(
    useShallow((state) =>
      state.selectedTeamId
        ? state.members.filter(
            (member) => member.team_id === state.selectedTeamId,
          )
        : state.members,
    ),
  );
}

/**
 * Return the number of members currently online.
 *
 * @returns The number of online members.
 */
export function useOnlineMemberCount(): number {
  return useDashboardStore(
    useShallow(
      (state) => state.members.filter((member) => member.is_online).length,
    ),
  );
}

/**
 * Return the team identifier used to scope every request.
 *
 * @returns The selected team identifier or `null`.
 */
export function useActiveTeamId(): string | null {
  return useDashboardStore((state) => state.selectedTeamId);
}

/**
 * Return the number of active filters.
 *
 * @returns The number of filters narrowing the current view.
 */
export function useActiveFilterCount(): number {
  return useDashboardStore(
    useShallow((state) => {
      let count = 0;
      if (state.categoryFilter !== "all") count += 1;
      if (state.statusFilter !== "all") count += 1;
      if (state.searchQuery.trim().length > 0) count += 1;
      return count;
    }),
  );
}
