import { buildQuery, get, post } from "../../api/client";
import type { RequestOptions } from "../../api/client";
import {
  DEFAULT_ACTION_FILTER,
  DEFAULT_CASE_FILTER,
  type AccountControlListResponse,
  type AccountStatusPayload,
  type ActionFilterState,
  type ActionListResponse,
  type AdminStats,
  type CaseFilterState,
  type CaseListResponse,
  type CreateCasePayload,
  type HealthListResponse,
  type HealthMetricsPayload,
  type ModerationCase,
  type SystemHealth,
} from "./types";

export interface ApiOptions {
  signal?: AbortSignal;
}

function caseQuery(
  filter: Partial<CaseFilterState>,
): Record<string, string | number | boolean> {
  const value = { ...DEFAULT_CASE_FILTER, ...filter };
  return {
    status: value.status === "all" ? "" : value.status,
    priority: value.priority === "all" ? "" : value.priority,
    report_type: value.reportType === "all" ? "" : value.reportType,
    assignee_id: value.assignee,
    unassigned: value.unassigned,
    search: value.search,
    overdue: value.overdueOnly,
    sort: value.sort,
    limit: value.limit,
    offset: value.offset,
  };
}

function actionQuery(
  filter: Partial<ActionFilterState>,
): Record<string, string | number> {
  const value = { ...DEFAULT_ACTION_FILTER, ...filter };
  return {
    target_type: value.targetType === "all" ? "" : value.targetType,
    action: value.action === "all" ? "" : value.action,
    actor_id: value.actorId,
    search: value.search,
    limit: value.limit,
  };
}

function requestOptions(options: ApiOptions): RequestOptions {
  return { signal: options.signal };
}

export const adminApi = {
  listCases(
    filter: Partial<CaseFilterState> = {},
    options: ApiOptions = {},
  ): Promise<CaseListResponse> {
    return get<CaseListResponse>(
      `/api/admin/cases${buildQuery(caseQuery(filter))}`,
      requestOptions(options),
    );
  },

  createCase(
    payload: CreateCasePayload,
    options: ApiOptions = {},
  ): Promise<ModerationCase> {
    return post<ModerationCase>(
      "/api/admin/cases",
      payload,
      requestOptions(options),
    );
  },

  assignCase(
    caseId: string,
    assigneeId: string,
    options: ApiOptions = {},
  ): Promise<ModerationCase> {
    return post<ModerationCase>(
      `/api/admin/cases/${encodeURIComponent(caseId)}/assign`,
      { assignee_id: assigneeId },
      requestOptions(options),
    );
  },

  resolveCase(
    caseId: string,
    resolution: string,
    options: ApiOptions = {},
  ): Promise<ModerationCase> {
    return post<ModerationCase>(
      `/api/admin/cases/${encodeURIComponent(caseId)}/resolve`,
      { resolution },
      requestOptions(options),
    );
  },

  dismissCase(
    caseId: string,
    reason: string,
    options: ApiOptions = {},
  ): Promise<ModerationCase> {
    return post<ModerationCase>(
      `/api/admin/cases/${encodeURIComponent(caseId)}/dismiss`,
      { reason },
      requestOptions(options),
    );
  },

  listAccounts(options: ApiOptions = {}): Promise<AccountControlListResponse> {
    return get<AccountControlListResponse>(
      "/api/admin/account-controls",
      requestOptions(options),
    );
  },

  setAccountStatus(
    payload: AccountStatusPayload,
    options: ApiOptions = {},
  ): Promise<AccountControlListResponse["items"][number]> {
    return post<AccountControlListResponse["items"][number]>(
      "/api/admin/account-controls",
      payload,
      requestOptions(options),
    );
  },

  listActions(
    filter: Partial<ActionFilterState> = {},
    options: ApiOptions = {},
  ): Promise<ActionListResponse> {
    return get<ActionListResponse>(
      `/api/admin/actions${buildQuery(actionQuery(filter))}`,
      requestOptions(options),
    );
  },

  listHealth(options: ApiOptions = {}): Promise<HealthListResponse> {
    return get<HealthListResponse>(
      "/api/admin/health",
      requestOptions(options),
    );
  },

  recordHealth(
    payload: HealthMetricsPayload,
    options: ApiOptions = {},
  ): Promise<SystemHealth> {
    return post<SystemHealth>(
      "/api/admin/health",
      payload,
      requestOptions(options),
    );
  },

  stats(options: ApiOptions = {}): Promise<AdminStats> {
    return get<AdminStats>("/api/admin/stats", requestOptions(options));
  },
};
