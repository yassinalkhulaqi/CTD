/**
 * Typed HTTP adapter of the onboarding tour feature.
 */

import { get, post, put } from "../../api/client";
import type {
  Checklist,
  ChecklistItemInput,
  OnboardingStep,
  ProgressSummary,
  ResetResponse,
  StepActionResponse,
  TargetCheckResponse,
} from "./types";

/** Request options accepted by every endpoint. */
interface CallOptions {
  signal?: AbortSignal;
}

/**
 * Append the user identifier to a URL.
 *
 * @param path - The API path.
 * @param userId - The user whose state is addressed.
 * @returns The encoded URL.
 */
function userPath(path: string, userId: string): string {
  return `${path}?user_id=${encodeURIComponent(userId)}`;
}

/** Endpoints of the onboarding wizard. */
export const onboardingApi = {
  /**
   * Return the ordered step catalogue with derived states.
   *
   * @param userId - The user whose states are derived.
   * @param options - Request options.
   * @returns The catalogue steps.
   */
  listSteps(
    userId: string,
    options: CallOptions = {},
  ): Promise<OnboardingStep[]> {
    return get<OnboardingStep[]>(
      userPath("/api/onboarding/steps", userId),
      options,
    );
  },

  /**
   * Return the progress summary of a user.
   *
   * @param userId - The user identifier.
   * @param options - Request options.
   * @returns The summary payload.
   */
  getProgress(
    userId: string,
    options: CallOptions = {},
  ): Promise<ProgressSummary> {
    return get<ProgressSummary>(
      userPath("/api/onboarding/progress", userId),
      options,
    );
  },

  /**
   * Return the next actionable step.
   *
   * @param userId - The user identifier.
   * @param options - Request options.
   * @returns The next step, or null when the tour is complete.
   */
  getNext(
    userId: string,
    options: CallOptions = {},
  ): Promise<OnboardingStep | null> {
    return get<OnboardingStep | null>(
      userPath("/api/onboarding/next", userId),
      options,
    );
  },

  /**
   * Mark a step complete.
   *
   * @param stepId - Identifier, slug or completion key of the step.
   * @param userId - The user identifier.
   * @returns The action result with a refreshed summary.
   */
  completeStep(
    stepId: string,
    userId: string,
    options: CallOptions = {},
  ): Promise<StepActionResponse> {
    return post<StepActionResponse>(
      userPath(
        `/api/onboarding/steps/${encodeURIComponent(stepId)}/complete`,
        userId,
      ),
      undefined,
      options,
    );
  },

  /**
   * Skip a step.
   *
   * @param stepId - Identifier, slug or completion key of the step.
   * @param userId - The user identifier.
   * @returns The action result with a refreshed summary.
   */
  skipStep(
    stepId: string,
    userId: string,
    options: CallOptions = {},
  ): Promise<StepActionResponse> {
    return post<StepActionResponse>(
      userPath(
        `/api/onboarding/steps/${encodeURIComponent(stepId)}/skip`,
        userId,
      ),
      undefined,
      options,
    );
  },

  /**
   * Return the setup checklist of a user.
   *
   * @param userId - The user identifier.
   * @param options - Request options.
   * @returns The checklist.
   */
  getChecklist(userId: string, options: CallOptions = {}): Promise<Checklist> {
    return get<Checklist>(
      userPath("/api/onboarding/checklist", userId),
      options,
    );
  },

  /**
   * Replace the setup checklist.
   *
   * @param userId - The user identifier.
   * @param items - The replacement items.
   * @returns The saved checklist.
   */
  putChecklist(
    userId: string,
    items: ChecklistItemInput[],
    options: CallOptions = {},
  ): Promise<Checklist> {
    return put<Checklist>(
      userPath("/api/onboarding/checklist", userId),
      { items },
      options,
    );
  },

  /**
   * Tick or untick one checklist item.
   *
   * @param userId - The user identifier.
   * @param itemId - The item identifier.
   * @param done - The desired state.
   * @returns The updated checklist.
   */
  setChecklistItem(
    userId: string,
    itemId: string,
    done: boolean,
    options: CallOptions = {},
  ): Promise<Checklist> {
    return put<Checklist>(
      userPath(
        `/api/onboarding/checklist/${encodeURIComponent(itemId)}`,
        userId,
      ),
      { done },
      options,
    );
  },

  /**
   * Reset onboarding progress and restore the default checklist.
   *
   * @param userId - The user identifier.
   * @returns The reset result.
   */
  reset(userId: string, options: CallOptions = {}): Promise<ResetResponse> {
    return post<ResetResponse>(
      userPath("/api/onboarding/reset", userId),
      undefined,
      options,
    );
  },

  /**
   * Validate a spotlight target against the safe selector grammar.
   *
   * @param target - The target string to check.
   * @returns The validation result.
   */
  checkTarget(
    target: string,
    options: CallOptions = {},
  ): Promise<TargetCheckResponse> {
    return post<TargetCheckResponse>(
      "/api/onboarding/targets/check",
      { target },
      options,
    );
  },
};
