/**
 * Routed achievements screen: badge gallery, progress, evaluation and rankings.
 */

import { useEffect, useMemo, useState } from "react";
import { RefreshCw, SearchX, Sparkles, Trophy } from "lucide-react";
import { useMembers } from "../../api";
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorState,
  Skeleton,
} from "../../components/ui";
import {
  useAchievementBadges,
  useAchievementLeaderboard,
  useAchievementStats,
  useAwardBadge,
  useEvaluateAchievements,
  useMemberAchievements,
} from "./hooks";
import {
  filterBadges,
  sortBadges,
  statusCounts,
  type BadgeTier,
  type BadgeView,
  type CriteriaKind,
} from "./types";
import { AchievementStatsPanel } from "./components/AchievementStats";
import { BadgeCard } from "./components/BadgeCard";
import { BadgeDetail } from "./components/BadgeDetail";
import { LeaderboardPanel } from "./components/LeaderboardPanel";
import { TierFilter } from "./components/TierFilter";
import { UnlockToast } from "./components/UnlockToast";
import styles from "./AchievementsPage.module.css";

/** Metric keys exposed by the evaluation form. */
const METRIC_FIELDS: Array<{ key: string; label: string; hint: string }> = [
  { key: "solves", label: "Solves", hint: "Total challenge solves" },
  {
    key: "categories",
    label: "Categories",
    hint: "Distinct categories solved",
  },
  { key: "streak", label: "Streak", hint: "Consecutive solve days" },
  { key: "hints", label: "Hints", hint: "Hints used so far" },
];

