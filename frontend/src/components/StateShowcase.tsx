/**
 * A working preview of the state driven dashboard shell.
 *
 * The component exercises the stores, the layout primitives and the query
 * layer together so the wiring can be validated before the full dashboard
 * modules land.
 */

import { useEffect, useState } from "react";
import { ActivityFeed } from "./layout/ActivityFeed";
import { Sidebar, type NavigationId } from "./layout/Sidebar";
import { TopBar } from "./layout/TopBar";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Skeleton,
  StatCard,
} from "./ui";
import { useDashboardSnapshot, useTeams } from "../api/resources";
import { useHydrateDashboard } from "../hooks/useDashboardData";
import { formatNumber } from "../lib/utils";
import { useActivityStore } from "../stores/activityStore";
import styles from "./StateShowcase.module.css";

/**
 * Render the state driven dashboard shell.
 *
 * @returns The shell element.
 */
export function StateShowcase() {
  const [active, setActive] = useState<NavigationId>("overview");
  const teams = useTeams();
  const snapshot = useDashboardSnapshot(undefined, { refetchInterval: 30_000 });
  const { members } = useHydrateDashboard();
  const pushEvents = useActivityStore((state) => state.pushMany);

  useEffect(() => {
    if (!snapshot.data?.recent_events?.length) return;
    const events = snapshot.data.recent_events.map((event) => ({
      id: event.id,
      team_id: event.team_id,
      kind: event.kind,
      payload: event.payload,
      occurred_at: event.occurred_at,
    }));
    pushEvents(events);
  }, [pushEvents, snapshot.data]);

  const overview = snapshot.data?.overview;

  return (
    <div className={styles.shell}>
      <Sidebar active={active} onNavigate={setActive} />
      <div className={styles.content}>
        <TopBar title="Competition overview" />

        <section className={styles.stats} aria-label="Headline statistics">
          <StatCard
            label="Teams"
            value={
              overview ? (
                formatNumber(overview.teams)
              ) : (
                <Skeleton width={40} height={28} />
              )
            }
            loading={!overview}
          />
          <StatCard
            label="Solves"
            value={
              overview ? (
                formatNumber(overview.solves)
              ) : (
                <Skeleton width={40} height={28} />
              )
            }
            loading={!overview}
          />
          <StatCard
            label="Challenges"
            value={
              overview ? (
                formatNumber(overview.challenges)
              ) : (
                <Skeleton width={40} height={28} />
              )
            }
            loading={!overview}
          />
          <StatCard
            label="Members"
            value={
              overview ? (
                formatNumber(overview.members)
              ) : (
                <Skeleton width={40} height={28} />
              )
            }
            loading={!overview}
          />
        </section>

        <div className={styles.columns}>
          <Card>
            <CardHeader>
              <CardTitle>Leaderboard</CardTitle>
            </CardHeader>
            <CardContent>
              {teams.data && teams.data.length > 0 ? (
                <ul className={styles.leaderboard}>
                  {snapshot.data?.scoreboard.map((row) => (
                    <li key={row.team_id} className={styles.leaderboardRow}>
                      <span className={styles.leaderboardName}>
                        {row.team_name}
                      </span>
                      <span className={styles.leaderboardPoints}>
                        {formatNumber(row.points)}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState
                  title="No teams yet"
                  description="Create a team to get started."
                />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <ActivityFeed loading={!snapshot.data} />
            </CardContent>
          </Card>
        </div>

        <p className={styles.status}>
          {members.data
            ? `${members.data.length} members loaded`
            : "Loading members…"}
        </p>
      </div>
    </div>
  );
}
