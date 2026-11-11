/**
 * Typed endpoint definitions for every dashboard resource.
 */

import { buildQuery, del, get, patch, post, put, type RequestOptions } from "./client";
import type {
  ActivityEvent,
  Challenge,
  ChallengeCategory,
  ChallengeStatus,
  CompetitionStatus,
  Difficulty,
  Member,
  MemberContribution,
  OverviewStats,
  Solve,
  Team,
  TeamScore,
} from "../types";

/** Query parameters accepted by the team endpoints. */
export interface TeamQuery {
  /** Restrict the result to a single team. */
  teamId?: string;
}

/** Query parameters accepted by the challenge endpoints. */
export interface ChallengeQuery {
  /** Restrict the result to a single team. */
  teamId?: string;
  /** Restrict the result to a single category. */
  category?: ChallengeCategory;
  /** Restrict the result to a single lifecycle status. */
  status?: ChallengeStatus;
}

/** Query parameters accepted by the solve endpoints. */
export interface SolveQuery {
  /** Restrict the result to a single member. */
  memberId?: string;
  /** Restrict the result to a single challenge. */
  challengeId?: string;
  /** Restrict the result to a single team. */
  teamId?: string;
}

/** The payload used to create a team. */
export interface TeamCreateInput {
  name: string;
  slug?: string;
  color?: string;
  description?: string;
}

/** The payload used to update a team. */
export interface TeamUpdateInput {
  name?: string;
  color?: string;
  description?: string;
}

/** The payload used to create a member. */
export interface MemberCreateInput {
  team_id: string;
  handle: string;
  display_name?: string;
  role?: string;
}

/** The payload used to update a member. */
export interface MemberUpdateInput {
  handle?: string;
  display_name?: string;
  role?: string;
}

/** The payload used to create a challenge. */
export interface ChallengeCreateInput {
  team_id: string;
  title: string;
  category: ChallengeCategory;
  difficulty: Difficulty;
  points?: number;
  description?: string;
  status?: ChallengeStatus;
  tags?: string[];
  starts_at?: string | null;
  ends_at?: string | null;
}

/** The payload used to update a challenge. */
export interface ChallengeUpdateInput {
  title?: string;
  category?: ChallengeCategory;
  difficulty?: Difficulty;
  points?: number;
  description?: string;
  status?: ChallengeStatus;
  tags?: string[];
  starts_at?: string | null;
  ends_at?: string | null;
}

/** The payload used to record a solve. */
export interface SolveCreateInput {
  challenge_id: string;
  member_id: string;
  flag?: string;
  points_awarded?: number | null;
}

/** The teams endpoints. */
export const teamsApi = {
  /**
   * Return every team.
   *
   * @param options - Request options.
   * @returns The teams.
   */
  list(options?: RequestOptions): Promise<Team[]> {
    return get<Team[]>("/api/teams", options);
  },

  /**
   * Return the aggregated leaderboard.
   *
   * @param options - Request options.
   * @returns The leaderboard rows.
   */
  scoreboard(options?: RequestOptions): Promise<TeamScore[]> {
    return get<TeamScore[]>("/api/teams/scoreboard", options);
  },

  /**
   * Return a single team.
   *
   * @param teamId - The identifier of the team.
   * @param options - Request options.
   * @returns The team.
   */
  get(teamId: string, options?: RequestOptions): Promise<Team> {
    return get<Team>(`/api/teams/${encodeURIComponent(teamId)}`, options);
  },

  /**
   * Create a team.
   *
   * @param payload - The team payload.
   * @param options - Request options.
   * @returns The created team.
   */
  create(payload: TeamCreateInput, options?: RequestOptions): Promise<Team> {
    return post<Team>("/api/teams", payload, options);
  },

  /**
   * Update a team.
   *
   * @param teamId - The identifier of the team.
   * @param payload - The fields to update.
   * @param options - Request options.
   * @returns The updated team.
   */
  update(teamId: string, payload: TeamUpdateInput, options?: RequestOptions): Promise<Team> {
    return patch<Team>(`/api/teams/${encodeURIComponent(teamId)}`, payload, options);
  },

  /**
   * Delete a team.
   *
   * @param teamId - The identifier of the team.
   * @param options - Request options.
   * @returns A promise resolved when the team was removed.
   */
  remove(teamId: string, options?: RequestOptions): Promise<void> {
    return del<void>(`/api/teams/${encodeURIComponent(teamId)}`, options);
  },
};

