/**
 * Data loading and mutation state for the submission console.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { submissionsApi } from "./api";
import type {
  ChallengeOption,
  MemberOption,
  QueueSummary,
  Submission,
  SubmissionDraft,
  SubmissionFilters,
  SubmissionStats,
  ValidationRule,
} from "./types";

/** Controls the submission console screen. */
export interface SubmissionsController {
  submissions: Submission[];
  stats: SubmissionStats | null;
  rules: ValidationRule[];
  challenges: ChallengeOption[];
  members: MemberOption[];
  filters: SubmissionFilters;
  loading: boolean;
  busy: boolean;
  error: string | null;
  lastSummary: QueueSummary | null;
  setFilters: (patch: Partial<SubmissionFilters>) => void;
  refresh: () => Promise<void>;
  submitFlag: (draft: SubmissionDraft) => Promise<Submission>;
  retry: (id: string, flag?: string) => Promise<void>;
  process: () => Promise<QueueSummary>;
  clearError: () => void;
}

/** Default filters show every submission. */
export const DEFAULT_FILTERS: SubmissionFilters = {
  status: "all",
  challenge_id: "",
  member_id: "",
};

/**
 * Extract a readable message from an unknown failure.
 *
 * @param error - The thrown value.
 * @returns A message suitable for an accessible alert.
 */
function messageOf(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "The submission pipeline could not be reached.";
}

/**
 * Load and mutate submission pipeline data.
 *
 * @returns The controller consumed by the page.
 */
export function useSubmissions(): SubmissionsController {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [stats, setStats] = useState<SubmissionStats | null>(null);
  const [rules, setRules] = useState<ValidationRule[]>([]);
  const [challenges, setChallenges] = useState<ChallengeOption[]>([]);
  const [members, setMembers] = useState<MemberOption[]>([]);
  const [filters, setFiltersState] =
    useState<SubmissionFilters>(DEFAULT_FILTERS);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSummary, setLastSummary] = useState<QueueSummary | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [found, summary, configured, challengeOptions, memberOptions] =
        await Promise.all([
          submissionsApi.list(filters),
          submissionsApi.stats(),
          submissionsApi.rules(),
          submissionsApi.challenges(),
          submissionsApi.members(),
        ]);
      if (!mounted.current) return;
      setSubmissions(found);
      setStats(summary);
      setRules(configured);
      setChallenges(challengeOptions);
      setMembers(memberOptions);
      setError(null);
    } catch (cause) {
      if (mounted.current) setError(messageOf(cause));
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const setFilters = useCallback((patch: Partial<SubmissionFilters>) => {
    setFiltersState((current) => ({ ...current, ...patch }));
  }, []);

  const clearError = useCallback(() => setError(null), []);

  const submitFlag = useCallback(
    async (draft: SubmissionDraft): Promise<Submission> => {
      setBusy(true);
      try {
        const created = await submissionsApi.submit(draft);
        await submissionsApi.process();
        await refresh();
        return created;
      } catch (cause) {
        if (mounted.current) setError(messageOf(cause));
        throw cause;
      } finally {
        if (mounted.current) setBusy(false);
      }
    },
    [refresh],
  );

  const retry = useCallback(
    async (id: string, flag?: string): Promise<void> => {
      setBusy(true);
      try {
        await submissionsApi.retry(id, flag);
        await refresh();
      } catch (cause) {
        if (mounted.current) setError(messageOf(cause));
        throw cause;
      } finally {
        if (mounted.current) setBusy(false);
      }
    },
    [refresh],
  );

  const process = useCallback(async (): Promise<QueueSummary> => {
    setBusy(true);
    try {
      const summary = await submissionsApi.process();
      if (mounted.current) setLastSummary(summary);
      await refresh();
      return summary;
    } catch (cause) {
      if (mounted.current) setError(messageOf(cause));
      throw cause;
    } finally {
      if (mounted.current) setBusy(false);
    }
  }, [refresh]);

  return {
    submissions,
    stats,
    rules,
    challenges,
    members,
    filters,
    loading,
    busy,
    error,
    lastSummary,
    setFilters,
    refresh,
    submitFlag,
    retry,
    process,
    clearError,
  };
}
