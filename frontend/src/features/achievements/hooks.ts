/**
 * Data hooks for the achievement gallery and evaluation flows.
 */

import { useCallback } from "react";
import { queryKey, useMutation, useQuery } from "../../api";
import { achievementApi } from "./api";
import type { BadgeListParams } from "./types";

/**
 * Load the badge catalogue with progress for an optional member.
 *
 * @param params - Catalogue filters.
 * @returns The query state.
 */
export function useAchievementBadges(params: BadgeListParams = {}) {
  const { member_id, tier, criteria_kind, include_secret } = params;
  const key = queryKey("achievements:badges", {
    member_id,
    tier,
    criteria_kind,
    include_secret,
  });
  const fetcher = useCallback(
    (signal: AbortSignal) =>
      achievementApi.listBadges(
        { member_id, tier, criteria_kind, include_secret },
        signal,
      ),
    [member_id, tier, criteria_kind, include_secret],
  );
  return useQuery({ key, fetcher, staleTime: 20_000 });
}

/**
 * Load the achievement leaderboard.
 *
 * @param limit - Optional maximum number of entries.
 * @returns The query state.
 */
export function useAchievementLeaderboard(limit?: number) {
  const key = queryKey("achievements:leaderboard", { limit });
  const fetcher = useCallback(
    (_signal: AbortSignal) => achievementApi.getLeaderboard(limit),
    [limit],
  );
  return useQuery({ key, fetcher, staleTime: 20_000 });
}

/**
 * Load aggregate achievement statistics.
 *
 * @returns The query state.
 */
export function useAchievementStats() {
  const key = queryKey("achievements:stats");
  const fetcher = useCallback(
    (_signal: AbortSignal) => achievementApi.getStats(),
    [],
  );
  return useQuery({ key, fetcher, staleTime: 30_000 });
}

/**
 * Load one member's achievement profile.
 *
 * @param memberId - The member identifier, or `null` to disable the query.
 * @returns The query state.
 */
export function useMemberAchievements(memberId: string | null) {
  const key = memberId ? queryKey("achievements:member", { memberId }) : null;
  const fetcher = useCallback(
    (_signal: AbortSignal) =>
      achievementApi.getMemberAchievements(memberId ?? ""),
    [memberId],
  );
  return useQuery({ key, fetcher, staleTime: 15_000 });
}

/** Input accepted by the evaluation mutation. */
export interface EvaluateInput {
  memberId: string;
  metrics: Record<string, number>;
}

/**
 * Return the mutation used to evaluate member metrics.
 *
 * @returns The mutation state.
 */
export function useEvaluateAchievements() {
  return useMutation<
    EvaluateInput,
    Awaited<ReturnType<typeof achievementApi.evaluateMember>>
  >({
    mutationFn: (input) =>
      achievementApi.evaluateMember(input.memberId, input.metrics),
    invalidatesPrefixes: [queryKey("achievements")],
  });
}

/** Input accepted by the manual award mutation. */
export interface AwardInput {
  memberId: string;
  badgeId: string;
}

/**
 * Return the mutation used to grant a badge manually.
 *
 * @returns The mutation state.
 */
export function useAwardBadge() {
  return useMutation<
    AwardInput,
    Awaited<ReturnType<typeof achievementApi.awardBadge>>
  >({
    mutationFn: (input) =>
      achievementApi.awardBadge(input.memberId, input.badgeId),
    invalidatesPrefixes: [queryKey("achievements")],
  });
}
