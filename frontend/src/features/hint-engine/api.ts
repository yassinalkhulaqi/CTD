/** Typed API adapter for the hint engine endpoints. */

import {
  buildQuery,
  del,
  get,
  patch,
  post,
  type RequestOptions,
} from "../../api/client";
import type { Challenge, Member, Team } from "../../types";
import type {
  BudgetResetInput,
  ChallengeHintView,
  Hint,
  HintBudget,
  HintDraft,
  HintLedger,
  HintUnlock,
} from "./types";

/** Optional filters accepted by the hint list endpoint. */
export interface HintListQuery {
  challengeId?: string;
  teamId?: string;
}

/**
 * Encode a path segment once.
 *
 * @param value - The segment value.
 * @returns The encoded value.
 */
function segment(value: string): string {
  return encodeURIComponent(value);
}

/** The hint engine endpoints. */
export const hintsApi = {
  /** Return the hint catalogue, optionally filtered. */
  list(query: HintListQuery = {}, options?: RequestOptions): Promise<Hint[]> {
    const suffix = buildQuery({
      challenge_id: query.challengeId,
      team_id: query.teamId,
    });
    return get<Hint[]>(`/api/hints${suffix}`, options);
  },

  /** Author a new hint. */
  create(payload: HintDraft, options?: RequestOptions): Promise<Hint> {
    return post<Hint>("/api/hints", payload, options);
  },

  /** Edit an existing hint. */
  update(
    id: string,
    payload: Partial<HintDraft>,
    options?: RequestOptions,
  ): Promise<Hint> {
    return patch<Hint>(`/api/hints/${segment(id)}`, payload, options);
  },

  /** Delete a hint that has never been unlocked. */
  remove(id: string, options?: RequestOptions): Promise<void> {
    return del<void>(`/api/hints/${segment(id)}`, options);
  },

  /** Return a team's masked hint ladder for a challenge. */
  challengeView(
    challengeId: string,
    teamId: string,
    memberId?: string,
    options?: RequestOptions,
  ): Promise<ChallengeHintView> {
    const suffix = buildQuery({ team_id: teamId, member_id: memberId });
    return get<ChallengeHintView>(
      `/api/hints/challenges/${segment(challengeId)}${suffix}`,
      options,
    );
  },

  /** Reveal a hint and debit the team's budget. */
  unlock(
    hintId: string,
    memberId: string,
    teamId: string,
    options?: RequestOptions,
  ): Promise<HintUnlock> {
    return post<HintUnlock>(
      `/api/hints/${segment(hintId)}/unlock`,
      { member_id: memberId, team_id: teamId },
      options,
    );
  },

  /** Return a team's hint budget. */
  budget(teamId: string, options?: RequestOptions): Promise<HintBudget> {
    return get<HintBudget>(`/api/hints/budget/${segment(teamId)}`, options);
  },

  /** Clear a team's spending and provision a new window. */
  resetBudget(
    teamId: string,
    payload: BudgetResetInput = {},
    options?: RequestOptions,
  ): Promise<HintBudget> {
    return post<HintBudget>(
      `/api/hints/budget/${segment(teamId)}/reset`,
      payload,
      options,
    );
  },

  /** Return the reveal history and spend summary. */
  ledger(teamId: string, options?: RequestOptions): Promise<HintLedger> {
    return get<HintLedger>(`/api/hints/ledger/${segment(teamId)}`, options);
  },

  /** Return the teams available in the competition. */
  teams(options?: RequestOptions): Promise<Team[]> {
    return get<Team[]>("/api/teams", options);
  },

  /** Return challenges, optionally restricted to one team. */
  challenges(teamId?: string, options?: RequestOptions): Promise<Challenge[]> {
    return get<Challenge[]>(
      `/api/challenges${buildQuery({ team_id: teamId })}`,
      options,
    );
  },

  /** Return members, optionally restricted to one team. */
  members(teamId?: string, options?: RequestOptions): Promise<Member[]> {
    return get<Member[]>(
      `/api/members${buildQuery({ team_id: teamId })}`,
      options,
    );
  },
};
