/**
 * Typed HTTP adapter for the achievement API.
 */

import { buildQuery, get, post } from "../../api/client";
import type {
  AchievementStats,
  AwardResult,
  BadgeCreatePayload,
  BadgeDetailResponse,
  BadgeListParams,
  BadgeListResponse,
  BatchEvaluationResult,
  EvaluationResult,
  LeaderboardResponse,
  MemberAchievement,
  SeedResult,
} from "./types";

/** Base path shared by every achievement endpoint. */
export const ACHIEVEMENTS_PATH = "/api/achievements";

/**
 * Load the badge catalogue with optional filters.
 *
 * @param params - Optional filter parameters.
 * @param signal - Optional abort signal.
 * @returns The badge catalogue.
 */
export function listBadges(
  params: BadgeListParams = {},
  signal?: AbortSignal,
): Promise<BadgeListResponse> {
  const query = buildQuery({
    member_id: params.member_id,
    tier: params.tier,
    criteria_kind: params.criteria_kind,
    include_secret: params.include_secret,
  });
  return get<BadgeListResponse>(`${ACHIEVEMENTS_PATH}/badges${query}`, {
    signal,
  });
}

/**
 * Load one badge by identifier.
 *
 * @param badgeId - The badge identifier.
 * @param memberId - Optional viewer used to reveal secret badges.
 * @returns The badge detail payload.
 */
export function getBadge(
  badgeId: string,
  memberId?: string,
): Promise<BadgeDetailResponse> {
  const query = buildQuery({ member_id: memberId });
  return get<BadgeDetailResponse>(
    `${ACHIEVEMENTS_PATH}/badges/${encodeURIComponent(badgeId)}${query}`,
  );
}

/**
 * Create a custom badge.
 *
 * @param payload - The badge definition.
 * @returns The created badge.
 */
export function createBadge(payload: BadgeCreatePayload): Promise<{
  id: string;
  name: string;
  score: number;
}> {
  return post(`${ACHIEVEMENTS_PATH}/badges`, payload);
}

/**
 * Evaluate one member's metrics.
 *
 * @param memberId - The member identifier.
 * @param metrics - The metrics mapping.
 * @returns The evaluation result.
 */
export function evaluateMember(
  memberId: string,
  metrics: Record<string, number>,
): Promise<EvaluationResult> {
  return post<EvaluationResult>(`${ACHIEVEMENTS_PATH}/evaluate`, {
    member_id: memberId,
    metrics,
  });
}

/**
 * Evaluate several members in one request.
 *
 * @param submissions - Member/metrics pairs.
 * @returns The batch evaluation result.
 */
export function evaluateBatch(
  submissions: Array<{ member_id: string; metrics: Record<string, number> }>,
): Promise<BatchEvaluationResult> {
  return post<BatchEvaluationResult>(`${ACHIEVEMENTS_PATH}/evaluate/batch`, {
    submissions,
  });
}

/**
 * Load a member's complete achievement profile.
 *
 * @param memberId - The member identifier.
 * @returns The member profile.
 */
export function getMemberAchievements(
  memberId: string,
): Promise<MemberAchievement> {
  return get<MemberAchievement>(
    `${ACHIEVEMENTS_PATH}/members/${encodeURIComponent(memberId)}`,
  );
}

/**
 * Load the achievement leaderboard.
 *
 * @param limit - Optional maximum number of entries.
 * @returns The leaderboard payload.
 */
export function getLeaderboard(limit?: number): Promise<LeaderboardResponse> {
  return get<LeaderboardResponse>(
    `${ACHIEVEMENTS_PATH}/leaderboard${buildQuery({ limit })}`,
  );
}

/**
 * Load aggregate achievement statistics.
 *
 * @returns The achievement statistics.
 */
export function getStats(): Promise<AchievementStats> {
  return get<AchievementStats>(`${ACHIEVEMENTS_PATH}/stats`);
}

/**
 * Manually grant a badge to a member.
 *
 * @param memberId - The receiving member.
 * @param badgeId - The badge identifier.
 * @param evidence - Optional evidence payload.
 * @returns The award result.
 */
export function awardBadge(
  memberId: string,
  badgeId: string,
  evidence: Record<string, unknown> = {},
): Promise<AwardResult> {
  return post<AwardResult>(
    `${ACHIEVEMENTS_PATH}/members/${encodeURIComponent(memberId)}/awards/${encodeURIComponent(badgeId)}`,
    { evidence },
  );
}

/**
 * Seed missing built-in badges.
 *
 * @returns The seeding summary.
 */
export function seedCatalogue(): Promise<SeedResult> {
  return post<SeedResult>(`${ACHIEVEMENTS_PATH}/seed`);
}

/** Grouped API adapter for consumers that prefer a single import. */
export const achievementApi = {
  listBadges,
  getBadge,
  createBadge,
  evaluateMember,
  evaluateBatch,
  getMemberAchievements,
  getLeaderboard,
  getStats,
  awardBadge,
  seedCatalogue,
};
