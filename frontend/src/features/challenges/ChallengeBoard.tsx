/**
 * The challenge board: columns of challenges grouped by lifecycle status.
 */

import { useMemo, useState } from "react";
import { Flag, Lock, Sparkles, Timer } from "lucide-react";
import { cn, formatNumber } from "../../lib/utils";
import { useChallenges, useSolves } from "../../api/resources";
import { useDashboardStore } from "../../stores/dashboardStore";
import type { Challenge } from "../../types";
import { Badge, Card, EmptyState, Skeleton } from "../../components/ui";
import type { BoardColumn, BoardColumnData } from "./types";
import styles from "./ChallengeBoard.module.css";

const COLUMNS: Array<{ id: BoardColumn; label: string; hint: string }> = [
  { id: "pending", label: "Pending", hint: "Not started yet" },
  { id: "active", label: "Active", hint: "Currently being worked on" },
  { id: "solved", label: "Solved", hint: "Cleared by the team" },
  { id: "locked", label: "Locked", hint: "Not available" },
];

const DIFFICULTY_TONE: Record<string, string> = {
  trivial: "#94a3b8",
  easy: "#34d399",
  medium: "#38bdf8",
  hard: "#f59e0b",
  insane: "#f43f5e",
};

/** Props accepted by {@link ChallengeBoard}. */
export interface ChallengeBoardProps {
  /** Called when a challenge card is activated. */
  onSelect: (challenge: Challenge) => void;
  /** The identifier of the challenge currently selected. */
  selectedId?: string | null;
  /** Additional class applied to the container. */
  className?: string;
}

/**
 * Render the challenge board.
 *
 * @param props - The component props.
 * @returns The board element.
 */
export function ChallengeBoard({ onSelect, selectedId, className }: ChallengeBoardProps) {
  const teamId = useDashboardStore((state) => state.selectedTeamId);
  const categoryFilter = useDashboardStore((state) => state.categoryFilter);
  const statusFilter = useDashboardStore((state) => state.statusFilter);

  const [dragTarget, setDragTarget] = useState<BoardColumn | null>(null);

  const challenges = useChallenges(
    {
      teamId: teamId ?? undefined,
      category: categoryFilter === "all" ? undefined : categoryFilter,
      status: statusFilter === "all" ? undefined : statusFilter,
    },
    { staleTime: 8_000 },
  );
  const solves = useSolves({ teamId: teamId ?? undefined }, { staleTime: 15_000 });

  const solveCountByChallenge = useMemo(() => {
    const counts = new Map<string, number>();
    for (const solve of solves.data ?? []) {
      counts.set(solve.challenge_id, (counts.get(solve.challenge_id) ?? 0) + 1);
    }
    return counts;
  }, [solves.data]);

  const columns = useMemo<BoardColumnData[]>(
    () =>
      COLUMNS.map((column) => ({
        id: column.id,
        label: column.label,
        challenges: (challenges.data ?? []).filter(
          (challenge) => challenge.status === column.id,
        ),
      })),
    [challenges.data],
  );

  if (!challenges.data) {
    return (
      <div className={cn(styles.board, className)}>
        {COLUMNS.map((column) => (
          <Card key={column.id} className={styles.column}>
            <Skeleton height={120} />
          </Card>
        ))}
      </div>
    );
  }

  const total = columns.reduce((sum, column) => sum + column.challenges.length, 0);

  return (
    <div className={cn(styles.board, className)}>
      {columns.map((column) => {
        const meta = COLUMNS.find((entry) => entry.id === column.id);
        const isTarget = dragTarget === column.id;
        return (
          <Card
            key={column.id}
            className={cn(styles.column, isTarget && styles.columnTarget)}
            data-board-column={column.id}
            onDragOver={(event) => {
              event.preventDefault();
              setDragTarget(column.id);
            }}
            onDragLeave={() => setDragTarget(null)}
            onDrop={() => setDragTarget(null)}
          >
            <header className={styles.columnHeader}>
              <div>
                <h3 className={styles.columnTitle}>
                  {column.label}
                  <span className={styles.columnCount}>{column.challenges.length}</span>
                </h3>
                <p className={styles.columnHint}>{meta?.hint}</p>
              </div>
            </header>

            <div className={styles.columnBody}>
              {column.challenges.length === 0 ? (
                <EmptyState
                  icon={<Flag size={18} />}
                  title="No challenge"
                  description="Nothing sits in this column yet."
                />
              ) : (
                column.challenges.map((challenge) => (
                  <button
                    key={challenge.id}
                    type="button"
                    className={cn(
                      styles.card,
                      challenge.id === selectedId && styles.cardSelected,
                    )}
                    onClick={() => onSelect(challenge)}
                    aria-pressed={challenge.id === selectedId}
                    draggable
                  >
                    <div className={styles.cardTop}>
                      <span className={styles.cardTitle}>{challenge.title}</span>
                      {challenge.status === "locked" ? (
                        <Lock size={13} aria-hidden="true" />
                      ) : challenge.status === "solved" ? (
                        <Sparkles size={13} aria-hidden="true" />
                      ) : null}
                    </div>
                    <div className={styles.cardMeta}>
                      <span
                        className={styles.cardDifficulty}
                        style={{ color: DIFFICULTY_TONE[challenge.difficulty] }}
                      >
                        {challenge.difficulty}
                      </span>
                      <span className={styles.cardCategory}>{challenge.category}</span>
                      <span className={styles.cardPoints}>
                        {formatNumber(challenge.points)} pts
                      </span>
                    </div>
                    <div className={styles.cardFooter}>
                      <span className={styles.cardTags}>
                        {challenge.tags.slice(0, 2).map((tag) => (
                          <span key={tag} className={styles.cardTag}>
                            {tag}
                          </span>
                        ))}
                      </span>
                      {challenge.ends_at ? (
                        <span className={styles.cardTimer}>
                          <Timer size={11} aria-hidden="true" />
                          {Math.max(0, Math.round(challenge.seconds_remaining / 60))}m
                        </span>
                      ) : null}
                      {solveCountByChallenge.has(challenge.id) ? (
                        <Badge tone="success">
                          {solveCountByChallenge.get(challenge.id)} solve
                        </Badge>
                      ) : null}
                    </div>
                  </button>
                ))
              )}
            </div>
          </Card>
        );
      })}
      {total === 0 ? (
        <p className={styles.emptyHint}>No challenge matches the current filters.</p>
      ) : null}
    </div>
  );
}
