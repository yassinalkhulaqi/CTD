/**
 * Data loading and mutation hooks for the scoreboard page.
 */

import { useCallback, useEffect, useState } from "react";
import { toApiError } from "../../api/client";
import { scoreboardApi } from "./api";
import type {
  RankingResponse,
  ScoreBreakdown,
  ScoreRule,
  ScoreRuleDraft,
  ScoreSnapshot,
  TeamOption,
} from "./types";

/** State returned by the overview hook. */
export interface ScoreboardOverviewState {
  teams: TeamOption[];
  ranking: RankingResponse | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/**
 * Load the team list and the live ranking.
 *
 * @returns The overview state and a reload callback.
 */
export function useScoreboardOverview(): ScoreboardOverviewState {
  const [teams, setTeams] = useState<TeamOption[]>([]);
  const [ranking, setRanking] = useState<RankingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  const reload = useCallback(() => setRevision((value) => value + 1), []);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    Promise.all([
      scoreboardApi.getTeams({ signal: controller.signal }),
      scoreboardApi.getRanking({ signal: controller.signal }),
    ])
      .then(([loadedTeams, loadedRanking]) => {
        if (!active) return;
        setTeams(loadedTeams);
        setRanking(loadedRanking);
        setLoading(false);
      })
      .catch((cause: unknown) => {
        if (!active || controller.signal.aborted) return;
        setError(toApiError(cause).message);
        setLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [revision]);

  return { teams, ranking, loading, error, reload };
}

/** State returned by the per-team hook. */
export interface TeamScoreboardState {
  rule: ScoreRule | null;
  breakdown: ScoreBreakdown | null;
  snapshots: ScoreSnapshot[];
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/**
 * Load the rule, breakdown and history of one team.
 *
 * @param teamId - The selected team, or `null` before a selection exists.
 * @param revision - A counter incremented after mutations.
 * @returns The team state and a reload callback.
 */
export function useTeamScoreboard(
  teamId: string | null,
  revision = 0,
): TeamScoreboardState {
  const [rule, setRule] = useState<ScoreRule | null>(null);
  const [breakdown, setBreakdown] = useState<ScoreBreakdown | null>(null);
  const [snapshots, setSnapshots] = useState<ScoreSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [localRevision, setLocalRevision] = useState(0);

  const reload = useCallback(() => setLocalRevision((value) => value + 1), []);

  useEffect(() => {
    if (!teamId) {
      setRule(null);
      setBreakdown(null);
      setSnapshots([]);
      setLoading(false);
      setError(null);
      return;
    }

    let active = true;
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    Promise.all([
      scoreboardApi.getRule(teamId, { signal: controller.signal }),
      scoreboardApi.getBreakdown(teamId, { signal: controller.signal }),
      scoreboardApi.getSnapshots(teamId, 30, { signal: controller.signal }),
    ])
      .then(([loadedRule, loadedBreakdown, loadedSnapshots]) => {
        if (!active) return;
        setRule(loadedRule);
        setBreakdown(loadedBreakdown);
        setSnapshots(loadedSnapshots);
        setLoading(false);
      })
      .catch((cause: unknown) => {
        if (!active || controller.signal.aborted) return;
        setError(toApiError(cause).message);
        setLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [teamId, revision, localRevision]);

  return { rule, breakdown, snapshots, loading, error, reload };
}

/** State returned by the mutation hook. */
export interface ScoreboardActionsState {
  saveRule: (draft: ScoreRuleDraft) => Promise<boolean>;
  captureSnapshot: () => Promise<boolean>;
  busy: boolean;
  error: string | null;
  notice: string | null;
  dismissNotice: () => void;
}

/**
 * Provide rule saving and snapshot creation with status feedback.
 *
 * @param teamId - The selected team.
 * @param onComplete - Called after a successful mutation.
 * @returns The action callbacks and their status.
 */
export function useScoreboardActions(
  teamId: string | null,
  onComplete: () => void,
): ScoreboardActionsState {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const dismissNotice = useCallback(() => setNotice(null), []);

  const run = useCallback(
    async (
      operation: () => Promise<void>,
      success: string,
    ): Promise<boolean> => {
      if (!teamId) return false;
      setBusy(true);
      setError(null);
      setNotice(null);
      try {
        await operation();
        setNotice(success);
        onComplete();
        return true;
      } catch (cause) {
        setError(toApiError(cause).message);
        return false;
      } finally {
        setBusy(false);
      }
    },
    [teamId, onComplete],
  );

  const saveRule = useCallback(
    (draft: ScoreRuleDraft) =>
      run(async () => {
        await scoreboardApi.putRule(teamId ?? "", draft);
      }, "Scoring policy saved."),
    [run, teamId],
  );

  const captureSnapshot = useCallback(
    () =>
      run(async () => {
        await scoreboardApi.createSnapshot(teamId ?? "");
      }, "Snapshot recorded."),
    [run, teamId],
  );

  return { saveRule, captureSnapshot, busy, error, notice, dismissNotice };
}
