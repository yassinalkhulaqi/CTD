/** Data loading and mutation hooks for the hint workspace. */

import { useCallback, useEffect, useState } from "react";
import type { Challenge, Member, Team } from "../../types";
import { hintsApi } from "./api";
import type { ChallengeHintView, HintLedger } from "./types";

/**
 * Convert an unknown rejection into a displayable message.
 *
 * @param error - The rejection value.
 * @returns A human readable message.
 */
function messageOf(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "The hint service is unavailable";
}

/** The catalogue data needed to populate the workspace selectors. */
export interface HintCatalog {
  teams: Team[];
  challenges: Challenge[];
  members: Member[];
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/** Load teams, challenges and members for the hint workspace. */
export function useHintCatalog(): HintCatalog {
  const [teams, setTeams] = useState<Team[]>([]);
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  const reload = useCallback(() => setRevision((value) => value + 1), []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([hintsApi.teams(), hintsApi.challenges(), hintsApi.members()])
      .then(([nextTeams, nextChallenges, nextMembers]) => {
        if (!active) return;
        setTeams(nextTeams);
        setChallenges(nextChallenges);
        setMembers(nextMembers);
        setError(null);
      })
      .catch((reason: unknown) => {
        if (active) setError(messageOf(reason));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [revision]);

  return { teams, challenges, members, loading, error, reload };
}

/** View state and actions for one team's hint ladder. */
export interface HintWorkspace {
  view: ChallengeHintView | null;
  ledger: HintLedger | null;
  loading: boolean;
  working: boolean;
  error: string | null;
  refresh: () => void;
  unlock: (hintId: string, memberId: string, teamId: string) => Promise<void>;
  resetBudget: (teamId: string) => Promise<void>;
}

/** Load and mutate the hint ladder of a selected challenge and team. */
export function useHintWorkspace(
  teamId: string,
  challengeId: string,
  memberId: string,
): HintWorkspace {
  const [view, setView] = useState<ChallengeHintView | null>(null);
  const [ledger, setLedger] = useState<HintLedger | null>(null);
  const [loading, setLoading] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal): Promise<void> => {
      if (!teamId || !challengeId) {
        setView(null);
        setLedger(null);
        setError(null);
        return;
      }
      setLoading(true);
      try {
        const [nextView, nextLedger] = await Promise.all([
          hintsApi.challengeView(challengeId, teamId, memberId || undefined, {
            signal,
          }),
          hintsApi.ledger(teamId, { signal }),
        ]);
        setView(nextView);
        setLedger(nextLedger);
        setError(null);
      } catch (reason) {
        if (signal?.aborted) return;
        setError(messageOf(reason));
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    [challengeId, memberId, teamId],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const refresh = useCallback(() => {
    void load();
  }, [load]);

  const unlock = useCallback(
    async (
      hintId: string,
      unlockMemberId: string,
      unlockTeamId: string,
    ): Promise<void> => {
      setWorking(true);
      try {
        await hintsApi.unlock(hintId, unlockMemberId, unlockTeamId);
        await load();
      } finally {
        setWorking(false);
      }
    },
    [load],
  );

  const resetBudget = useCallback(
    async (resetTeamId: string): Promise<void> => {
      setWorking(true);
      try {
        await hintsApi.resetBudget(resetTeamId);
        await load();
      } finally {
        setWorking(false);
      }
    },
    [load],
  );

  return {
    view,
    ledger,
    loading,
    working,
    error,
    refresh,
    unlock,
    resetBudget,
  };
}
