/**
 * A single wizard step card with its completion affordances.
 */

import {
  Check,
  CheckCircle2,
  Clock,
  Compass,
  Crosshair,
  Flag,
  Map,
  Play,
  SkipForward,
  Sparkles,
  UserRound,
  type LucideIcon,
} from "lucide-react";
import { Badge, Button, Card, CardContent } from "../../../components/ui";
import { cn } from "../../../lib/utils";
import { isResolved, stateLabel, stateTone } from "../tour";
import type { OnboardingStep, StepState } from "../types";
import styles from "./StepCard.module.css";

const ICONS: Record<string, LucideIcon> = {
  sparkles: Sparkles,
  user: UserRound,
  layout: Map,
  flag: Flag,
  chart: Compass,
  users: UserRound,
  check: CheckCircle2,
};

/** Props accepted by {@link StepCard}. */
export interface StepCardProps {
  /** The step to display. */
  step: OnboardingStep;
  /** Its derived state for the current user. */
  state: StepState;
  /** Whether the step is the current focus of the tour. */
  isCurrent: boolean;
  /** Mark the step complete. */
  onComplete: (step: OnboardingStep) => void;
  /** Skip the step. */
  onSkip: (step: OnboardingStep) => void;
  /** Open the spotlight tour at this step. */
  onSpotlight: (step: OnboardingStep) => void;
  /** Whether a mutation is in flight. */
  busy?: boolean;
}

/**
 * Render one actionable wizard step.
 *
 * @param props - The component props.
 * @returns The step card.
 */
export function StepCard({
  step,
  state,
  isCurrent,
  onComplete,
  onSkip,
  onSpotlight,
  busy = false,
}: StepCardProps) {
  const Icon = ICONS[step.icon] ?? Compass;
  const resolved = isResolved({ ...step, state });
  const locked = state === "locked";
  return (
    <Card
      as="article"
      className={cn(
        styles.card,
        isCurrent && styles.current,
        styles[stateTone(state)],
      )}
      aria-labelledby={`step-title-${step.id}`}
    >
      <CardContent className={styles.content}>
        <div className={styles.icon} aria-hidden="true">
          <Icon size={19} />
        </div>
        <div className={styles.main}>
          <div className={styles.heading}>
            <h3 id={`step-title-${step.id}`} className={styles.title}>
              {step.title}
            </h3>
            <Badge tone={stateTone(state)} outline dot>
              {stateLabel(state)}
            </Badge>
            {!step.required ? (
              <Badge tone="neutral" outline>
                optional
              </Badge>
            ) : null}
          </div>
          <p className={styles.description}>{step.description}</p>
          <div className={styles.meta}>
            <span>
              <Clock size={13} aria-hidden="true" />
              {step.duration_label}
            </span>
            <span>
              <Crosshair size={13} aria-hidden="true" />
              <code>{step.target}</code>
            </span>
            {step.hint ? (
              <span className={styles.hint}>{step.hint}</span>
            ) : null}
          </div>
        </div>
        <div className={styles.actions}>
          <Button
            size="sm"
            variant="secondary"
            icon={<Play size={13} />}
            onClick={() => onSpotlight(step)}
            disabled={locked}
          >
            Show me
          </Button>
          <Button
            size="sm"
            variant="ghost"
            icon={<SkipForward size={13} />}
            onClick={() => onSkip(step)}
            disabled={locked || resolved || busy}
          >
            Skip
          </Button>
          <Button
            size="sm"
            icon={resolved ? <Check size={13} /> : undefined}
            onClick={() => onComplete(step)}
            disabled={locked || resolved || busy}
            loading={busy}
          >
            {state === "complete" ? "Done" : "Mark complete"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
