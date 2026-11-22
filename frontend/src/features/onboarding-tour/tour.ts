/**
 * Pure view logic of the onboarding tour.
 *
 * Keeping these helpers free of React and network concerns makes the tricky
 * parts of the wizard — ordering, resume decisions and keyboard behaviour —
 * straightforward to unit test.
 */

import type {
  Checklist,
  ChecklistItem,
  OnboardingStep,
  StateTone,
  StepState,
  TourFrame,
} from "./types";

/**
 * Return a clamped integer percentage.
 *
 * @param completed - The number of finished items.
 * @param total - The number of items in total.
 * @returns An integer between 0 and 100.
 */
export function completionPercent(completed: number, total: number): number {
  if (total <= 0) return 0;
  const ratio = Math.max(0, Math.min(completed, total)) / total;
  return Math.floor(ratio * 100);
}

/**
 * Return steps sorted by their declared order.
 *
 * @param steps - The steps to sort.
 * @returns A new sorted array.
 */
export function orderedSteps(steps: OnboardingStep[]): OnboardingStep[] {
  return [...steps].sort(
    (a, b) => a.order - b.order || a.slug.localeCompare(b.slug),
  );
}

/**
 * Return whether a step has already been resolved.
 *
 * @param step - The step to inspect.
 * @returns True when the step is complete or skipped.
 */
export function isResolved(step: OnboardingStep): boolean {
  return step.state === "complete" || step.state === "skipped";
}

/**
 * Return the first step that still needs attention.
 *
 * @param steps - The catalogue steps.
 * @returns The next step, or null when the tour is finished.
 */
export function nextStep(steps: OnboardingStep[]): OnboardingStep | null {
  return orderedSteps(steps).find((step) => !isResolved(step)) ?? null;
}

/**
 * Return a human readable label for a step state.
 *
 * @param state - The derived state.
 * @returns The label shown in the stepper and step cards.
 */
export function stateLabel(state: StepState | null): string {
  if (state === null) return "Pending";
  const labels: Record<StepState, string> = {
    locked: "Locked",
    available: "Ready",
    active: "Current",
    complete: "Completed",
    skipped: "Skipped",
  };
  return labels[state];
}

/**
 * Return the colour token associated with a step state.
 *
 * @param state - The derived state.
 * @returns A semantic tone token used by the CSS modules.
 */
export function stateTone(state: StepState | null): StateTone {
  if (state === null) return "neutral";
  const tones: Record<StepState, StateTone> = {
    locked: "neutral",
    available: "info",
    active: "accent",
    complete: "success",
    skipped: "warning",
  };
  return tones[state];
}

/**
 * Format a position string for the tour overlay.
 *
 * @param index - Zero-based index of the current step.
 * @param total - The number of steps in the tour.
 * @returns A label such as `Step 2 of 7`.
 */
export function stepPosition(index: number, total: number): string {
  return `Step ${Math.max(1, index + 1)} of ${Math.max(0, total)}`;
}

/**
 * Build a tour frame for a step identifier.
 *
 * @param steps - The ordered catalogue.
 * @param stepId - The identifier of the step to spotlight.
 * @returns The frame, or null when the identifier is unknown.
 */
export function buildTourFrame(
  steps: OnboardingStep[],
  stepId: string | null,
): TourFrame | null {
  if (stepId === null) return null;
  const ordered = orderedSteps(steps);
  const index = ordered.findIndex((step) => step.id === stepId);
  if (index < 0) return null;
  return {
    step: ordered[index],
    index,
    total: ordered.length,
    isFirst: index === 0,
    isLast: index === ordered.length - 1,
  };
}

/**
 * Translate a keyboard event key into a tour action.
 *
 * Arrow and Enter keys move through the tour, Escape closes it. Every other
 * key is ignored so typing in a focusable child stays predictable.
 *
 * @param key - The value of `KeyboardEvent.key`.
 * @returns The action to perform, or null when the key is not a shortcut.
 */
export function tourKeyboardAction(
  key: string,
): "next" | "previous" | "close" | null {
  if (key === "ArrowRight" || key === "ArrowDown" || key === "Enter")
    return "next";
  if (key === "ArrowLeft" || key === "ArrowUp") return "previous";
  if (key === "Escape") return "close";
  return null;
}

/**
 * Summarise a checklist without relying on server supplied counters.
 *
 * @param items - The checklist items.
 * @returns Completed count, total count and percentage.
 */
export function checklistSummary(items: ChecklistItem[]): {
  completed: number;
  total: number;
  percent: number;
} {
  const completed = items.filter((item) => item.done).length;
  const total = items.length;
  return { completed, total, percent: completionPercent(completed, total) };
}

/**
 * Return a short resume message derived from progress state.
 *
 * @param checklist - The setup checklist, when loaded.
 * @param percent - The onboarding completion percentage.
 * @returns A friendly sentence for the progress banner.
 */
export function resumeMessage(
  checklist: Checklist | null,
  percent: number,
): string {
  if (percent >= 100)
    return "Everything is ready. You can revisit the tour any time.";
  if (!checklist) return "Your progress will appear here once the tour loads.";
  const remaining = checklist.total - checklist.completed;
  if (remaining === 0)
    return "Checklist complete — finish the remaining tour steps.";
  return `${remaining} checklist item${remaining === 1 ? "" : "s"} left to finish.`;
}

/**
 * Return the index of a step in an ordered catalogue.
 *
 * @param steps - The catalogue steps.
 * @param stepId - The identifier to locate.
 * @returns The zero-based index, or -1 when missing.
 */
export function indexOfStep(steps: OnboardingStep[], stepId: string): number {
  return orderedSteps(steps).findIndex((step) => step.id === stepId);
}
