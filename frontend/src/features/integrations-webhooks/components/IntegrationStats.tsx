/**
 * Headline counters for the integrations screen.
 */

import { Activity, CheckCircle2, PlugZap, Webhook } from "lucide-react";
import { Badge, Progress, StatCard } from "../../../components/ui";
import {
  eventLabel,
  formatTimestamp,
  percentage,
  summariseStats,
  topEvents,
} from "../logic";
import type { IntegrationStats as IntegrationStatsModel } from "../types";
import styles from "./IntegrationStats.module.css";

/** Props accepted by {@link IntegrationStats}. */
export interface IntegrationStatsProps {
  stats: IntegrationStatsModel | null;
  loading?: boolean;
}

/**
 * Render the integration overview tiles and busiest events.
 *
 * @param props - The stats props.
 * @returns The stats element.
 */
export function IntegrationStats({
  stats,
  loading = false,
}: IntegrationStatsProps) {
  if (!stats) {
    return <p className={styles.placeholder}>Statistics are unavailable.</p>;
  }

  const busiest = topEvents(stats);
  return (
    <section className={styles.section} aria-label="Integration statistics">
      <div className={styles.tiles}>
        <StatCard
          label="Integrations"
          value={stats.total_integrations}
          meta={`${stats.enabled_integrations} active`}
          icon={<Webhook size={16} />}
          accent="var(--accent-base)"
          loading={loading}
        />
        <StatCard
          label="Deliveries"
          value={stats.total_deliveries}
          meta={`${stats.pending_deliveries} pending`}
          icon={<Activity size={16} />}
          accent="var(--info-base)"
          loading={loading}
        />
        <StatCard
          label="Success rate"
          value={percentage(stats.success_rate)}
          meta={summariseStats(stats)}
          icon={<CheckCircle2 size={16} />}
          accent="var(--success-base)"
          loading={loading}
        />
        <StatCard
          label="Adapters"
          value={stats.total_adapters}
          meta={`last send ${formatTimestamp(stats.last_sent_at)}`}
          icon={<PlugZap size={16} />}
          accent="var(--warning-base)"
          loading={loading}
        />
      </div>
      <div className={styles.detail}>
        <div className={styles.progressBlock}>
          <span className={styles.label}>Delivery outcomes</span>
          <Progress
            value={stats.success_rate}
            label="Successful deliveries"
            tone="success"
            thin
          />
          <div className={styles.legend}>
            <Badge tone="success" outline>
              {stats.successful_deliveries} delivered
            </Badge>
            <Badge tone="danger" outline>
              {stats.failed_deliveries} failed
            </Badge>
            <Badge tone="warning" outline>
              {stats.pending_deliveries} pending
            </Badge>
          </div>
        </div>
        <div className={styles.events}>
          <span className={styles.label}>Busiest events</span>
          <div className={styles.eventChips}>
            {busiest.length === 0 ? (
              <span className={styles.empty}>No events dispatched yet</span>
            ) : (
              busiest.map(([event, count]) => (
                <Badge key={event} tone="info" outline>
                  {eventLabel(event)} · {count}
                </Badge>
              ))
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
