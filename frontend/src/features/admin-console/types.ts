export type CaseStatus = "open" | "in_review" | "resolved" | "dismissed";
export type CasePriority = "low" | "normal" | "high" | "critical";
export type ReportType =
  | "harassment"
  | "cheating"
  | "spam"
  | "inappropriate_content"
  | "security_issue"
  | "other";
export type CaseSort =
  "created_desc" | "created_asc" | "priority_desc" | "due_asc";
export type TargetType = "case" | "account" | "system";
export type AdminActionKind =
  | "case_opened"
  | "case_assigned"
  | "case_resolved"
  | "case_dismissed"
  | "account_suspended"
  | "account_activated"
  | "health_recorded";
export type AccountStatus = "active" | "suspended";
export type HealthState = "healthy" | "degraded" | "critical";

export interface ModerationCase {
  id: string;
  report_type: ReportType;
  target_id: string;
  reporter_id: string;
  status: CaseStatus;
  priority: CasePriority;
  assignee_id: string | null;
  resolution: string | null;
  created_at: string;
  due_at: string;
  is_overdue: boolean;
  is_terminal: boolean;
  sla_hours: number;
}

export interface CaseListResponse {
  items: ModerationCase[];
  total: number;
  limit: number;
  offset: number;
}

export interface CaseFilterState {
  status: CaseStatus | "all";
  priority: CasePriority | "all";
  reportType: ReportType | "all";
  assignee: string;
  unassigned: boolean;
  search: string;
  overdueOnly: boolean;
  sort: CaseSort;
  limit: number;
  offset: number;
}

export interface CreateCasePayload {
  report_type: ReportType;
  target_id: string;
  reporter_id: string;
  priority: CasePriority;
}

export interface AccountControl {
  user_id: string;
  username: string;
  role: string;
  status: AccountStatus;
  flags: string[];
  updated_at: string;
  is_suspended: boolean;
  auth_active: boolean;
  is_consistent: boolean;
}

export interface AccountControlListResponse {
  items: AccountControl[];
  suspended: number;
}

export interface AccountStatusPayload {
  user_id: string;
  status: AccountStatus;
  reason: string;
  flags: string[];
}

export interface AdminAction {
  id: string;
  actor_id: string;
  target_type: TargetType;
  target_id: string;
  action: AdminActionKind;
  reason: string;
  created_at: string;
  summary: string;
}

export interface ActionListResponse {
  items: AdminAction[];
  total: number;
  limit: number;
  offset: number;
}

export interface ActionFilterState {
  targetType: TargetType | "all";
  action: AdminActionKind | "all";
  actorId: string;
  search: string;
  limit: number;
}

export interface HealthMetricsPayload {
  database_ok: boolean;
  api_latency_ms: number;
  cache_hit_ratio: number;
  queue_depth: number;
}

export interface SystemHealth {
  id: string;
  checked_at: string;
  database_ok: boolean;
  api_latency_ms: number;
  cache_hit_ratio: number;
  queue_depth: number;
  score: number;
  state: HealthState;
  bottleneck: string;
  is_healthy: boolean;
}

export interface HealthListResponse {
  items: SystemHealth[];
  latest: SystemHealth | null;
}

export interface AdminStats {
  total_cases: number;
  open_cases: number;
  in_review_cases: number;
  resolved_cases: number;
  dismissed_cases: number;
  active_cases: number;
  overdue_cases: number;
  critical_cases: number;
  suspended_accounts: number;
  actions_24h: number;
  health_checks: number;
  latest_score: number;
  database_ok: boolean;
  resolution_rate: number;
  attention_score: number;
  health_state: HealthState;
  priority_counts: Record<string, number>;
  report_counts: Record<string, number>;
}

export interface AdminConsoleData {
  cases: CaseListResponse;
  accounts: AccountControlListResponse;
  actions: ActionListResponse;
  health: HealthListResponse;
  stats: AdminStats;
}

export const DEFAULT_CASE_FILTER: CaseFilterState = {
  status: "all",
  priority: "all",
  reportType: "all",
  assignee: "",
  unassigned: false,
  search: "",
  overdueOnly: false,
  sort: "created_desc",
  limit: 50,
  offset: 0,
};

export const DEFAULT_ACTION_FILTER: ActionFilterState = {
  targetType: "all",
  action: "all",
  actorId: "",
  search: "",
  limit: 100,
};
