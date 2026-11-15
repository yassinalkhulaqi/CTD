/**
 * The challenge board page.
 */

import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Flag, LayoutGrid, Rows3 } from "lucide-react";
import { useChallenges } from "../../api/resources";
import { useActiveTeamId, useDashboardStore } from "../../stores/dashboardStore";
import { cn, formatNumber } from "../../lib/utils";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorState,
  SegmentedControl,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "../../components/ui";
import { ChallengeBoard, ChallengeDrawer } from "../../features/challenges";
import type { Challenge, ChallengeStatus } from "../../types";
import styles from "./ChallengesPage.module.css";

const STATUS_TONES: Record<
  ChallengeStatus,
  "accent" | "success" | "warning" | "danger" | "neutral"
> = {
  pending: "neutral",
  active: "accent",
  solved: "success",
  locked: "danger",
};

const DIFFICULTY_TONES: Record<string, "neutral" | "info" | "warning" | "danger"> = {
  trivial: "neutral",
  easy: "neutral",
  medium: "info",
  hard: "warning",
  insane: "danger",
};

const STATUS_ORDER: ChallengeStatus[] = ["pending", "active", "solved", "locked"];

type ViewMode = "board" | "table";

const VIEW_OPTIONS = [
  { value: "board" as const, label: "Board", icon: <LayoutGrid size={13} /> },
  { value: "table" as const, label: "Table", icon: <Rows3 size={13} /> },
];

/**
 * Render the challenge board.
 *
 * @returns The page element.
 */
export default function ChallengesPage() {
  const navigate = useNavigate();
  const params = useParams();
  const teamId = useActiveTeamId();

  const categoryFilter = useDashboardStore((state) => state.categoryFilter);
  const statusFilter = useDashboardStore((state) => state.statusFilter);
  const setStatusFilter = useDashboardStore((state) => state.setStatusFilter);
  const searchQuery = useDashboardStore((state) => state.searchQuery);
  const setSearchQuery = useDashboardStore((state) => state.setSearchQuery);

  const [view, setView] = useState<ViewMode>("board");
  const [selectedId, setSelectedId] = useState<string | null>(params.challengeId ?? null);

  const challenges = useChallenges(
    {
      teamId: teamId ?? undefined,
      category: categoryFilter === "all" ? undefined : categoryFilter,
    },
    { staleTime: 8_000 },
  );

  const filtered = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return challenges.data ?? [];
    return (challenges.data ?? []).filter(
      (challenge) =>
        challenge.title.toLowerCase().includes(query) ||
        challenge.category.includes(query) ||
        challenge.tags.some((tag) => tag.includes(query)),
    );
  }, [challenges.data, searchQuery]);

  const statusCounts = useMemo(() => {
    const source = challenges.data ?? [];
    return STATUS_ORDER.map((status) => ({
      status,
      count: source.filter((challenge) => challenge.status === status).length,
    }));
  }, [challenges.data]);

  const visible = useMemo(
    () =>
      statusFilter === "all"
        ? filtered
        : filtered.filter((challenge) => challenge.status === statusFilter),
    [filtered, statusFilter],
  );

  const selected = useMemo(
    () => filtered.find((challenge) => challenge.id === selectedId) ?? null,
    [filtered, selectedId],
  );

  function select(challenge: Challenge) {
    setSelectedId(challenge.id);
    navigate(`/challenges/${challenge.id}`);
  }

  if (challenges.error) {
    return (
      <ErrorState
        title="The challenge board could not be loaded"
        message={challenges.error instanceof Error ? challenges.error.message : "Unknown error"}
        onRetry={() => void challenges.refetch()}
      />
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.statusChips} role="group" aria-label="Filter by status">
          <button
            type="button"
            className={cn(styles.chip, statusFilter === "all" && styles.chipActive)}
            onClick={() => setStatusFilter("all")}
            aria-pressed={statusFilter === "all"}
          >
            All
            <span className={styles.chipCount}>{challenges.data?.length ?? 0}</span>
          </button>
          {statusCounts.map(({ status, count }) => (
            <button
              key={status}
              type="button"
              className={cn(styles.chip, statusFilter === status && styles.chipActive)}
              onClick={() => setStatusFilter(statusFilter === status ? "all" : status)}
              aria-pressed={statusFilter === status}
              data-status={status}
            >
              <span className={styles.chipDot} aria-hidden="true" />
              <span className={styles.chipLabel}>{status}</span>
              <span className={styles.chipCount}>{count}</span>
            </button>
          ))}
        </div>

        <div className={styles.headerActions}>
          <span className={styles.resultCount}>{visible.length} shown</span>
          <SegmentedControl
            options={VIEW_OPTIONS}
            value={view}
            onValueChange={setView}
            label="View mode"
          />
        </div>
      </div>

      <Card>
        <CardHeader
          actions={
            searchQuery ? (
              <Button variant="ghost" size="sm" onClick={() => setSearchQuery("")}>
                Clear search
              </Button>
            ) : null
          }
        >
          <CardTitle>Challenges</CardTitle>
        </CardHeader>

        <CardContent>
          {!challenges.data ? (
            <div className={styles.skeletons}>
              <Skeleton height={36} />
              <Skeleton height={36} />
              <Skeleton height={36} />
            </div>
          ) : view === "board" ? (
            filtered.length === 0 ? (
              <EmptyState
                icon={<Flag size={22} />}
                title="No challenges match"
                description="Adjust the filters or search terms to see more challenges."
                action={
                  <Button size="sm" onClick={() => setSearchQuery("")}>
                    Clear the search
                  </Button>
                }
              />
            ) : (
              <ChallengeBoard onSelect={select} selectedId={selectedId} />
            )
          ) : visible.length === 0 ? (
            <EmptyState
              icon={<Flag size={22} />}
              title="No challenges match"
              description="Adjust the filters or search terms to see more challenges."
            />
          ) : (
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Challenge</TableHeaderCell>
                  <TableHeaderCell>Category</TableHeaderCell>
                  <TableHeaderCell>Difficulty</TableHeaderCell>
                  <TableHeaderCell>Status</TableHeaderCell>
                  <TableHeaderCell align="right">Points</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {visible.map((challenge) => (
                  <TableRow
                    key={challenge.id}
                    selected={challenge.id === selectedId}
                    onActivate={() => select(challenge)}
                  >
                    <TableCell>
                      <span className={styles.challengeName}>{challenge.title}</span>
                    </TableCell>
                    <TableCell>
                      <Badge tone="neutral">{challenge.category}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge tone={DIFFICULTY_TONES[challenge.difficulty] ?? "neutral"}>
                        {challenge.difficulty}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge tone={STATUS_TONES[challenge.status]} dot>
                        {challenge.status}
                      </Badge>
                    </TableCell>
                    <TableCell align="right">{formatNumber(challenge.points)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <ChallengeDrawer challenge={selected} onClose={() => setSelectedId(null)} />
    </div>
  );
}
