/**
 * Typed API adapter of the submission pipeline feature.
 */

import { buildQuery, get, post } from "../../api/client";
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

/** Request options accepted by every adapter method. */
interface Options {
  signal?: AbortSignal;
}

/** Payload used to create a validation rule. */
export type RuleDraft = Pick<
  ValidationRule,
  "name" | "pattern" | "description" | "enabled" | "priority" | "kind"
>;

/** The submission pipeline endpoints. */
export const submissionsApi = {
  /**
   * List submissions using the active filters.
   *
   * @param filters - Status, challenge and member filters.
   * @param options - Request options.
   * @returns The matching submissions, newest first.
   */
  list(filters: SubmissionFilters, options?: Options): Promise<Submission[]> {
    const query = buildQuery({
      status: filters.status === "all" ? undefined : filters.status,
      challenge_id: filters.challenge_id,
      member_id: filters.member_id,
      limit: 200,
    });
    return get<Submission[]>(`/api/submissions${query}`, options);
  },

  /**
   * Return one submission by identifier.
   *
   * @param id - The submission identifier.
   * @param options - Request options.
   * @returns The submission.
   */
  get(id: string, options?: Options): Promise<Submission> {
    return get<Submission>(
      `/api/submissions/${encodeURIComponent(id)}`,
      options,
    );
  },

  /**
   * Submit a flag for validation.
   *
   * @param draft - The challenge, member and flag values.
   * @param options - Request options.
   * @returns The created queued submission.
   */
  submit(draft: SubmissionDraft, options?: Options): Promise<Submission> {
    return post<Submission>("/api/submissions", draft, options);
  },

  /**
   * Retry a rejected submission, optionally with a corrected flag.
   *
   * @param id - The submission identifier.
   * @param flag - An optional replacement flag.
   * @param options - Request options.
   * @returns The rescheduled submission.
   */
  retry(id: string, flag?: string, options?: Options): Promise<Submission> {
    return post<Submission>(
      `/api/submissions/${encodeURIComponent(id)}/retry`,
      flag ? { flag } : {},
      options,
    );
  },

  /**
   * Process the queue and return a run summary.
   *
   * @param limit - Maximum number of submissions to process.
   * @param options - Request options.
   * @returns The summary of the pass.
   */
  process(limit: number = 100, options?: Options): Promise<QueueSummary> {
    return post<QueueSummary>("/api/submissions/process", { limit }, options);
  },

  /**
   * Return the aggregate pipeline statistics.
   *
   * @param options - Request options.
   * @returns The statistics.
   */
  stats(options?: Options): Promise<SubmissionStats> {
    return get<SubmissionStats>("/api/submissions/stats", options);
  },

  /**
   * Return every configured validation rule.
   *
   * @param options - Request options.
   * @returns The rules.
   */
  rules(options?: Options): Promise<ValidationRule[]> {
    return get<ValidationRule[]>("/api/submissions/rules", options);
  },

  /**
   * Create a validation rule.
   *
   * @param draft - The rule definition.
   * @param options - Request options.
   * @returns The persisted rule.
   */
  createRule(draft: RuleDraft, options?: Options): Promise<ValidationRule> {
    return post<ValidationRule>("/api/submissions/rules", draft, options);
  },

  /**
   * Return the challenges available in the selector.
   *
   * @param options - Request options.
   * @returns Challenge options.
   */
  challenges(options?: Options): Promise<ChallengeOption[]> {
    return get<ChallengeOption[]>("/api/challenges", options);
  },

  /**
   * Return the members available in the selector.
   *
   * @param options - Request options.
   * @returns Member options.
   */
  members(options?: Options): Promise<MemberOption[]> {
    return get<MemberOption[]>("/api/members", options);
  },
};
