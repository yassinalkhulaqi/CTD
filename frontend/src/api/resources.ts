/**
 * Resource hooks binding the typed endpoints to the query layer.
 *
 * Every hook owns its cache key so components stay free of query plumbing.
 */

import { useCallback, useMemo } from "react";
import {
  challengesApi,
  dashboardApi,
  membersApi,
  solvesApi,
  statsApi,
  teamsApi,
  type ChallengeQuery,
  type SolveQuery,
  type TeamQuery,
} from "./endpoints";
import { queryKey } from "./cache";
import { useMutation } from "./useMutation";
import { useQuery, type UseQueryResult } from "./useQuery";

/** Options shared by every resource hook. */
export interface ResourceOptions {
  /** Whether the query should run automatically. */
  enabled?: boolean;
  /** The polling interval in milliseconds. */
  refetchInterval?: number;
  /** The time after which the data is considered stale, in milliseconds. */
  staleTime?: number;
}

/**
 * Return the teams of the competition.
 *
 * @param options - The hook options.
 * @returns The query state.
 */
export function useTeams(options: ResourceOptions = {}): UseQueryResult<Awaited<ReturnType<typeof teamsApi.list>>> {
  const key = queryKey("teams");
  const fetcher = useCallback(
    (signal: AbortSignal) => teamsApi.list({ signal }),
    [],
  );
  return useQuery({ key, fetcher, ...options });
}

/**
 * Return the members of the competition.
 *
 * @param query - Optional filters.
 * @param options - The hook options.
 * @returns The query state.
 */
export function useMembers(
  query: TeamQuery = {},
  options: ResourceOptions = {},
): UseQueryResult<Awaited<ReturnType<typeof membersApi.list>>> {
  const teamId = query.teamId;
  const key = queryKey("members", { teamId });
  const fetcher = useCallback(
    (signal: AbortSignal) => membersApi.list({ teamId }, { signal }),
    [teamId],
  );
  return useQuery({ key, fetcher, ...options });
}

/**
 * Return the challenges of the competition.
 *
 * @param query - Optional filters.
 * @param options - The hook options.
 * @returns The query state.
 */
export function useChallenges(
  query: ChallengeQuery = {},
  options: ResourceOptions = {},
): UseQueryResult<Awaited<ReturnType<typeof challengesApi.list>>> {
  const { teamId, category, status } = query;
  const key = queryKey("challenges", { teamId, category, status });
  const fetcher = useCallback(
    (signal: AbortSignal) => challengesApi.list({ teamId, category, status }, { signal }),
    [teamId, category, status],
  );
  return useQuery({ key, fetcher, ...options });
}

/**
 * Return the per-member contribution statistics.
 *
 * @param query - Optional filters.
 * @param options - The hook options.
 * @returns The query state.
 */
export function useContributions(
  query: TeamQuery = {},
  options: ResourceOptions = {},
): UseQueryResult<Awaited<ReturnType<typeof membersApi.contributions>>> {
  const teamId = query.teamId;
  const key = queryKey("members:contributions", { teamId });
  const fetcher = useCallback(
    (signal: AbortSignal) => membersApi.contributions({ teamId }, { signal }),
    [teamId],
  );
  return useQuery({ key, fetcher, ...options });
}

/**
 * Return the solves of the competition.
 *
 * @param query - Optional filters.
 * @param options - The hook options.
 * @returns The query state.
 */
export function useSolves(
  query: SolveQuery = {},
  options: ResourceOptions = {},
): UseQueryResult<Awaited<ReturnType<typeof solvesApi.list>>> {
  const { memberId, challengeId, teamId } = query;
  const key = queryKey("solves", { memberId, challengeId, teamId });
  const fetcher = useCallback(
    (signal: AbortSignal) => solvesApi.list({ memberId, challengeId, teamId }, { signal }),
    [memberId, challengeId, teamId],
  );
  return useQuery({ key, fetcher, ...options });
}

/**
 * Return the headline counters of the competition.
 *
 * @param options - The hook options.
 * @returns The query state.
 */
export function useOverview(options: ResourceOptions = {}) {
  const key = queryKey("stats:overview");
  const fetcher = useCallback((signal: AbortSignal) => statsApi.overview({ signal }), []);
  return useQuery({ key, fetcher, ...options });
}

/**
 * Return the aggregated dashboard payload.
 *
 * @param teamId - Optional team filter.
 * @param options - The hook options.
 * @returns The query state.
 */
export function useDashboardSnapshot(teamId?: string, options: ResourceOptions = {}) {
  const key = queryKey("dashboard", { teamId });
  const fetcher = useCallback(
    (signal: AbortSignal) => dashboardApi.snapshot(teamId, { signal }),
    [teamId],
  );
  return useQuery({ key, fetcher, ...options });
}

/**
 * Return the hourly solve timeline.
 *
 * @param hours - The size of the window in hours.
 * @param teamId - Optional team filter.
 * @param options - The hook options.
 * @returns The query state.
 */
export function useTimeline(hours = 24, teamId?: string, options: ResourceOptions = {}) {
  const key = queryKey("stats:timeline", { hours, teamId });
  const fetcher = useCallback(
    (signal: AbortSignal) => statsApi.timeline(hours, teamId, { signal }),
    [hours, teamId],
  );
  return useQuery({ key, fetcher, ...options });
}

/**
 * Return the mutation used to record a solve.
 *
 * @returns The mutation state.
 */
export function useRecordSolve() {
  return useMutation({
    mutationFn: (input: Parameters<typeof solvesApi.create>[0]) => solvesApi.create(input),
    invalidates: [queryKey("solves"), queryKey("challenges"), queryKey("stats:overview")],
    invalidatesPrefixes: [queryKey("dashboard")],
  });
}

/**
 * Return the mutation used to create a challenge.
 *
 * @returns The mutation state.
 */
export function useCreateChallenge() {
  return useMutation({
    mutationFn: (input: Parameters<typeof challengesApi.create>[0]) =>
      challengesApi.create(input),
    invalidates: [queryKey("challenges"), queryKey("stats:overview")],
    invalidatesPrefixes: [queryKey("dashboard")],
  });
}

/**
 * Return the mutation used to create a member.
 *
 * @returns The mutation state.
 */
export function useCreateMember() {
  return useMutation({
    mutationFn: (input: Parameters<typeof membersApi.create>[0]) => membersApi.create(input),
    invalidates: [queryKey("members"), queryKey("stats:overview")],
    invalidatesPrefixes: [queryKey("dashboard")],
  });
}

/**
 * Return the mutations available on a challenge.
 *
 * @param challengeId - The identifier of the challenge.
 * @returns The available mutations.
 */
export function useChallengeMutations(challengeId: string) {
  const setStatus = useMutation({
    mutationFn: (status: Parameters<typeof challengesApi.setStatus>[1]) =>
      challengesApi.setStatus(challengeId, status),
    invalidates: [queryKey("challenges"), queryKey("stats:overview")],
    invalidatesPrefixes: [queryKey("dashboard")],
  });

  const remove = useMutation({
    mutationFn: () => challengesApi.remove(challengeId),
    invalidates: [queryKey("challenges"), queryKey("stats:overview")],
    invalidatesPrefixes: [queryKey("dashboard")],
  });

  return useMemo(() => ({ setStatus, remove }), [setStatus, remove]);
}
