/**
 * The analytics page.
 *
 * The charts are expanded by the analytics feature branch; this page renders
 * the raw aggregates so the routing is complete.
 */

import { BarChart3, TrendingUp } from "lucide-react";
import { useDashboardSnapshot, useTimeline } from "../../api/resources";
import { useActiveTeamId, windowToHours } from "../../stores/dashboardStore";
import { usePreferencesStore } from "../../stores/preferencesStore";
import { formatNumber } from "../../lib/utils";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Skeleton,
  StatCard,
} from "../../components/ui";
import styles from "./AnalyticsPage.module.css";

/**
 * Render the analytics page.
 *
 * @returns The page element.
 */
export default function AnalyticsPage() {
  const teamId = useActiveTeamId();
  const timeWindow = usePreferencesStore((state) => state.timeWindow);
  const snapshot = useDashboardSnapshot(teamId ?? undefined, { staleTime: 30_000 });
  const timeline = useTimeline(windowToHours(timeWindow), teamId ?? undefined, {
    staleTime: 30_000,
  });

  const buckets = timeline.data ?? [];
  const total = buckets.reduce((sum, value) => sum + value, 0);
  const peak = Math.max(1, ...buckets);

  return (
    <div className={styles.page}>
      <section className={styles.stats} aria-label="Analytics summary">
        <StatCard
          label="Solves in window"
          value={formatNumber(total)}
          icon={<TrendingUp size={16} />}
          accent="#22d3ee"
          loading={!timeline.data}
        />
        <StatCard
          label="Peak hour"
          value={formatNumber(peak)}
          icon={<BarChart3 size={16} />}
          accent="#f59e0b"
          loading={!timeline.data}
        />
        <StatCard
          label="Completion"
          value={
            snapshot.data
              ? `${Math.round(snapshot.data.overview.completion_rate * 100)}%`
              : <Skeleton width={48} height={30} />
          }
          accent="#34d399"
          loading={!snapshot.data}
        />
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Solve velocity</CardTitle>
        </CardHeader>
        <CardContent>
          {!timeline.data ? (
            <Skeleton height={140} />
          ) : buckets.length === 0 || total === 0 ? (
            <EmptyState
              icon={<BarChart3 size={22} />}
              title="No activity in this window"
              description="Widen the time window to see the solve velocity."
            />
          ) : (
            <div className={styles.chart} role="img" aria-label="Solves per hour">
              {buckets.map((value, index) => (
                <span
                  key={index}
                  className={styles.bar}
                  style={{ height: `${Math.max(4, (value / peak) * 100)}%` }}
                  title={`${value} solves`}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