/** Render the achievements feature route. */
export function AchievementsPage() {
  const membersQuery = useMembers({}, { staleTime: 30_000 });
  const [memberId, setMemberId] = useState<string | null>(null);
  const [tier, setTier] = useState<BadgeTier | "all">("all");
  const [kind, setKind] = useState<CriteriaKind | "all">("all");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<BadgeView | null>(null);
  const [unlocks, setUnlocks] = useState<BadgeView[]>([]);
  const [metrics, setMetrics] = useState<Record<string, number>>({
    solves: 5,
    categories: 2,
    streak: 3,
    hints: 2,
  });

  useEffect(() => {
    if (memberId || !membersQuery.data?.length) return;
    setMemberId(membersQuery.data[0].id);
  }, [memberId, membersQuery.data]);

  const badgeQuery = useAchievementBadges({
    member_id: memberId ?? undefined,
    tier: tier === "all" ? undefined : tier,
    criteria_kind: kind === "all" ? undefined : kind,
  });
  const statsQuery = useAchievementStats();
  const leaderboardQuery = useAchievementLeaderboard(8);
  const memberQuery = useMemberAchievements(memberId);
  const evaluateMutation = useEvaluateAchievements();
  const awardMutation = useAwardBadge();

  const allViews = useMemo(
    () => badgeQuery.data?.badges ?? [],
    [badgeQuery.data],
  );
  const views = useMemo(
    () => sortBadges(filterBadges(allViews, tier, kind, query)),
    [allViews, tier, kind, query],
  );
  const counts = useMemo(() => {
    const result: Record<BadgeTier | "all", number> = {
      all: allViews.length,
      bronze: 0,
      silver: 0,
      gold: 0,
    };
    for (const view of allViews) result[view.badge.tier] += 1;
    return result;
  }, [allViews]);
  const statuses = useMemo(() => statusCounts(allViews), [allViews]);
  const selectedView = selected
    ? (views.find((view) => view.badge.id === selected.badge.id) ?? selected)
    : null;

  async function handleEvaluate() {
    if (!memberId) return;
    const result = await evaluateMutation.mutate({ memberId, metrics });
    if (!result) return;
    const unlockedIds = new Set(
      result.outcomes
        .filter((outcome) => outcome.newly_awarded)
        .map((outcome) => outcome.badge_id),
    );
    setUnlocks(allViews.filter((view) => unlockedIds.has(view.badge.id)));
  }

  async function handleAward() {
    if (!memberId || !selectedView) return;
    await awardMutation.mutate({ memberId, badgeId: selectedView.badge.id });
  }

  const loading = badgeQuery.isLoading || statsQuery.isLoading;
  const failed = badgeQuery.error || statsQuery.error;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.heading}>
          <span className={styles.eyebrow}>
            <Trophy size={14} aria-hidden="true" /> Progress
          </span>
          <h1>Achievements</h1>
          <p>Track badges, celebrate unlocks and see how the team stacks up.</p>
        </div>
        <div className={styles.headerActions}>
          <label className={styles.memberSelect}>
            <span>Viewing member</span>
            <select
              value={memberId ?? ""}
              onChange={(event) => setMemberId(event.target.value || null)}
              disabled={membersQuery.isLoading}
            >
              <option value="">Select a member</option>
              {(membersQuery.data ?? []).map((member) => (
                <option key={member.id} value={member.id}>
                  {member.display_name || member.handle}
                </option>
              ))}
            </select>
          </label>
          <Button
            variant="secondary"
            icon={<RefreshCw size={15} />}
            onClick={() => {
              void badgeQuery.refetch();
              void statsQuery.refetch();
              void leaderboardQuery.refetch();
            }}
            loading={badgeQuery.isFetching || statsQuery.isFetching}
            loadingLabel="Refreshing"
          >
            Refresh
          </Button>
        </div>
      </header>

      <AchievementStatsPanel stats={statsQuery.data} loading={loading} />

      {failed ? (
        <ErrorState
          title="Achievement data is unavailable"
          message="The badge service could not be reached. Please retry."
          onRetry={() => {
            void badgeQuery.refetch();
            void statsQuery.refetch();
          }}
        />
      ) : null}

      <div className={styles.layout}>
        <div className={styles.gallery}>
          <section
            aria-labelledby="gallery-heading"
            className={styles.gallerySection}
          >
            <CardHeader
              actions={
                <span className={styles.summary}>
                  {statuses.unlocked} unlocked · {statuses.ready} ready ·{" "}
                  {statuses.locked} locked
                </span>
              }
            >
              <h2 id="gallery-heading" className={styles.sectionTitle}>
                Badge gallery
              </h2>
            </CardHeader>

            <TierFilter
              tier={tier}
              kind={kind}
              query={query}
              counts={counts}
              onTierChange={setTier}
              onKindChange={setKind}
              onQueryChange={setQuery}
            />

            {loading ? (
              <div className={styles.grid} aria-busy="true">
                {[0, 1, 2, 3, 4, 5].map((index) => (
                  <Card key={index} className={styles.skeletonCard}>
                    <Skeleton height={68} circle />
                    <Skeleton height={16} />
                    <Skeleton lines={2} />
                  </Card>
                ))}
              </div>
            ) : views.length === 0 ? (
              <EmptyState
                icon={<SearchX size={20} />}
                title="No badges match"
                description="Try a different tier, criterion or search term."
                action={
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setTier("all");
                      setKind("all");
                      setQuery("");
                    }}
                  >
                    Clear filters
                  </Button>
                }
              />
            ) : (
              <div className={styles.grid}>
                {views.map((view) => (
                  <BadgeCard
                    key={view.badge.id}
                    view={view}
                    onSelect={setSelected}
                    selected={selected?.badge.id === view.badge.id}
                    newlyUnlocked={unlocks.some(
                      (unlock) => unlock.badge.id === view.badge.id,
                    )}
                  />
                ))}
              </div>
            )}
          </section>

          <Card className={styles.evaluateCard} as="section" bare>
            <CardHeader>
              <CardTitle level={3}>Evaluate member metrics</CardTitle>
              <CardDescription>
                Re-run the criteria engine to refresh progress and unlock
                badges.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form
                className={styles.metricForm}
                onSubmit={(event) => {
                  event.preventDefault();
                  void handleEvaluate();
                }}
              >
                {METRIC_FIELDS.map((field) => (
                  <label key={field.key} className={styles.metricField}>
                    <span>{field.label}</span>
                    <input
                      type="number"
                      min={0}
                      value={metrics[field.key] ?? 0}
                      onChange={(event) =>
                        setMetrics((current) => ({
                          ...current,
                          [field.key]: Math.max(0, Number(event.target.value)),
                        }))
                      }
                    />
                    <small>{field.hint}</small>
                  </label>
                ))}
                <div className={styles.formActions}>
                  <Button
                    type="submit"
                    icon={<Sparkles size={15} />}
                    loading={evaluateMutation.isPending}
                    loadingLabel="Evaluating"
                    disabled={!memberId}
                  >
                    Evaluate metrics
                  </Button>
                  {memberQuery.data ? (
                    <span className={styles.memberSummary}>
                      {memberQuery.data.unlocked} badges ·{" "}
                      {memberQuery.data.points} pts
                    </span>
                  ) : null}
                </div>
                {evaluateMutation.error ? (
                  <p className={styles.error} role="alert">
                    Evaluation failed. Please check the selected member.
                  </p>
                ) : null}
              </form>
            </CardContent>
          </Card>
        </div>

        <aside className={styles.sidebar} aria-label="Achievement rankings">
          <LeaderboardPanel
            entries={leaderboardQuery.data?.entries}
            loading={leaderboardQuery.isLoading}
            highlightedMemberId={memberId}
          />
          <Card className={styles.tipCard} bare>
            <CardHeader>
              <CardTitle level={3}>How rarity works</CardTitle>
            </CardHeader>
            <CardContent>
              <p>
                Rarity falls as more members unlock a badge. Legendary badges
                are held by fewer than one in ten members.
              </p>
              <p>
                Secret badges stay masked until you earn them — keep exploring.
              </p>
            </CardContent>
          </Card>
        </aside>
      </div>

      <BadgeDetail
        view={selectedView}
        open={selected !== null}
        onClose={() => setSelected(null)}
        awardedTo={selectedView?.holders ?? 0}
        awardedAt={
          selectedView
            ? memberQuery.data?.awards.find(
                (award) => award.badge_id === selectedView.badge.id,
              )?.awarded_at
            : undefined
        }
        onAward={memberId ? handleAward : undefined}
        awarding={awardMutation.isPending}
      />

      <UnlockToast badges={unlocks} onDismiss={() => setUnlocks([])} />
    </div>
  );
}
