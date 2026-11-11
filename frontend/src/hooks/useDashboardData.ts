/**
 * Hooks binding the API layer to the dashboard stores.
 */

import { useEffect } from "react";
import { useMembers, useTeams } from "../api/resources";
import { useDashboardStore } from "../stores/dashboardStore";

/**
 * Load the teams and the members into the dashboard store.
 *
 * The hook is safe to call from several components: the store is only
 * updated when the payloads actually changed.
 *
 * @returns The query states of the teams and the members.
 */
export function useHydrateDashboard(): {
  teams: ReturnType<typeof useTeams>;
  members: ReturnType<typeof useMembers>;
} {
  const teams = useTeams({ staleTime: 60_000 });
  const members = useMembers({}, { staleTime: 60_000 });

  useEffect(() => {
    if (teams.data) useDashboardStore.getState().setTeams(teams.data);
  }, [teams.data]);

  useEffect(() => {
    if (members.data) useDashboardStore.getState().setMembers(members.data);
  }, [members.data]);

  return { teams, members };
}

/**
 * Reset every dashboard store to its default state.
 *
 * @returns A function performing the reset.
 */
export function useResetDashboard(): () => void {
  return () => {
    const state = useDashboardStore.getState();
    state.setTeams([]);
    state.setMembers([]);
    state.setSelectedTeam(null);
    state.setSelectedMember(null);
    state.resetFilters();
  };
}
