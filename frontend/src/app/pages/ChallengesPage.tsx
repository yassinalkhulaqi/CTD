/**
 * The challenge board page.
 */

import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Flag, Filter } from "lucide-react";
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
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../../components/ui";
import type { Challenge, ChallengeStatus } from "../../types";
import styles from "./ChallengesPage.module.css";

const STATUS_TONES: Record<ChallengeStatus, "accent" | "success" | "warning" | "danger" | "neutral"> = {
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

  const [selectedId, setSelectedId] = useState<string | null>(params.challengeId ?? null);

  const challenges = useChallenges(
    {
      teamId: teamId ?? undefined,
      category: categoryFilter === "all" ? undefined : categoryFilter,
      status: statusFilter === "all" ? undefined : statusFilter,
    },
    { staleTime: 10_000 },
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

  const selected = filtered.find((challenge) => challenge.id === selectedId) ?? null;

  const byStatus = useMemo(() => {
    const groups: Record<string, Challenge[]> = {
      pending: [],
      active: [],
      solved: [],
      locked: [],
    };
    for (const challenge of filtered) {
      groups[challenge.status]?.push(challenge);
    }
    return groups;
  }, [filtered]);

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
        <CardHeader actions={<Badge tone="neutral">{filtered.length} challenges</Badge>}>
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
          ) : filtered.length === 0 ? (
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
            <Tabs value={statusFilter} onValueChange={(value) => useDashboardStore.getState().setStatusFilter(value as ChallengeStatus | "all")}>
              <TabsList scrollable>
                <TabsTrigger value="all">All</TabsTrigger>
                <TabsTrigger value="pending">Pending</TabsTrigger>
                <TabsTrigger value="active">Active</TabsTrigger>
                <TabsTrigger value="solved">Solved</TabsTrigger>
                <TabsTrigger value="locked">Locked</TabsTrigger>
              </TabsList>

              {(["all", "pending", "active", "solved", "locked"] as const).map((status) => {
                const rows =
                  status === "all"
                    ? filtered
                    : (byStatus[status] ?? []);
                return (
                  <TabsContent key={status} value={status}>
                    {rows.length === 0 ? (
                      <EmptyState
                        icon={<Flag size={20} />}
                        title="Nothing here yet"
                        description="No challenge currently sits in this state."
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
                          {rows.map((challenge) => (
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
                              <TableCell align="right">
                                {formatNumber(challenge.points)}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    )}
                  </TabsContent>
                );
              })}
            </Tabs>
          )}
        </CardContent>
      </Card>

      {selected ? (
        <Card>
          <CardHeader>
            <CardTitle>{selected.title}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={styles.description}>{selected.description || "No description provided."}</p>
            <dl className={styles.details}>
              <div>
                <dt>Category</dt>
                <dd>{selected.category}</dd>
              </div>
              <div>
                <dt>Difficulty</dt>
                <dd>{selected.difficulty}</dd>
              </div>
              <div>
                <dt>Base points</dt>
                <dd>{formatNumber(selected.points)}</dd>
              </div>
              <div>
                <dt>Time remaining</dt>
                <dd>{Math.round(selected.seconds_remaining)}s</dd>
              </div>
            </dl>
            {selected.tags.length > 0 ? (
              <div className={styles.tags}>
                {selected.tags.map((tag) => (
                  <Badge key={tag} tone="info">
                    {tag}
                  </Badge>
                ))}
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
