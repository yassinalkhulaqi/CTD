/**
 * The analytics page.
 */

import { useMemo } from "react";
import { Activity, BarChart3, Clock, Target, TrendingUp } from "lucide-react";
import { useDashboardSnapshot, useTimeline } from "../../api/resources";
import { useActiveTeamId, windowToHours } from "../../stores/dashboardStore";
import { usePreferencesStore } from "../../stores/preferencesStore";
import { formatDuration, formatNumber } from "../../lib/utils";
import {
  AreaChart,
  BarChart,
  DonutChart,
  Heatmap,
  Sparkline,
  timelineLabels,
  type DonutSlice,
} from "../../components/charts";
import {
  Avatar,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  SegmentedControl,
  Skeleton,
  StatCard,
} from "../../components/ui";
import styles from "./AnalyticsPage.module.css";

const WINDOW_OPTIONS = [
  { value: "6h" as const, label: "6h" },
  { value: "12h" as const, label: "12h" },
  { value: "24h" as const, label: "24h" },
  { value: "7d" as const, label: "7d" },
];

/**
 * Render the analytics page.
 *
 * @returns The page element.
 */
export default function AnalyticsPage() {
  const teamId = useActiveTeamId();
  const timeWindow = usePreferencesStore((state) => state.timeWindow);
  const setTimeWindow = usePreferencesStore((state) => state.setTimeWindow);

  const hours = windowToHours(timeWindow);
  const snapshot = useDashboardSnapshot(teamId ?? undefined, { staleTime: 30_000 });
  const timeline = useTimeline(hours, teamId ?? undefined, { staleTime: 30_000 });

  const buckets = timeline.data ?? [];
  const total = buckets.reduce((sum, value) => sum + value, 0);
  const peak = Math.max(0, ...buckets);
  const average = buckets.length > 0 ? total / buckets.length : 0;

  const labels = useMemo(() => timelineLabels(buckets.length), [buckets.length]);
  const contributions = useMemo(
    () => [...(snapshot.data?.contributions ?? [])].sort((a, b) => b.points - a.points),
    [snapshot.data],
  );
  const maxPoints = Math.max(1, ...contributions.map((row) => row.points));

  const categorySlices = useMemo<DonutSlice[]>(
    () =>
      (snapshot.data?.categories ?? []).map((entry) => ({
        label: entry.label,
        value: entry.challenges,
        color: entry.accent,
      })),
    [snapshot.data],
  );

  const heatmapMatrix = useMemo(() => {
    const matrix = Array.from({ length: 7 }, () => new Array<number>(24).fill(0));
    const solves = snapshot.data?.contributions ?? [];
    for (const contribution of solves) {
      const first = contribution.first_solve_at ? new Date(contribution.first_solve_at) : null;
      if (!first) continue;
      matrix[first.getDay() === 0 ? 6 : first.getDay() - 1][first.getHours()] += contribution.solves;
    }
    return matrix;
  }, [snapshot.data]);

  return (
    <div className={styles.page}>
      <div className={styles.toolbar}>
        <div className={styles.toolbarText}>
          <h2 className={styles.toolbarTitle}>Momentum</h2>
          <p className={styles.toolbarMeta}>
            {`${formatNumber(total)} solves in the last ${timeWindow}, peaking at ${formatNumber(peak)} per hour.`}
          </p>
        </div>
        <SegmentedControl
          options={WINDOW_OPTIONS}
          value={timeWindow}
          onValueChange={setTimeWindow}
          label="Analytics window"
        />
      </div>

      <section className={styles.stats} aria-label="Analytics summary">
        <StatCard
          label="Solves in window"
          value={formatNumber(total)}
          icon={<TrendingUp size={16} />}
          accent="#22d3ee"
          loading={!timeline.data}
          meta={`${average.toFixed(1)} per hour on average`}
        />
        <StatCard
          label="Peak hour"
          value={formatNumber(peak)}
          icon={<BarChart3 size={16} />}
          accent="#f59e0b"
          loading={!timeline.data}
          meta="busiest hour of the window"
        />
        <StatCard
          label="Completion"
          value={
            snapshot.data
              ? `${Math.round(snapshot.data.overview.completion_rate * 100)}%`
              : <Skeleton width={48} height={30} />
          }
          icon={<Target size={16} />}
          accent="#34d399"
          loading={!snapshot.data}
          meta="of the published challenges"
        />
        <StatCard
          label="Time remaining"
          value={
            snapshot.data
              ? formatDuration(snapshot.data.competition_seconds_remaining)
              : <Skeleton width={64} height={30} />
          }
          icon={<Clock size={16} />}
          accent="#a855f7"
          loading={!snapshot.data}
          meta="until the competition closes"
        />
      </section>

      <div className={styles.grid}>
        <Card className={styles.spanTwo}>
          <CardHeader>
            <CardTitle>Solve velocity</CardTitle>
            <CardDescription>Solves recorded per hour over the trailing window.</CardDescription>
          </CardHeader>
          <CardContent>
            {!timeline.data ? (
              <Skeleton height={180} />
            ) : total === 0 ? (
              <EmptyState
                icon={<Activity size={22} />}
                title="No activity in this window"
                description="Widen the time window to see the solve velocity."
              />
            ) : (
              <AreaChart
                values={buckets}
                labels={labels}
                label="Solve velocity"
                height={200}
                color="var(--accent-base)"
              />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Challenge mix</CardTitle>
            <CardDescription>Published challenges per category.</CardDescription>
          </CardHeader>
          <CardContent>
            {categorySlices.length === 0 ? (
              <EmptyState
                icon={<Target size={22} />}
                title="No categories yet"
                description="Publish a challenge to populate the mix."
              />
            ) : (
              <DonutChart
                slices={categorySlices}
                label="Challenge mix"
                centreLabel={formatNumber(
                  categorySlices.reduce((sum, slice) => sum + slice.value, 0),
                )}
              />
            )}
          </CardContent>
        </Card>

        <Card className={styles.spanTwo}>
          <CardHeader>
            <CardTitle>Hourly distribution</CardTitle>
            <CardDescription>Number of solves recorded during each hour.</CardDescription>
          </CardHeader>
          <CardContent>
            {!timeline.data ? (
              <Skeleton height={180} />
            ) : (
              <BarChart
                values={buckets}
                labels={labels}
                label="Hourly distribution"
                unit="solves"
                height={180}
              />
            )}
          </CardContent>
        </Card>

        <Card className={styles.spanTwo}>
          <CardHeader>
            <CardTitle>Activity heatmap</CardTitle>
            <CardDescription>First solves per weekday and hour.</CardDescription>
          </CardHeader>
          <CardContent>
            {heatmapMatrix.every((row) => row.every((value) => value === 0)) ? (
              <EmptyState
                icon={<Activity size={22} />}
                title="Not enough data yet"
                description="The heatmap appears once the team starts solving challenges."
              />
            ) : (
              <Heatmap matrix={heatmapMatrix} label="Activity heatmap" />
            )}
          </CardContent>
        </Card>

        <Card className={styles.spanTwo}>
          <CardHeader>
            <CardTitle>Contributors</CardTitle>
            <CardDescription>Points secured by each member in this event.</CardDescription>
          </CardHeader>
          <CardContent>
            {contributions.length === 0 ? (
              <EmptyState
                icon={<Target size={22} />}
                title="No contributors yet"
                description="Points appear here once the first flag is captured."
              />
            ) : (
              <ul className={styles.contributors}>
                {contributions.slice(0, 8).map((row, index) => (
                  <li key={row.member_id} className={styles.contributor}>
                    <span className={styles.contributorRank}>{index + 1}</span>
                    <Avatar name={row.display_name} size="xs" />
                    <span className={styles.contributorBody}>
                      <span className={styles.contributorName}>{row.display_name}</span>
                      <span className={styles.contributorBar} aria-hidden="true">
                        <span
                          className={styles.contributorBarFill}
                          style={{ width: `${Math.max(4, (row.points / maxPoints) * 100)}%` }}
                        />
                      </span>
                    </span>
                    <Sparkline
                      values={[0, row.solves / 2, row.solves]}
                      label={`Trend of ${row.display_name}`}
                      width={72}
                      height={24}
                    />
                    <span className={styles.contributorPoints}>{formatNumber(row.points)}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
