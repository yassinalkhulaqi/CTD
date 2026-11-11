/**
 * The challenge board page.
 */

import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Flag, Filter, LayoutGrid, Rows3 } from "lucide-react";
import { useChallenges } from "../../api/resources";
import { useActiveTeamId, useDashboardStore } from "../../stores/dashboardStore";
import { formatNumber } from "../../lib/utils";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorState,
  Input,
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
  const searchQuery = useDashboardStore((state) => state.searchQuery);
  const setSearchQuery = useDashboardStore((state) => state.setSearchQuery);

  const [view, setView] = useState<ViewMode>("board");
  const [selectedId, setSelectedId] = useState<string | null>(params.challengeId ?? null);

  const challenges = useChallenges(
    {
      teamId: teamId ?? undefined,
      category: categoryFilter === "all" ? undefined : categoryFilter,
      status: statusFilter === "all" ? undefined : statusFilter,
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
      <Card>
        <CardHeader
          actions={
            <div className={styles.headerActions}>
              <Badge tone="neutral">{filtered.length} challenges</Badge>
              <SegmentedControl
                options={VIEW_OPTIONS}
                value={view}
                onValueChange={setView}
                label="View mode"
              />
            </div>
          }
        >
          <CardTitle>Challenge board</CardTitle>
        </CardHeader>
        <CardContent>
          <div className={styles.toolbar}>
            <Input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Filter by title, category or tag…"
              icon={<Filter size={14} />}
              hideLabel
              aria-label="Filter challenges"
              className={styles.search}
            />
            {searchQuery ? (
              <Button variant="ghost" size="sm" onClick={() => setSearchQuery("")}>
                Reset
              </Button>
            ) : null}
          </div>

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
          ) : filtered.length === 0 ? (
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
                {filtered.map((challenge) => (
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