/** The members endpoints. */
export const membersApi = {
  /**
   * Return every member.
   *
   * @param query - Optional filters.
   * @param options - Request options.
   * @returns The members.
   */
  list(query?: TeamQuery, options?: RequestOptions): Promise<Member[]> {
    const search = buildQuery({ team_id: query?.teamId });
    return get<Member[]>(`/api/members${search}`, options);
  },

  /**
   * Return the per-member contribution statistics.
   *
   * @param query - Optional filters.
   * @param options - Request options.
   * @returns The contributions.
   */
  contributions(query?: TeamQuery, options?: RequestOptions): Promise<MemberContribution[]> {
    const search = buildQuery({ team_id: query?.teamId });
    return get<MemberContribution[]>(`/api/members/contributions${search}`, options);
  },

  /**
   * Return a single member.
   *
   * @param memberId - The identifier of the member.
   * @param options - Request options.
   * @returns The member.
   */
  get(memberId: string, options?: RequestOptions): Promise<Member> {
    return get<Member>(`/api/members/${encodeURIComponent(memberId)}`, options);
  },

  /**
   * Create a member.
   *
   * @param payload - The member payload.
   * @param options - Request options.
   * @returns The created member.
   */
  create(payload: MemberCreateInput, options?: RequestOptions): Promise<Member> {
    return post<Member>("/api/members", payload, options);
  },

  /**
   * Update a member.
   *
   * @param memberId - The identifier of the member.
   * @param payload - The fields to update.
   * @param options - Request options.
   * @returns The updated member.
   */
  update(
    memberId: string,
    payload: MemberUpdateInput,
    options?: RequestOptions,
  ): Promise<Member> {
    return patch<Member>(`/api/members/${encodeURIComponent(memberId)}`, payload, options);
  },

  /**
   * Update the presence of a member.
   *
   * @param memberId - The identifier of the member.
   * @param presence - The new presence.
   * @param options - Request options.
   * @returns The updated member.
   */
  setPresence(
    memberId: string,
    presence: "online" | "away" | "offline",
    options?: RequestOptions,
  ): Promise<Member> {
    return put<Member>(
      `/api/members/${encodeURIComponent(memberId)}/presence`,
      { presence },
      options,
    );
  },

  /**
   * Delete a member.
   *
   * @param memberId - The identifier of the member.
   * @param options - Request options.
   * @returns A promise resolved when the member was removed.
   */
  remove(memberId: string, options?: RequestOptions): Promise<void> {
    return del<void>(`/api/members/${encodeURIComponent(memberId)}`, options);
  },
};

