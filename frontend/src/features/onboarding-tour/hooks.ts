/**
 * Data loading and mutation hooks of the onboarding tour.
 */

import { useCallback } from "react";
import { useMutation, useQuery } from "../../api";
import { queryKey } from "../../api/cache";
import { onboardingApi } from "./api";
import type { Checklist, ProgressSummary } from "./types";

/**
 * Load the step catalogue for a user.
 *
 * @param userId - The user whose step states are derived.
 * @returns The query state.
 */
export function useOnboardingSteps(userId: string) {
  const fetcher = useCallback(
    (signal: AbortSignal) => onboardingApi.listSteps(userId, { signal }),
    [userId],
  );
  return useQuery({
    key: queryKey("onboarding:steps", { userId }),
    fetcher,
    staleTime: 30_000,
  });
}

/**
 * Load the progress summary of a user.
 *
 * @param userId - The user identifier.
 * @returns The query state.
 */
export function useOnboardingProgress(userId: string) {
  const fetcher = useCallback(
    (signal: AbortSignal) => onboardingApi.getProgress(userId, { signal }),
    [userId],
  );
  return useQuery({
    key: queryKey("onboarding:progress", { userId }),
    fetcher,
    staleTime: 15_000,
  });
}

/**
 * Combine the catalogue and progress queries used by the wizard page.
 *
 * @param userId - The user identifier.
 * @returns The combined loading state and data.
 */
export function useOnboarding(userId: string) {
  const stepsQuery = useOnboardingSteps(userId);
  const progressQuery = useOnboardingProgress(userId);
  const progress = progressQuery.data;
  const steps = progress?.steps ?? stepsQuery.data ?? [];
  return {
    steps,
    progress,
    isLoading: stepsQuery.isLoading || progressQuery.isLoading,
    error: progressQuery.error ?? stepsQuery.error,
    refetch: async () => {
      await Promise.all([stepsQuery.refetch(), progressQuery.refetch()]);
    },
  };
}

/** Input accepted by the step completion mutation. */
export interface StepMutationInput {
  stepId: string;
}

/**
 * Return the mutation used to complete a step.
 *
 * @param userId - The user identifier.
 * @returns The mutation state.
 */
export function useCompleteStep(userId: string) {
  return useMutation<StepMutationInput, ProgressSummary>({
    mutationFn: (input) =>
      onboardingApi
        .completeStep(input.stepId, userId)
        .then((result) => result.progress),
    invalidatesPrefixes: [queryKey("onboarding")],
  });
}

/**
 * Return the mutation used to skip a step.
 *
 * @param userId - The user identifier.
 * @returns The mutation state.
 */
export function useSkipStep(userId: string) {
  return useMutation<StepMutationInput, ProgressSummary>({
    mutationFn: (input) =>
      onboardingApi
        .skipStep(input.stepId, userId)
        .then((result) => result.progress),
    invalidatesPrefixes: [queryKey("onboarding")],
  });
}

/** Input accepted by the checklist toggle mutation. */
export interface ChecklistToggleInput {
  itemId: string;
  done: boolean;
}

/**
 * Return the mutation used to toggle a checklist item.
 *
 * @param userId - The user identifier.
 * @returns The mutation state.
 */
export function useToggleChecklistItem(userId: string) {
  return useMutation<ChecklistToggleInput, Checklist>({
    mutationFn: (input) =>
      onboardingApi.setChecklistItem(userId, input.itemId, input.done),
    invalidatesPrefixes: [queryKey("onboarding")],
  });
}

/**
 * Return the mutation used to reset onboarding progress.
 *
 * @param userId - The user identifier.
 * @returns The mutation state.
 */
export function useResetOnboarding(userId: string) {
  return useMutation<void, ProgressSummary>({
    mutationFn: () =>
      onboardingApi.reset(userId).then((result) => result.progress),
    invalidatesPrefixes: [queryKey("onboarding")],
  });
}
