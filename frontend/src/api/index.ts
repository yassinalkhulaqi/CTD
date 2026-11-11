/**
 * Public surface of the API integration layer.
 */

export {
  API_BASE_URL,
  ApiError,
  buildQuery,
  configureAuth,
  del,
  get,
  patch,
  pendingRequestCount,
  post,
  put,
  request,
  toApiError,
} from "./client";
export type { RequestOptions, RefreshResolver, TokenResolver } from "./client";

export {
  DEFAULT_STALE_TIME,
  QueryCache,
  queryCache,
  queryKey,
  stableStringify,
} from "./cache";
export type { CacheEntry, CacheSnapshot, QueryCacheOptions } from "./cache";

export { fetcherFrom, useQuery } from "./useQuery";
export type { UseQueryOptions, UseQueryResult } from "./useQuery";

export { useMutation } from "./useMutation";
export type { UseMutationOptions, UseMutationResult } from "./useMutation";

export {
  useChallengeMutations,
  useChallenges,
  useContributions,
  useCreateChallenge,
  useCreateMember,
  useDashboardSnapshot,
  useMembers,
  useOverview,
  useRecordSolve,
  useSolves,
  useTeams,
  useTimeline,
} from "./resources";
export type { ResourceOptions } from "./resources";

export {
  challengesApi,
  dashboardApi,
  membersApi,
  solvesApi,
  statsApi,
  teamsApi,
} from "./endpoints";
export type {
  ChallengeCreateInput,
  ChallengeQuery,
  ChallengeUpdateInput,
  DashboardSnapshot,
  MemberCreateInput,
  MemberUpdateInput,
  SolveCreateInput,
  SolveQuery,
  TeamCreateInput,
  TeamQuery,
  TeamUpdateInput,
} from "./endpoints";
