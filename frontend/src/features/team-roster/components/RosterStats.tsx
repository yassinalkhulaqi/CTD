/**
 * Statistics tiles and role/availability breakdowns for the roster page.
 */

import { Activity, Crown, Mail, UserCheck, Users } from "lucide-react";
import { Card, Progress, StatCard } from "../../../components/ui";
import { AVAILABILITY_OPTIONS, ROLE_OPTIONS, formatHours } from "../domain";
import type { RosterStats, RosterSummary } from "../types";
import styles from "./RosterStats.module.css";

/** Props accepted by {@link RosterStatsView}. */
export interface RosterStatsProps {
  /** Statistics returned by the API. */
  stats: RosterStats | null;
  /** Locally derived summary used while the API stats load. */
  summary: RosterSummary;
  /** Whether the initial roster load is in progress. */
  loading?: boolean;
}

/**
 * Render roster statistics with accessible progress indicators.
 *
 * @param props - The component props.
 * @returns The statistics section element.
 */
export function RosterStatsView({
  stats,
  summary,
  loading = false,
}: RosterStatsProps) {
  const memberCount = stats?.total_members ?? summary.members;
  const utilisation = stats?.utilisation ?? summary.utilisation;
  const pending = stats?.pending_invitations ?? summary.pending;

  return (
    <section className={styles.section} aria-labelledby="roster-stats-title">
      <div className={styles.heading}>
        <h2 id="roster-stats-title" className={styles.title}>
          Roster overview
        </h2>
        <p className={styles.subtitle}>
          Live capacity and composition of the team.
        </p>
      </div>

      <div className={styles.tiles}>
        <StatCard
          label="Members"
          value={memberCount}
          icon={<Users size={17} />}
          accent="var(--accent-base)"
          meta={
            stats ? `${stats.total_capacity_hours}h planned` : "Loading details"
          }
          loading={loading}
        />
        <StatCard
          label="Leads"
          value={stats?.lead_count ?? summary.leads}
          icon={<Crown size={17} />}
          accent="var(--warning-base)"
          meta="Can change roles"
          loading={loading}
        />
        <StatCard
          label="Available"
          value={stats?.available_count ?? summary.available}
          icon={<UserCheck size={17} />}
          accent="var(--success-base)"
          meta="Ready for work"
          loading={loading}
        />
        <StatCard
          label="Pending invites"
          value={pending}
          icon={<Mail size={17} />}
          accent="var(--info-base)"
          meta="Awaiting response"
          loading={loading}
        />
        <StatCard
          label="Utilisation"
          value={`${Math.round(utilisation * 100)}%`}
          icon={<Activity size={17} />}
          accent="var(--accent-base)"
          meta={
            stats
              ? `${formatHours(stats.assigned_hours)} reserved`
              : "Across the roster"
          }
          loading={loading}
        />
      </div>

      <div className={styles.breakdowns}>
        <Card className={styles.panel}>
          <h3 className={styles.panelTitle}>By role</h3>
          <div className={styles.rows}>
            {ROLE_OPTIONS.map((option) => {
              const count = stats?.by_role[option.value] ?? 0;
              return (
                <div className={styles.row} key={option.value}>
                  <span className={styles.rowLabel}>{option.label}</span>
                  <Progress
                    value={count}
                    max={Math.max(1, memberCount)}
                    label={`${option.label} members`}
                    className={styles.bar}
                  />
                  <span className={styles.rowValue}>{count}</span>
                </div>
              );
            })}
          </div>
        </Card>
        <Card className={styles.panel}>
          <h3 className={styles.panelTitle}>By availability</h3>
          <div className={styles.rows}>
            {AVAILABILITY_OPTIONS.map((option) => {
              const count = stats?.by_availability[option.value] ?? 0;
              return (
                <div className={styles.row} key={option.value}>
                  <span className={styles.rowLabel}>{option.label}</span>
                  <Progress
                    value={count}
                    max={Math.max(1, memberCount)}
                    tone={
                      option.tone === "success"
                        ? "success"
                        : option.tone === "warning"
                          ? "warning"
                          : "accent"
                    }
                    label={`${option.label} members`}
                    className={styles.bar}
                  />
                  <span className={styles.rowValue}>{count}</span>
                </div>
              );
            })}
          </div>
        </Card>
      </div>
    </section>
  );
}
