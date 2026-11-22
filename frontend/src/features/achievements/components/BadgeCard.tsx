/**
 * A gallery card that summarises one badge and opens its detail sheet.
 */

import { Check, Lock, Sparkles } from "lucide-react";
import { cn } from "../../../lib/utils";
import { Badge as ToneBadge } from "../../../components/ui";
import {
  criteriaCaption,
  percentLabel,
  tierColor,
  type BadgeView,
} from "../types";
import { BadgeIcon } from "./BadgeIcon";
import { ProgressRing } from "./ProgressRing";
import styles from "./BadgeCard.module.css";

/** Props accepted by {@link BadgeCard}. */
export interface BadgeCardProps {
  /** The badge to render. */
  view: BadgeView;
  /** Called when the card is activated. */
  onSelect: (view: BadgeView) => void;
  /** Whether this badge was unlocked by the latest evaluation. */
  newlyUnlocked?: boolean;
  /** Whether this card is currently selected. */
  selected?: boolean;
  /** Additional class name. */
  className?: string;
}

/**
 * Render a badge gallery card.
 *
 * @param props - The component props.
 * @returns The card element.
 */
export function BadgeCard({
  view,
  onSelect,
  newlyUnlocked = false,
  selected = false,
  className,
}: BadgeCardProps) {
  const accent = tierColor(view.badge.tier);
  const complete = view.percent >= 100 || view.awarded;
  const tone = view.awarded ? "success" : complete ? "warning" : "neutral";

  return (
    <button
      type="button"
      className={cn(
        styles.card,
        view.awarded && styles.unlocked,
        selected && styles.selected,
        newlyUnlocked && styles.justUnlocked,
        className,
      )}
      style={{ ["--badge-accent" as string]: accent }}
      onClick={() => onSelect(view)}
      aria-label={`View ${view.display_name} badge details`}
      aria-pressed={selected}
    >
      {newlyUnlocked ? (
        <span className={styles.sparkle} aria-hidden="true">
          <Sparkles size={14} />
        </span>
      ) : null}
      <div className={styles.top}>
        <ProgressRing
          value={view.awarded ? 100 : view.percent}
          size={68}
          strokeWidth={5}
          color={accent}
          label={`${view.display_name} progress ${percentLabel(view.percent)}`}
          celebrate={newlyUnlocked}
        >
          <span className={styles.ringIcon}>
            {view.awarded ? (
              <Check size={20} aria-hidden="true" />
            ) : view.revealed ? (
              <BadgeIcon token={view.display_icon} size={22} />
            ) : (
              <Lock size={18} aria-hidden="true" />
            )}
          </span>
        </ProgressRing>
        <div className={styles.heading}>
          <span className={styles.name}>{view.display_name}</span>
          <span className={styles.tier} style={{ color: accent }}>
            {view.badge.tier}
          </span>
        </div>
      </div>

      <p className={styles.description}>{view.display_description}</p>

      <div className={styles.meta}>
        <ToneBadge tone={tone} outline>
          {criteriaCaption(view.badge)}
        </ToneBadge>
        <span className={styles.points}>{view.badge.score} pts</span>
      </div>

      <div className={styles.footer}>
        <div
          className={styles.meter}
          role="meter"
          aria-valuenow={view.current}
          aria-valuemin={0}
          aria-valuemax={view.target}
          aria-label={`${view.display_name} criterion progress`}
        >
          <span
            className={styles.meterFill}
            style={{ width: `${percentLabel(view.percent).replace("%", "")}%` }}
          />
        </div>
        <span className={styles.counter}>
          {view.current}/{view.target}
        </span>
      </div>
    </button>
  );
}
