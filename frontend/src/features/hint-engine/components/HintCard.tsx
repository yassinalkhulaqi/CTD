/** One tier of the progressive hint ladder. */

import { Check, Clock3, Coins, UnlockKeyhole } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../../../components/ui";
import { canUnlock, formatCountdown, formatCredits, stateTone } from "../hints";
import type { HintBudget, HintView } from "../types";
import { HintReveal } from "./HintReveal";
import styles from "./HintCard.module.css";

/** Props accepted by {@link HintCard}. */
export interface HintCardProps {
  hint: HintView;
  budget: HintBudget | null;
  onUnlock?: (hint: HintView, origin: HTMLElement | null) => void;
  busy?: boolean;
}

/**
 * Render a hint, its reveal state and the unlock action.
 *
 * @param props - The component props.
 * @returns The tier card.
 */
export function HintCard({
  hint,
  budget,
  onUnlock,
  busy = false,
}: HintCardProps) {
  const unlockable = canUnlock(hint, budget);
  return (
    <Card
      as="article"
      className={`${styles.card} ${hint.unlocked ? styles.unlocked : ""}`}
      aria-label={`Tier ${hint.tier}: ${hint.title}`}
    >
      <CardHeader
        actions={
          <Badge tone={stateTone(hint.state)} dot>
            {hint.badge_label}
          </Badge>
        }
      >
        <span className={styles.tier}>Tier {hint.tier}</span>
        <CardTitle level={3}>{hint.title}</CardTitle>
      </CardHeader>
      <CardContent className={styles.content}>
        <HintReveal hint={hint} />
        <p className={styles.reason} aria-live="polite">
          {hint.reason}
        </p>
        {hint.remaining_seconds > 0 && !hint.unlocked ? (
          <p className={styles.countdown}>
            <Clock3 size={13} aria-hidden="true" />
            Unlocks in {formatCountdown(hint.remaining_seconds)}
          </p>
        ) : null}
      </CardContent>
      <CardFooter className={styles.footer}>
        <span className={styles.cost}>
          <Coins size={14} aria-hidden="true" />
          {formatCredits(hint.cost)} credits
        </span>
        {hint.unlocked ? (
          <span className={styles.done}>
            <Check size={14} aria-hidden="true" />
            Revealed
          </span>
        ) : (
          <Button
            size="sm"
            variant={unlockable ? "primary" : "secondary"}
            icon={<UnlockKeyhole size={14} />}
            disabled={!unlockable || !onUnlock}
            loading={busy}
            loadingLabel="Unlocking"
            onClick={(event) =>
              onUnlock?.(hint, event.currentTarget as HTMLElement)
            }
            aria-label={`Unlock tier ${hint.tier} hint ${hint.title} for ${hint.cost} credits`}
          >
            Unlock
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
