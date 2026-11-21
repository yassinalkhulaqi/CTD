/**
 * Detail sheet for a single badge, rendered as an accessible drawer.
 */

import { Award, Lock, Sparkles, Users } from "lucide-react";
import {
  Badge,
  Button,
  Divider,
  Drawer,
  Progress,
} from "../../../components/ui";
import {
  criteriaCaption,
  percentLabel,
  progressRatio,
  rarityColor,
  relativeTime,
  tierColor,
  type BadgeView,
} from "../types";
import { BadgeIcon } from "./BadgeIcon";
import { ProgressRing } from "./ProgressRing";
import styles from "./BadgeDetail.module.css";

/** Props accepted by {@link BadgeDetail}. */
export interface BadgeDetailProps {
  /** The badge being inspected. */
  view: BadgeView | null;
  /** Whether the detail sheet is visible. */
  open: boolean;
  /** Called when the sheet requests to close. */
  onClose: () => void;
  /** Number of members who own the badge. */
  awardedTo?: number;
  /** Timestamp of the viewer's award. */
  awardedAt?: string | null;
  /** Called to grant the badge manually. */
  onAward?: () => void;
  /** Whether the award request is in flight. */
  awarding?: boolean;
}

/**
 * Render the badge detail sheet.
 *
 * @param props - The component props.
 * @returns The drawer element.
 */
export function BadgeDetail({
  view,
  open,
  onClose,
  awardedTo = 0,
  awardedAt,
  onAward,
  awarding = false,
}: BadgeDetailProps) {
  if (!view) return null;

  const accent = tierColor(view.badge.tier);
  const rarityAccent = rarityColor(view.rarity_band);

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title="Badge details"
      footer={
        onAward ? (
          <Button
            icon={<Award size={15} />}
            onClick={onAward}
            loading={awarding}
            loadingLabel="Unlocking..."
            disabled={view.awarded}
            block
          >
            {view.awarded ? "Already unlocked" : "Unlock badge"}
          </Button>
        ) : undefined
      }
    >
      <div
        className={styles.hero}
        style={{ ["--tier-accent" as string]: accent }}
      >
        <ProgressRing
          value={view.awarded ? 100 : view.percent}
          size={112}
          strokeWidth={8}
          color={accent}
          label={`${view.display_name} completion`}
        >
          <span className={styles.heroIcon}>
            {view.revealed ? (
              <BadgeIcon token={view.display_icon} size={38} />
            ) : (
              <Lock size={32} aria-hidden="true" />
            )}
          </span>
        </ProgressRing>
        <h3 className={styles.title}>{view.display_name}</h3>
        <div className={styles.chips}>
          <Badge tone="accent" outline>
            {view.badge.tier}
          </Badge>
          <Badge tone="neutral" outline>
            {view.badge.score} pts
          </Badge>
          <Badge tone="info" outline dot>
            {view.rarity_band}
          </Badge>
        </div>
      </div>

      <p className={styles.description}>{view.display_description}</p>

      {!view.revealed ? (
        <p className={styles.secretHint}>
          <Lock size={14} aria-hidden="true" />
          Unlock this badge to reveal its identity and criteria.
        </p>
      ) : null}

      <Divider />

      <dl className={styles.facts}>
        <div>
          <dt>Criterion</dt>
          <dd>{criteriaCaption(view.badge)}</dd>
        </div>
        <div>
          <dt>Progress</dt>
          <dd>
            {view.current} / {view.target} ({percentLabel(view.percent)})
          </dd>
        </div>
        <div>
          <dt>Holders</dt>
          <dd>
            <Users size={13} aria-hidden="true" /> {awardedTo} members
          </dd>
        </div>
        <div>
          <dt>Rarity score</dt>
          <dd style={{ color: rarityAccent }}>{view.rarity} / 100</dd>
        </div>
        {awardedAt ? (
          <div>
            <dt>Unlocked</dt>
            <dd>{relativeTime(awardedAt)}</dd>
          </div>
        ) : null}
      </dl>

      <Progress
        value={progressRatio(view.awarded ? 100 : view.percent)}
        label={`${view.display_name} progress`}
        tone={view.awarded ? "success" : "accent"}
      />

      {view.awarded ? (
        <p className={styles.unlockedNote}>
          <Sparkles size={14} aria-hidden="true" />
          This badge is part of your collection.
        </p>
      ) : null}
    </Drawer>
  );
}
