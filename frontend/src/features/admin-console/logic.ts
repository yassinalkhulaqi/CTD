import type { BadgeTone } from "../../components/ui";
import { clamp, formatCompactDuration, formatPercent } from "../../lib/utils";
import type {
  AccountControl,
  ActionFilterState,
  AdminAction,
  AdminActionKind,
  CaseFilterState,
  CasePriority,
  CaseSort,
  CaseStatus,
  HealthMetricsPayload,
  HealthState,
  ModerationCase,
  ReportType,
} from "./types";

export const STATUS_TONES: Record<CaseStatus, BadgeTone> = {
  open: "info",
  in_review: "warning",
  resolved: "success",
  dismissed: "neutral",
};

export const PRIORITY_TONES: Record<CasePriority, BadgeTone> = {
  low: "neutral",
  normal: "info",
  high: "warning",
  critical: "danger",
};

export const HEALTH_TONES: Record<HealthState, BadgeTone> = {
  healthy: "success",
  degraded: "warning",
  critical: "danger",
};

export const HEALTH_ACCENTS: Record<HealthState, string> = {
  healthy: "var(--success-base)",
  degraded: "var(--warning-base)",
  critical: "var(--danger-base)",
};

export const ACTION_TONES: Record<AdminActionKind, BadgeTone> = {
  case_opened: "info",
  case_assigned: "accent",
  case_resolved: "success",
  case_dismissed: "neutral",
  account_suspended: "danger",
  account_activated: "success",
  health_recorded: "info",
};

export const REPORT_LABELS: Record<ReportType, string> = {
  harassment: "Harassment",
  cheating: "Cheating",
  spam: "Spam",
  inappropriate_content: "Inappropriate content",
  security_issue: "Security issue",
  other: "Other",
};

export const CASE_STATUS_LABELS: Record<CaseStatus, string> = {
  open: "Open",
  in_review: "In review",
  resolved: "Resolved",
  dismissed: "Dismissed",
};

export const PRIORITY_LABELS: Record<CasePriority, string> = {
  low: "Low",
  normal: "Normal",
  high: "High",
  critical: "Critical",
};

const PRIORITY_RANK: Record<CasePriority, number> = {
  low: 1,
  normal: 2,
  high: 3,
  critical: 4,
};

export function titleCase(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function healthScore(metrics: HealthMetricsPayload): number {
  const database = metrics.database_ok ? 1 : 0;
  const latency = clamp(1 - Math.max(0, metrics.api_latency_ms) / 2000, 0, 1);
  const cache = clamp(metrics.cache_hit_ratio, 0, 1);
  const queue = clamp(1 - Math.max(0, metrics.queue_depth) / 500, 0, 1);
  const weighted = database * 0.4 + latency * 0.25 + cache * 0.2 + queue * 0.15;
  return Math.round(clamp(weighted, 0, 1) * 1000) / 10;
}

export function healthStateFor(
  score: number,
  databaseOk: boolean,
): HealthState {
  if (!databaseOk) return "critical";
  if (score >= 85) return "healthy";
  if (score >= 60) return "degraded";
  return "critical";
}

export function formatSla(
  item: ModerationCase,
  nowMs: number = Date.now(),
): string {
  if (item.is_terminal) return "closed";
  const remainingMs = Date.parse(item.due_at) - nowMs;
  if (Number.isNaN(remainingMs)) return "unknown";
  const duration = formatCompactDuration(Math.abs(remainingMs) / 1000);
  if (remainingMs < 0) return `overdue ${duration}`;
  if (remainingMs < 45 * 60 * 1000) return `due ${duration}`;
  return `${duration} left`;
}

export function filterCases(
  cases: ModerationCase[],
  filter: CaseFilterState,
): ModerationCase[] {
  const needle = filter.search.trim().toLowerCase();
  const matches = cases.filter((item) => {
    if (filter.status !== "all" && item.status !== filter.status) return false;
    if (filter.priority !== "all" && item.priority !== filter.priority)
      return false;
    if (filter.reportType !== "all" && item.report_type !== filter.reportType)
      return false;
    if (filter.assignee && item.assignee_id !== filter.assignee) return false;
    if (filter.unassigned && item.assignee_id !== null) return false;
    if (filter.overdueOnly && (!item.is_overdue || item.is_terminal))
      return false;
    if (!needle) return true;
    const haystack = [
      item.id,
      item.target_id,
      item.reporter_id,
      item.resolution ?? "",
      REPORT_LABELS[item.report_type],
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(needle);
  });

  const byCreated = (left: ModerationCase, right: ModerationCase): number =>
    Date.parse(right.created_at) - Date.parse(left.created_at);
  const sorter: Record<
    CaseSort,
    (left: ModerationCase, right: ModerationCase) => number
  > = {
    created_desc: byCreated,
    created_asc: (left, right) => -byCreated(left, right),
    priority_desc: (left, right) =>
      PRIORITY_RANK[right.priority] - PRIORITY_RANK[left.priority] ||
      byCreated(left, right),
    due_asc: (left, right) =>
      Date.parse(left.due_at) - Date.parse(right.due_at) ||
      byCreated(left, right),
  };

  return [...matches]
    .sort(sorter[filter.sort])
    .slice(filter.offset, filter.offset + filter.limit);
}

export function filterActions(
  actions: AdminAction[],
  filter: ActionFilterState,
): AdminAction[] {
  const needle = filter.search.trim().toLowerCase();
  return actions
    .filter((entry) => {
      if (
        filter.targetType !== "all" &&
        entry.target_type !== filter.targetType
      ) {
        return false;
      }
      if (filter.action !== "all" && entry.action !== filter.action)
        return false;
      if (
        filter.actorId &&
        !entry.actor_id.toLowerCase().includes(filter.actorId.toLowerCase())
      ) {
        return false;
      }
      if (!needle) return true;
      const haystack = [
        entry.target_id,
        entry.reason,
        entry.summary,
        titleCase(entry.action),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(needle);
    })
    .slice(0, filter.limit);
}

export function summarizeAccounts(accounts: AccountControl[]): {
  total: number;
  active: number;
  suspended: number;
  flagged: number;
} {
  return {
    total: accounts.length,
    active: accounts.filter((account) => !account.is_suspended).length,
    suspended: accounts.filter((account) => account.is_suspended).length,
    flagged: accounts.filter((account) => account.flags.length > 0).length,
  };
}

export function describeAction(entry: AdminAction): string {
  if (entry.reason) return entry.reason;
  return titleCase(entry.action);
}

export function formatHealthPercent(ratio: number): string {
  return formatPercent(ratio, 0);
}

export function isCaseAction(entry: AdminAction): boolean {
  return entry.target_type === "case";
}

export function canSuspend(
  account: AccountControl,
  operatorId: string,
): boolean {
  return (
    account.user_id !== operatorId &&
    account.role !== "admin" &&
    !account.is_suspended
  );
}

export function healthBottleneckLabel(metric: string): string {
  const labels: Record<string, string> = {
    database: "Database availability",
    api_latency: "API latency",
    cache_hit_ratio: "Cache hit ratio",
    queue_depth: "Queue depth",
  };
  return labels[metric] ?? titleCase(metric);
}
