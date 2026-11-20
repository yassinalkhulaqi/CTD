/** Table summarising translation completeness per locale and namespace. */

import { useMemo } from "react";
import {
  Badge,
  Button,
  EmptyState,
  Progress,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "../../../components/ui";
import { completenessPercent, completenessTone } from "../format";
import type { CompletenessRow, CompletenessStat } from "../types";
import styles from "./CompletenessTable.module.css";

/** Props accepted by {@link CompletenessTable}. */
export interface CompletenessTableProps {
  /** The completeness statistics. */
  stats: CompletenessStat[];
  /** The currently selected locale code. */
  selectedLocale?: string;
  /** Called when a locale row is selected. */
  onSelect?: (locale: string) => void;
}

/**
 * Render the completeness report as an accessible table.
 *
 * @param props - The table props.
 * @returns The table or an empty state.
 */
export function CompletenessTable({
  stats,
  selectedLocale,
  onSelect,
}: CompletenessTableProps) {
  const rows = useMemo<CompletenessRow[]>(
    () =>
      stats
        .map((stat) => {
          const percent = completenessPercent(stat.translated, stat.total);
          return {
            ...stat,
            percent,
            percentLabel: `${percent.toFixed(1)}%`,
            tone: completenessTone(percent),
          };
        })
        .sort(
          (a, b) => a.percent - b.percent || a.locale.localeCompare(b.locale),
        ),
    [stats],
  );

  if (rows.length === 0) {
    return (
      <EmptyState
        title="No translations yet"
        description="Register a reference locale and add messages to see completeness."
      />
    );
  }

  return (
    <Table aria-label="Translation completeness" className={styles.table}>
      <TableHead>
        <TableRow>
          <TableHeaderCell>Locale</TableHeaderCell>
          <TableHeaderCell>Namespace</TableHeaderCell>
          <TableHeaderCell align="right">Keys</TableHeaderCell>
          <TableHeaderCell align="right">Translated</TableHeaderCell>
          <TableHeaderCell>Completeness</TableHeaderCell>
          <TableHeaderCell>Status</TableHeaderCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map((row) => (
          <TableRow
            key={`${row.locale}:${row.namespace}`}
            className={styles.row}
          >
            <TableCell>
              {onSelect ? (
                <Button
                  size="sm"
                  variant={row.locale === selectedLocale ? "primary" : "subtle"}
                  onClick={() => onSelect(row.locale)}
                  aria-pressed={row.locale === selectedLocale}
                >
                  {row.locale}
                </Button>
              ) : (
                <span className={styles.code}>{row.locale}</span>
              )}
            </TableCell>
            <TableCell>{row.namespace}</TableCell>
            <TableCell align="right">{row.total}</TableCell>
            <TableCell align="right">{row.translated}</TableCell>
            <TableCell>
              <div className={styles.progressCell}>
                <Progress
                  value={row.percent}
                  label={`${row.locale} ${row.namespace} completeness`}
                  tone={row.tone}
                  thin
                />
                <span className={styles.percent}>{row.percentLabel}</span>
              </div>
            </TableCell>
            <TableCell>
              <Badge tone={row.tone} dot>
                {row.is_complete ? "Complete" : `${row.missing} missing`}
              </Badge>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
