/** Reveal history table with a compact spend breakdown. */

import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "../../../components/ui";
import { formatCredits, formatTimestamp } from "../hints";
import type { HintLedger } from "../types";
import styles from "./HintLedger.module.css";

/** Props accepted by {@link HintLedgerView}. */
export interface HintLedgerViewProps {
  ledger: HintLedger | null;
  loading?: boolean;
}

/**
 * Render the reveal ledger and its per-tier totals.
 *
 * @param props - The component props.
 * @returns The ledger panel.
 */
export function HintLedgerView({
  ledger,
  loading = false,
}: HintLedgerViewProps) {
  const entries = ledger?.entries ?? [];
  return (
    <Card className={styles.card}>
      <CardHeader
        actions={
          ledger ? (
            <Badge tone="neutral" outline>
              {ledger.summary.unlock_count} unlocks
            </Badge>
          ) : undefined
        }
      >
        <CardTitle level={3}>Reveal ledger</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton lines={4} aria-label="Loading reveal history" />
        ) : entries.length === 0 ? (
          <EmptyState
            title="No hints revealed yet"
            description="Unlock a hint to start the team's reveal history."
          />
        ) : (
          <Table sticky aria-label="Hint reveal history">
            <TableHead>
              <TableRow>
                <TableHeaderCell>Tier</TableHeaderCell>
                <TableHeaderCell>Hint</TableHeaderCell>
                <TableHeaderCell>Member</TableHeaderCell>
                <TableHeaderCell>Cost</TableHeaderCell>
                <TableHeaderCell>Revealed</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {entries.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell>
                    <Badge tone="accent" outline>
                      T{entry.tier}
                    </Badge>
                  </TableCell>
                  <TableCell className={styles.title}>
                    {entry.hint_title}
                  </TableCell>
                  <TableCell>{entry.member_handle}</TableCell>
                  <TableCell className={styles.cost}>
                    {formatCredits(entry.cost_paid)}
                  </TableCell>
                  <TableCell className={styles.time}>
                    {formatTimestamp(entry.unlocked_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        {ledger && ledger.summary.by_tier.length > 0 ? (
          <ul className={styles.totals} aria-label="Spend by tier">
            {ledger.summary.by_tier.map((row) => (
              <li key={row.tier} className={styles.total}>
                <span>Tier {row.tier}</span>
                <span className={styles.totalCount}>{row.unlocks} unlocks</span>
                <span className={styles.totalSpend}>
                  {formatCredits(row.spent)} credits
                </span>
              </li>
            ))}
          </ul>
        ) : null}
      </CardContent>
    </Card>
  );
}