/** The challenges endpoints. */
export const challengesApi = {
  /**
   * Return the challenges matching the filters.
   *
   * @param query - Optional filters.
   * @param options - Request options.
   * @returns The challenges.
   */
  list(query?: ChallengeQuery, options?: RequestOptions): Promise<Challenge[]> {
    const search = buildQuery({
      team_id: query?.teamId,
      category: query?.category,
      status: query?.status,
    });
    return get<Challenge[]>(`/api/challenges${search}`, options);
  },

  /**
   * Return the challenge board grouped by lifecycle status.
   *
   * @param teamId - The identifier of the team.
   * @param options - Request options.
   * @returns The board.
   */
  board(teamId: string, options?: RequestOptions): Promise<Record<string, Challenge[]>> {
    const search = buildQuery({ team_id: teamId });
    return get<Record<string, Challenge[]>>(`/api/challenges/board${search}`, options);
  },

  /**
   * Return a single challenge.
   *
   * @param challengeId - The identifier of the challenge.
   * @param options - Request options.
   * @returns The challenge.
   */
  get(challengeId: string, options?: RequestOptions): Promise<Challenge> {
    return get<Challenge>(`/api/challenges/${encodeURIComponent(challengeId)}`, options);
  },

  /**
   * Create a challenge.
   *
   * @param payload - The challenge payload.
   * @param options - Request options.
   * @returns The created challenge.
   */
  create(payload: ChallengeCreateInput, options?: RequestOptions): Promise<Challenge> {
    return post<Challenge>("/api/challenges", payload, options);
  },

  /**
   * Update a challenge.
   *
   * @param challengeId - The identifier of the challenge.
   * @param payload - The fields to update.
   * @param options - Request options.
   * @returns The updated challenge.
   */
  update(
    challengeId: string,
    payload: ChallengeUpdateInput,
    options?: RequestOptions,
  ): Promise<Challenge> {
    return patch<Challenge>(
      `/api/challenges/${encodeURIComponent(challengeId)}`,
      payload,
      options,
    );
  },

  /**
   * Move a challenge between lifecycle states.
   *
   * @param challengeId - The identifier of the challenge.
   * @param status - The new status.
   * @param options - Request options.
   * @returns The updated challenge.
   */
  setStatus(
    challengeId: string,
    status: ChallengeStatus,
    options?: RequestOptions,
  ): Promise<Challenge> {
    return put<Challenge>(
      `/api/challenges/${encodeURIComponent(challengeId)}/status`,
      { status },
      options,
    );
  },

  /**
   * Delete a challenge.
   *
   * @param challengeId - The identifier of the challenge.
   * @param options - Request options.
   * @returns A promise resolved when the challenge was removed.
   */
  remove(challengeId: string, options?: RequestOptions): Promise<void> {
    return del<void>(`/api/challenges/${encodeURIComponent(challengeId)}`, options);
  },
};

/** The solves endpoints. */
export const solvesApi = {
  /**
   * Return the solves matching the filters.
   *
   * @param query - Optional filters.
   * @param options - Request options.
   * @returns The solves.
   */
  list(query?: SolveQuery, options?: RequestOptions): Promise<Solve[]> {
    const search = buildQuery({
      member_id: query?.memberId,
      challenge_id: query?.challengeId,
      team_id: query?.teamId,
    });
    return get<Solve[]>(`/api/solves${search}`, options);
  },

  /**
   * Return the hourly solve velocity of the trailing 24 hours.
   *
   * @param teamId - Optional team filter.
   * @param options - Request options.
   * @returns The hourly buckets.
   */
  velocity(teamId?: string, options?: RequestOptions): Promise<number[]> {
    const search = buildQuery({ team_id: teamId });
    return get<number[]>(`/api/solves/velocity${search}`, options);
  },

  /**
   * Record a solve.
   *
   * @param payload - The solve payload.
   * @param options - Request options.
   * @returns The recorded solve.
   */
  create(payload: SolveCreateInput, options?: RequestOptions): Promise<Solve> {
    return post<Solve>("/api/solves", payload, options);
  },

  /**
   * Withdraw a solve.
   *
   * @param solveId - The identifier of the solve.
   * @param options - Request options.
   * @returns A promise resolved when the solve was withdrawn.
   */
  remove(solveId: string, options?: RequestOptions): Promise<void> {
    return del<void>(`/api/solves/${encodeURIComponent(solveId)}`, options);
  },
};

