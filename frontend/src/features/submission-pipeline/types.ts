/**
 * Domain types and view models of the submission pipeline feature.
 */

/** Every state a submission can occupy. */
export type SubmissionStatus =
  "queued" | "validating" | "accepted" | "rejected" | "retrying";

/** A flag submission as returned by the API. */
export interface Submission {
  id: string;
  challenge_id: string;
  member_id: string;
  flag_cipher: string;
  status: SubmissionStatus;
  attempts: number;
  created_at: string;
  completed_at: string | null;
  error: string | null;
  accepted: boolean;
  stage_index: number;
  is_pending: boolean;
}

/** Per-member submission totals. */
export interface MemberSubmissionStats {
  member_id: string;
  total: number;
  accepted: number;
  rejected: number;
  pending: number;
  acceptance_rate: number;
}

/** Aggregate pipeline statistics. */
export interface SubmissionStats {
  total: number;
  by_status: Record<string, number>;
  by_member: MemberSubmissionStats[];
  acceptance_rate: number;
  average_attempts: number;
  pending: number;
  retries: number;
  attempts: number;
}

/** Outcome of one queue processing pass. */
export interface QueueSummary {
  processed: number;
  accepted: number;
  rejected: number;
  skipped: number;
  remaining: number;
  total: number;
  success_rate: number;
}

/** A configured validation rule. */
export interface ValidationRule {
  id: string;
  name: string;
  pattern: string;
  description: string;
  enabled: boolean;
  priority: number;
  kind: "format" | "acceptance";
}

/** A challenge shown in the submission console selector. */
export interface ChallengeOption {
  id: string;
  title: string;
  team_id: string;
  category?: string;
}

/** A member shown in the submission console selector. */
export interface MemberOption {
  id: string;
  handle: string;
  display_name: string;
  team_id: string;
}

/** The values entered in the submission form. */
export interface SubmissionDraft {
  challenge_id: string;
  member_id: string;
  flag: string;
}

/** Filters applied to the live submission log. */
export interface SubmissionFilters {
  status: SubmissionStatus | "all";
  challenge_id: string;
  member_id: string;
}

/** Result of validating a flag in the browser before submission. */
export interface ValidationResult {
  valid: boolean;
  code: string;
  message: string;
}

/** Static presentation metadata for a submission status. */
export interface StatusMeta {
  label: string;
  tone: "neutral" | "info" | "success" | "danger" | "warning";
  description: string;
}

/** Presentation metadata of every status. */
export const STATUS_META: Record<SubmissionStatus, StatusMeta> = {
  queued: {
    label: "Queued",
    tone: "neutral",
    description: "Accepted into the pipeline, waiting for validation.",
  },
  validating: {
    label: "Validating",
    tone: "info",
    description: "Format and answer checks are running.",
  },
  accepted: {
    label: "Accepted",
    tone: "success",
    description: "The flag matched the seeded challenge answer.",
  },
  rejected: {
    label: "Rejected",
    tone: "danger",
    description: "Validation failed; the submission may be retried.",
  },
  retrying: {
    label: "Retrying",
    tone: "warning",
    description: "A retry is scheduled after the backoff window.",
  },
};

/** The three stages shown in the visual pipeline. */
export const PIPELINE_STAGES: SubmissionStatus[] = [
  "queued",
  "validating",
  "accepted",
];

/** Human readable error codes returned by the pipeline. */
export const ERROR_MESSAGES: Record<string, string> = {
  format_empty: "Enter a flag before submitting.",
  format_invalid: "The flag does not satisfy an enabled validation rule.",
  format_too_long: "The flag is longer than the allowed 256 characters.",
  flag_mismatch: "The flag did not match the challenge answer.",
  validation_error: "The flag could not be validated.",
  conflict: "This flag was already submitted for the challenge.",
};
