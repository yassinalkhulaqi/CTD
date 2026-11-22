/**
 * The full ranking table with movement indicators and solve counts.
 */

import { useMemo, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "../../../components/ui";
import { cn, formatNumber } from "../../../lib/utils";
import { formatScore } from "../scoring";
import type { RankingEntry } from "../types";
import { MovementBadge } from "./MovementBadge";
import styles from "./RankTable.module.css";

/** Props accepted by {@link RankTable}. */
export interface RankTableProps {
  /** The entries to display. */
  entries: RankingEntry[];
  /** The currently selected team. */
  selectedTeamId?: string | null;
  /** Called when a team is activated. */
  onSelect?: (teamId: string) => void;
  /** Additional class applied to the container. */
  className?: string;
}

/** Columns that can be sorted from the table header. */
type SortKey = "rank" | "points" | "solves";

/** Compare two entries by the requested column. */
function compare(a: RankingEntry, b: RankingEntry, key: SortKey): number {
  if (key === "rank") return a.rank - b.rank;
  if (key === "points") return b.points - a.points || a.rank - b.rank;
  return b.solves - a.solves || a.rank - b.rank;
}

/**
 * Render the ranking table.
 *
 * @param props - The component props.
 * @returns The table element.
 */
export function RankTable({
  entries,
  selectedTeamId,
  onSelect,
  className,
}: RankTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("rank");
  const [direction, setDirection] = useState<"asc" | "desc">("asc");

  const rows = useMemo(() => {
    const sorted = [...entries].sort((a, b) => compare(a, b, sortKey));
    return direction === "asc" ? sorted : sorted.reverse();
  }, [entries, sortKey, direction]);

  const toggleSort = (key: string) => {
    if (key !== "rank" && key !== "points" && key !== "solves") return;
    if (key === sortKey) {
      setDirection((value) => (value === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(key);
    setDirection(key === "rank" ? "asc" : "desc");
  };

  return (
    <div className={cn(styles.wrapper, className)}>
      <Table aria-label="Team ranking" className={styles.table}>
        <TableHead>
          <TableRow>
            <TableHeaderCell
              sortKey="rank"
              sortDirection={sortKey === "rank" ? direction : null}
              onSort={toggleSort}
            >
              Rank
            </TableHeaderCell>
            <TableHeaderCell>Team</TableHeaderCell>
            <TableHeaderCell
              sortKey="points"
              align="right"
              sortDirection={sortKey === "points" ? direction : null}
              onSort={toggleSort}
            >
              Points
            </TableHeaderCell>
            <TableHeaderCell
              sortKey="solves"
              align="right"
              sortDirection={sortKey === "solves" ? direction : null}
              onSort={toggleSort}
            >
              Solves
            </TableHeaderCell>
            <TableHeaderCell align="right">Movement</TableHeaderCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((entry) => {
            const steps =
              entry.previous_rank === null
                ? 0
                : Math.abs(entry.previous_rank - entry.rank);
            return (
              <TableRow
                key={entry.team_id}
                selected={selectedTeamId === entry.team_id}
                className={entry.rank <= 3 ? styles.topRow : undefined}
              >
                <TableCell>
                  <span
                    className={cn(
                      styles.rank,
                      entry.rank <= 3 && styles.podiumRank,
                    )}
                  >
                    {entry.rank}
                  </span>
                </TableCell>
                <TableCell>
                  {onSelect ? (
                    <button
                      type="button"
                      className={styles.teamButton}
                      onClick={() => onSelect(entry.team_id)}
                      aria-label={`Inspect ${entry.team_name}`}
                    >
                      {entry.team_name}
                    </button>
                  ) : (
                    <span className={styles.teamName}>{entry.team_name}</span>
                  )}
                  <span className={styles.lastSolve}>
                    {entry.last_solve_at
                      ? `Last solve ${new Date(entry.last_solve_at).toLocaleTimeString()}`
                      : "No solves recorded"}
                  </span>
                </TableCell>
                <TableCell align="right">
                  <span className={styles.points}>
                    {formatScore(entry.points)}
                  </span>
                </TableCell>
                <TableCell align="right">
                  <span
                    className={styles.solves}
                    aria-label={`${entry.solves} solves`}
                  >
                    {formatNumber(entry.solves)}
                  </span>
                </TableCell>
                <TableCell align="right">
                  <MovementBadge movement={entry.movement} steps={steps} />
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
      {entries.length === 0 ? (
        <p className={styles.empty}>No teams to rank yet.</p>
      ) : null}
    </div>
  );
}
