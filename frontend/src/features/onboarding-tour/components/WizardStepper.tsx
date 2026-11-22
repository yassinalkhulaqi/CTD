/**
 * The vertical stepper of the setup wizard.
 */

import { Check, Lock, Play, SkipForward } from "lucide-react";
import { cn } from "../../../lib/utils";
import { stateLabel, stateTone, stepPosition } from "../tour";
import type { OnboardingStep } from "../types";
import styles from "./WizardStepper.module.css";

/** Props accepted by {@link WizardStepper}. */
export interface WizardStepperProps {
  /** The catalogue steps in any order. */
  steps: OnboardingStep[];
  /** Index of the step currently being spotlighted. */
  activeIndex: number;
  /** Called with the index of a selected step. */
  onSelect: (index: number) => void;
  /** Optional extra class names. */
  className?: string;
}

/**
 * Render a keyboard operable list of wizard steps.
 *
 * @param props - The component props.
 * @returns The stepper element.
 */
export function WizardStepper({
  steps,
  activeIndex,
  onSelect,
  className,
}: WizardStepperProps) {
  const ordered = [...steps].sort(
    (a, b) => a.order - b.order || a.slug.localeCompare(b.slug),
  );
  return (
    <nav
      aria-label="Onboarding steps"
      className={cn(styles.stepper, className)}
    >
      <ol className={styles.list}>
        {ordered.map((step, index) => {
          const isActive = index === activeIndex;
          const state = step.state;
          const Icon =
            state === "complete"
              ? Check
              : state === "skipped"
                ? SkipForward
                : state === "locked"
                  ? Lock
                  : Play;
          return (
            <li
              key={step.id}
              className={cn(
                styles.item,
                styles[stateTone(state)],
                isActive && styles.itemActive,
              )}
            >
              <button
                type="button"
                className={styles.button}
                onClick={() => onSelect(index)}
                disabled={state === "locked"}
                aria-current={isActive ? "step" : undefined}
                aria-label={`${stepPosition(index, ordered.length)}: ${step.title}, ${stateLabel(state)}`}
              >
                <span className={styles.marker} aria-hidden="true">
                  <Icon size={13} strokeWidth={2.5} />
                </span>
                <span className={styles.text}>
                  <span className={styles.title}>{step.title}</span>
                  <span className={styles.meta}>
                    {stateLabel(state)} · {step.duration_label}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