/** The statistics endpoints. */
export const statsApi = {
  /**
   * Return the headline counters.
   *
   * @param options - Request options.
   * @returns The overview counters.
   */
  overview(options?: RequestOptions): Promise<OverviewStats> {
    return get<OverviewStats>("/api/stats/overview", options);
  },

  /**
   * Return the per-category statistics.
   *
   * @param options - Request options.
   * @returns The category statistics.
   */
  categories(options?: RequestOptions) {
    return get<
      Array<{
        category: ChallengeCategory;
        label: string;
        accent: string;
        challenges: number;
        solves: number;
        solve_rate: number;
        unsolved: number;
      }>
    >("/api/stats/categories", options);
  },

  /**
   * Return the team leaderboard.
   *
   * @param options - Request options.
   * @returns The leaderboard rows.
   */
  leaderboard(options?: RequestOptions): Promise<TeamScore[]> {
    return get<TeamScore[]>("/api/stats/leaderboard", options);
  },

  /**
   * Return the hourly solve timeline.
   *
   * @param hours - The size of the window in hours.
   * @param teamId - Optional team filter.
   * @param options - Request options.
   * @returns The hourly buckets.
   */
  timeline(hours = 24, teamId?: string, options?: RequestOptions): Promise<number[]> {
    const search = buildQuery({ hours, team_id: teamId });
    return get<number[]>(`/api/stats/timeline${search}`, options);
  },

  /**
   * Return the weekday and hour heatmap.
   *
   * @param teamId - Optional team filter.
   * @param options - Request options.
   * @returns The 7x24 matrix.
   */
  heatmap(teamId?: string, options?: RequestOptions): Promise<number[][]> {
    const search = buildQuery({ team_id: teamId });
    return get<number[][]>(`/api/stats/heatmap${search}`, options);
  },

  /**
   * Return the solve counts grouped by difficulty.
   *
   * @param options - Request options.
   * @returns The difficulty breakdown.
   */
  difficulty(options?: RequestOptions): Promise<Record<string, number>> {
    return get<Record<string, number>>("/api/stats/difficulty", options);
  },

  /**
   * Return the competition timing envelope.
   *
   * @param options - Request options.
   * @returns The competition status.
   */
  competition(options?: RequestOptions): Promise<CompetitionStatus> {
    return get<CompetitionStatus>("/api/stats/competition", options);
  },

  /**
   * Return the recent activity feed.
   *
   * @param limit - The maximum number of events.
   * @param options - Request options.
   * @returns The activity events.
   */
  activity(limit = 20, options?: RequestOptions): Promise<ActivityEvent[]> {
    const search = buildQuery({ limit });
    return get<ActivityEvent[]>(`/api/stats/activity${search}`, options);
  },

  /**
   * Return the raw event feed.
   *
   * @param limit - The maximum number of events.
   * @param teamId - Optional team filter.
   * @param options - Request options.
   * @returns The events.
   */
  events(limit = 50, teamId?: string, options?: RequestOptions): Promise<ActivityEvent[]> {
    const search = buildQuery({ limit, team_id: teamId });
    return get<ActivityEvent[]>(`/api/stats/events${search}`, options);
  },
};

/** The aggregated dashboard payload. */
export interface DashboardSnapshot {
  overview: OverviewStats;
  scoreboard: TeamScore[];
  categories: Array<{
    category: ChallengeCategory;
    label: string;
    accent: string;
    challenges: number;
    solves: number;
    solve_rate: number;
    unsolved: number;
  }>;
  contributions: MemberContribution[];
  recent_events: ActivityEvent[];
  competition_seconds_remaining: number;
  generated_at: string;
}

/** The dashboard aggregation endpoints. */
export const dashboardApi = {
  /**
   * Return the aggregated dashboard payload.
   *
   * @param teamId - Optional team filter.
   * @param options - Request options.
   * @returns The snapshot.
   */
  snapshot(teamId?: string, options?: RequestOptions): Promise<DashboardSnapshot> {
    const search = buildQuery({ team_id: teamId });
    return get<DashboardSnapshot>(`/api/dashboard${search}`, options);
  },
};
