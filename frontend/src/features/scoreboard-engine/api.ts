/**
 * Typed HTTP adapter for the scoreboard engine endpoints.
 */

import { get, post, put } from "../../api/client";
import type {
  RankingResponse,
  ScoreBreakdown,
  ScoreRule,
  ScoreRuleDraft,
  ScoreSnapshot,
  TeamOption,
} from "./types";

/** Optional request configuration shared by every endpoint. */
interface CallOptions {
  signal?: AbortSignal;
}

/**
 * Return the teams available in the dashboard.
 *
 * @param options - Request options.
 * @returns The selectable teams.
 */
function getTeams(options: CallOptions = {}): Promise<TeamOption[]> {
  return get<TeamOption[]>("/api/teams", options);
}

/**
 * Return the live scoreboard ranking.
 *
 * @param options - Request options.
 * @returns The ranking response.
 */
function getRanking(options: CallOptions = {}): Promise<RankingResponse> {
  return get<RankingResponse>("/api/scoreboard/ranking", options);
}

/**
 * Return the effective scoring rule of a team.
 *
 * @param teamId - The team identifier.
 * @param options - Request options.
 * @returns The scoring rule.
 */
function getRule(
  teamId: string,
  options: CallOptions = {},
): Promise<ScoreRule> {
  return get<ScoreRule>(
    `/api/scoreboard/rules/${encodeURIComponent(teamId)}`,
    options,
  );
}

/**
 * Replace the scoring rule of a team.
 *
 * @param teamId - The team identifier.
 * @param draft - The edited rule values.
 * @param options - Request options.
 * @returns The stored rule.
 */
function putRule(
  teamId: string,
  draft: ScoreRuleDraft,
  options: CallOptions = {},
): Promise<ScoreRule> {
  return put<ScoreRule>(
    `/api/scoreboard/rules/${encodeURIComponent(teamId)}`,
    draft,
    options,
  );
}

/**
 * Record a new scoring snapshot for a team.
 *
 * @param teamId - The team identifier.
 * @returns The persisted snapshot.
 */
function createSnapshot(teamId: string): Promise<ScoreSnapshot> {
  return post<ScoreSnapshot>(
    `/api/scoreboard/snapshot/${encodeURIComponent(teamId)}`,
  );
}

/**
 * Return the itemised score breakdown of a team.
 *
 * @param teamId - The team identifier.
 * @param options - Request options.
 * @returns The score breakdown.
 */
function getBreakdown(
  teamId: string,
  options: CallOptions = {},
): Promise<ScoreBreakdown> {
  return get<ScoreBreakdown>(
    `/api/scoreboard/teams/${encodeURIComponent(teamId)}/breakdown`,
    options,
  );
}

/**
 * Return the snapshot history of a team.
 *
 * @param teamId - The team identifier.
 * @param limit - Maximum number of snapshots to return.
 * @param options - Request options.
 * @returns Snapshots, newest first.
 */
function getSnapshots(
  teamId: string,
  limit = 30,
  options: CallOptions = {},
): Promise<ScoreSnapshot[]> {
  return get<ScoreSnapshot[]>(
    `/api/scoreboard/snapshots/${encodeURIComponent(teamId)}?limit=${limit}`,
    options,
  );
}

/** The scoreboard HTTP endpoints. */
export const scoreboardApi = {
  getTeams,
  getRanking,
  getRule,
  putRule,
  createSnapshot,
  getBreakdown,
  getSnapshots,
};
