/**
 * Podium display for the three highest ranked teams.
 */

import { Crown, Medal } from "lucide-react";
import { Avatar, Card, EmptyState, Skeleton } from "../../../components/ui";
import { cn, formatNumber } from "../../../lib/utils";
import { podiumTone } from "../scoring";
import type { RankingEntry } from "../types";
import { MovementBadge } from "./MovementBadge";
import styles from "./Podium.module.css";

/** Props accepted by {@link Podium}. */
export interface PodiumProps {
  /** The ranked entries; only the first three are displayed. */
  entries: RankingEntry[];
  /** The currently selected team. */
  selectedTeamId?: string | null;
  /** Called when a team is activated. */
  onSelect?: (teamId: string) => void;
  /** Show loading placeholders instead of content. */
  loading?: boolean;
  /** Additional class applied to the container. */
  className?: string;
}

/** Visual ordering of the podium places: second, first, third. */
const DISPLAY_ORDER = [1, 0, 2];

/**
 * Render the podium for the top three teams.
 *
 * @param props - The component props.
 * @returns The podium section.
 */
export function Podium({
  entries,
  selectedTeamId,
  onSelect,
  loading = false,
  className,
}: PodiumProps) {
  const top = entries.filter((entry) => entry.rank <= 3);
  const byRank = new Map(top.map((entry) => [entry.rank, entry]));
  const places = DISPLAY_ORDER.map((index) => byRank.get(index + 1) ?? null);

  if (loading) {
    return (
      <div className={cn(styles.podium, className)} aria-label="Loading podium">
        {DISPLAY_ORDER.map((index) => (
          <Card
            key={index}
            className={cn(
              styles.card,
              styles[index === 1 ? "first" : index === 0 ? "second" : "third"],
            )}
          >
            <Skeleton height={150} />
          </Card>
        ))}
      </div>
    );
  }

  if (top.length === 0) {
    return (
      <Card className={className}>
        <EmptyState
          title="No ranking yet"
          description="Rankings appear as soon as the first solve is recorded."
          icon={<Medal size={22} />}
        />
      </Card>
    );
  }

  return (
    <ol className={cn(styles.podium, className)} aria-label="Top three teams">
      {places.map((entry, position) => {
        if (!entry) {
          return (
            <li
              key={position}
              className={styles.placeholder}
              aria-hidden="true"
            />
          );
        }
        const rank = position === 1 ? 1 : position === 0 ? 2 : 3;
        const selected = selectedTeamId === entry.team_id;
        const tone = podiumTone(rank);
        return (
          <li key={entry.team_id} className={styles.slot}>
            <Card
              as="article"
              className={cn(
                styles.card,
                styles[tone],
                selected && styles.selected,
              )}
            >
              <div className={styles.place}>
                <span className={styles.medal} aria-hidden="true">
                  {rank === 1 ? <Crown size={16} /> : <Medal size={15} />}
                </span>
                <span>
                  {rank === 1
                    ? "Champion"
                    : `${rank}${rank === 2 ? "nd" : "rd"} place`}
                </span>
              </div>
              <div className={styles.identity}>
                <Avatar
                  name={entry.team_name}
                  size={rank === 1 ? "lg" : "md"}
                />
                <div className={styles.nameBlock}>
                  <span className={styles.teamName}>{entry.team_name}</span>
                  <span className={styles.teamMeta}>
                    {formatNumber(entry.points)} pts · {entry.solves} solves
                  </span>
                </div>
              </div>
              <div className={styles.footer}>
                <MovementBadge
                  movement={entry.movement}
                  steps={
                    entry.movement === "up" || entry.movement === "down"
                      ? Math.abs(
                          (entry.previous_rank ?? entry.rank) - entry.rank,
                        )
                      : 0
                  }
                />
                {onSelect ? (
                  <button
                    type="button"
                    className={styles.selectButton}
                    onClick={() => onSelect(entry.team_id)}
                    aria-label={`Inspect ${entry.team_name}`}
                  >
                    Inspect
                  </button>
                ) : null}
              </div>
              <div className={styles.column} aria-hidden="true">
                <span className={styles.columnValue}>{rank}</span>
              </div>
            </Card>
          </li>
        );
      })}
    </ol>
  );
}
