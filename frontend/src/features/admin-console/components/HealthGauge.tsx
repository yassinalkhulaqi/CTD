import { useState, type CSSProperties, type FormEvent } from "react";
import { Activity, Database, Gauge, Layers3, Timer } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Checkbox,
  Input,
  Skeleton,
} from "../../../components/ui";
import { formatPercent, formatRelativeTime } from "../../../lib/utils";
import {
  HEALTH_TONES,
  healthBottleneckLabel,
  healthScore,
  healthStateFor,
} from "../logic";
import type { HealthMetricsPayload, SystemHealth } from "../types";
import styles from "./HealthGauge.module.css";

export interface HealthGaugeProps {
  health: SystemHealth | null;
  loading?: boolean;
  busy?: boolean;
  onRecord?: (payload: HealthMetricsPayload) => Promise<boolean> | boolean;
}

const TONE_COLORS: Record<string, string> = {
  healthy: "var(--success-base)",
  degraded: "var(--warning-base)",
  critical: "var(--danger-base)",
};

export function HealthGauge({
  health,
  loading = false,
  busy = false,
  onRecord,
}: HealthGaugeProps) {
  const [databaseOk, setDatabaseOk] = useState(true);
  const [latency, setLatency] = useState("120");
  const [cache, setCache] = useState("92");
  const [queue, setQueue] = useState("4");
  const [formError, setFormError] = useState<string | null>(null);

  const previewMetrics: HealthMetricsPayload = {
    database_ok: databaseOk,
    api_latency_ms: Number(latency) || 0,
    cache_hit_ratio: (Number(cache) || 0) / 100,
    queue_depth: Number(queue) || 0,
  };
  const previewScore = healthScore(previewMetrics);
  const previewState = healthStateFor(previewScore, databaseOk);
  const score = health?.score ?? 0;
  const state = health?.state ?? "critical";
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const offset =
    circumference - (Math.max(0, Math.min(100, score)) / 100) * circumference;

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    const parsedLatency = Number(latency);
    const parsedCache = Number(cache);
    const parsedQueue = Number(queue);
    if (
      !Number.isFinite(parsedLatency) ||
      !Number.isFinite(parsedCache) ||
      !Number.isFinite(parsedQueue) ||
      parsedLatency < 0 ||
      parsedCache < 0 ||
      parsedCache > 100 ||
      parsedQueue < 0
    ) {
      setFormError(
        "Enter non-negative metrics and a cache ratio between 0 and 100.",
      );
      return;
    }
    setFormError(null);
    await onRecord?.({
      database_ok: databaseOk,
      api_latency_ms: parsedLatency,
      cache_hit_ratio: parsedCache / 100,
      queue_depth: Math.round(parsedQueue),
    });
  }

  if (loading) {
    return (
      <Card className={styles.card}>
        <CardHeader>
          <Skeleton width={140} height={18} />
        </CardHeader>
        <CardContent>
          <Skeleton height={190} />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      className={styles.card}
      as="section"
      aria-labelledby="admin-health-title"
    >
      <CardHeader
        actions={
          <Badge tone={HEALTH_TONES[state]} dot>
            {state}
          </Badge>
        }
      >
        <CardTitle id="admin-health-title" level={3}>
          System health
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div
          className={styles.summary}
          style={{ "--gauge-color": TONE_COLORS[state] } as CSSProperties}
        >
          <svg
            className={styles.gauge}
            viewBox="0 0 120 120"
            role="img"
            aria-label={`Health score ${score} of 100`}
          >
            <circle className={styles.gaugeTrack} cx="60" cy="60" r={radius} />
            <circle
              className={styles.gaugeValue}
              cx="60"
              cy="60"
              r={radius}
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              transform="rotate(-90 60 60)"
            />
            <text
              className={styles.gaugeText}
              x="60"
              y="64"
              textAnchor="middle"
            >
              {Math.round(score)}
            </text>
          </svg>
          <div className={styles.summaryText}>
            <span className={styles.summaryLabel}>Health score</span>
            <strong className={styles.summaryValue}>
              {health ? `${score.toFixed(1)} / 100` : "No checks yet"}
            </strong>
            <span className={styles.summaryMeta}>
              {health
                ? `Checked ${formatRelativeTime(health.checked_at)}`
                : "Record the first snapshot"}
            </span>
            {health ? (
              <span className={styles.bottleneck}>
                Bottleneck: {healthBottleneckLabel(health.bottleneck)}
              </span>
            ) : null}
          </div>
        </div>

        <dl className={styles.metrics}>
          <div className={styles.metric}>
            <dt>
              <Database size={14} aria-hidden="true" /> Database
            </dt>
            <dd>
              {health ? (health.database_ok ? "online" : "offline") : "—"}
            </dd>
          </div>
          <div className={styles.metric}>
            <dt>
              <Timer size={14} aria-hidden="true" /> API latency
            </dt>
            <dd>{health ? `${Math.round(health.api_latency_ms)} ms` : "—"}</dd>
          </div>
          <div className={styles.metric}>
            <dt>
              <Layers3 size={14} aria-hidden="true" /> Cache hits
            </dt>
            <dd>{health ? formatPercent(health.cache_hit_ratio, 0) : "—"}</dd>
          </div>
          <div className={styles.metric}>
            <dt>
              <Activity size={14} aria-hidden="true" /> Queue depth
            </dt>
            <dd>{health ? health.queue_depth : "—"}</dd>
          </div>
        </dl>

        <form
          className={styles.form}
          onSubmit={(event) => void handleSubmit(event)}
        >
          <p className={styles.formTitle}>
            <Gauge size={14} aria-hidden="true" /> Record a snapshot
          </p>
          <div className={styles.formGrid}>
            <Input
              label="API latency (ms)"
              type="number"
              min="0"
              value={latency}
              onChange={(event) => setLatency(event.target.value)}
            />
            <Input
              label="Cache hit ratio (%)"
              type="number"
              min="0"
              max="100"
              value={cache}
              onChange={(event) => setCache(event.target.value)}
            />
            <Input
              label="Queue depth"
              type="number"
              min="0"
              value={queue}
              onChange={(event) => setQueue(event.target.value)}
            />
            <div className={styles.databaseToggle}>
              <Checkbox
                label="Database reachable"
                checked={databaseOk}
                onChange={(event) => setDatabaseOk(event.target.checked)}
              />
              <Badge tone={HEALTH_TONES[previewState]} outline>
                preview {previewScore.toFixed(1)}
              </Badge>
            </div>
          </div>
          {formError ? (
            <p className={styles.error} role="alert">
              {formError}
            </p>
          ) : null}
          <Button type="submit" size="sm" loading={busy} loadingLabel="Saving">
            Save health check
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
