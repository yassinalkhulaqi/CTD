import {
  Activity,
  CheckCircle2,
  Clock3,
  Gauge,
  ScrollText,
  ShieldAlert,
} from "lucide-react";
import { StatCard, type StatCardProps } from "../../../components/ui";
import { formatPercent } from "../../../lib/utils";
import { HEALTH_ACCENTS } from "../logic";
import type { AdminStats as AdminStatsModel } from "../types";
import styles from "./AdminStats.module.css";

export interface AdminStatsProps {
  stats: AdminStatsModel | null;
  loading?: boolean;
}

export function AdminStats({ stats, loading = false }: AdminStatsProps) {
  const cards: Array<Omit<StatCardProps, "key"> & { key: string }> = [
    {
      key: "open",
      label: "Open reports",
      value: stats?.open_cases ?? 0,
      meta: `${stats?.in_review_cases ?? 0} in review`,
      icon: <ShieldAlert size={16} />,
      accent: "var(--info-base)",
    },
    {
      key: "overdue",
      label: "SLA breaches",
      value: stats?.overdue_cases ?? 0,
      meta: `${stats?.critical_cases ?? 0} critical priority`,
      icon: <Clock3 size={16} />,
      accent: "var(--danger-base)",
    },
    {
      key: "resolution",
      label: "Resolution rate",
      value: formatPercent(stats?.resolution_rate ?? 0, 0),
      meta: `${stats?.resolved_cases ?? 0} of ${stats?.total_cases ?? 0} cases`,
      icon: <CheckCircle2 size={16} />,
      accent: "var(--success-base)",
    },
    {
      key: "suspended",
      label: "Suspended accounts",
      value: stats?.suspended_accounts ?? 0,
      meta: `${stats?.attention_score ?? 0} attention items`,
      icon: <Activity size={16} />,
      accent: "var(--warning-base)",
    },
    {
      key: "audit",
      label: "Actions (24h)",
      value: stats?.actions_24h ?? 0,
      meta: `${stats?.health_checks ?? 0} health checks`,
      icon: <ScrollText size={16} />,
      accent: "var(--accent-base)",
    },
    {
      key: "health",
      label: "Health score",
      value: stats ? `${stats.latest_score.toFixed(1)}` : "—",
      meta: stats?.health_state ?? "unknown",
      icon: <Gauge size={16} />,
      accent: stats
        ? HEALTH_ACCENTS[stats.health_state]
        : "var(--text-tertiary)",
    },
  ];

  return (
    <section className={styles.grid} aria-label="Administration statistics">
      {cards.map((card) => {
        const { key, ...props } = card;
        return <StatCard key={key} loading={loading} {...props} />;
      })}
    </section>
  );
}
