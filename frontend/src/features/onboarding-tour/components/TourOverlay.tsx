/**
 * Spotlight tour overlay with keyboard navigation.
 */

import { useEffect, useRef } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Crosshair,
  Lightbulb,
  X,
} from "lucide-react";
import { Badge, Button, IconButton, Kbd } from "../../../components/ui";
import { stepPosition, tourKeyboardAction } from "../tour";
import type { OnboardingStep } from "../types";
import styles from "./TourOverlay.module.css";

/** Props accepted by {@link TourOverlay}. */
export interface TourOverlayProps {
  /** The step being spotlighted. */
  step: OnboardingStep;
  /** Zero-based index of the step. */
  index: number;
  /** Total number of steps in the tour. */
  total: number;
  /** Whether this is the first step. */
  isFirst: boolean;
  /** Whether this is the last step. */
  isLast: boolean;
  /** Advance to the next step or finish the tour. */
  onNext: () => void;
  /** Return to the previous step. */
  onBack: () => void;
  /** Dismiss the tour. */
  onClose: () => void;
}

/**
 * Render a modal overlay that guides the user through one tour step.
 *
 * @param props - The component props.
 * @returns The overlay element.
 */
export function TourOverlay({
  step,
  index,
  total,
  isFirst,
  isLast,
  onNext,
  onBack,
  onClose,
}: TourOverlayProps) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
  }, [step.id]);

  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      const action = tourKeyboardAction(event.key);
      if (action === null) return;
      event.preventDefault();
      if (action === "next") onNext();
      else if (action === "previous") onBack();
      else onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onNext, onBack, onClose]);

  return (
    <div
      className={styles.backdrop}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className={styles.spotlight} aria-hidden="true">
        <span className={styles.spotlightRing} />
        <span className={styles.spotlightTarget}>{step.target}</span>
      </div>
      <section
        className={styles.card}
        role="dialog"
        aria-modal="true"
        aria-labelledby="onboarding-tour-title"
      >
        <header className={styles.header}>
          <div className={styles.position}>
            <Badge tone="accent" outline>
              {stepPosition(index, total)}
            </Badge>
            <Badge tone="neutral">{step.kind}</Badge>
          </div>
          <IconButton
            ref={closeRef}
            icon={<X size={16} />}
            label="Close guided tour"
            size="sm"
            onClick={onClose}
          />
        </header>

        <div className={styles.body}>
          <p className={styles.eyebrow}>Guided tour</p>
          <h2 id="onboarding-tour-title" className={styles.title}>
            {step.title}
          </h2>
          <p className={styles.description}>{step.description}</p>
          {step.hint ? (
            <p className={styles.hint}>
              <Lightbulb size={15} aria-hidden="true" />
              <span>{step.hint}</span>
            </p>
          ) : null}
          <p className={styles.target}>
            <Crosshair size={14} aria-hidden="true" />
            <span>Spotlighting</span>
            <code>{step.target}</code>
          </p>
        </div>

        <footer className={styles.footer}>
          <div className={styles.shortcuts} aria-hidden="true">
            <span>
              <Kbd>←</Kbd> <Kbd>→</Kbd> navigate
            </span>
            <span>
              <Kbd>Esc</Kbd> close
            </span>
          </div>
          <div className={styles.actions}>
            <Button variant="ghost" size="sm" onClick={onClose}>
              Skip tour
            </Button>
            <Button
              variant="secondary"
              size="sm"
              icon={<ChevronLeft size={14} />}
              disabled={isFirst}
              onClick={onBack}
            >
              Back
            </Button>
            <Button
              size="sm"
              trailingIcon={<ChevronRight size={14} />}
              onClick={onNext}
            >
              {isLast ? "Finish" : "Next step"}
            </Button>
          </div>
        </footer>
      </section>
    </div>
  );
}
