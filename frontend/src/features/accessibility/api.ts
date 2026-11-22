import {
  buildQuery,
  del,
  get,
  post,
  type RequestOptions,
} from "../../api/client";
import type {
  A11yIssue,
  AccessibilityStats,
  AriaSuggestionPayload,
  ContrastAudit,
  ContrastAuditPayload,
  FocusOrderCreatePayload,
  FocusOrderEntry,
  FocusTrapSnapshot,
  IssueCreatePayload,
  Shortcut,
  ShortcutConflict,
  ShortcutCreatePayload,
  Severity,
} from "./types";

const BASE_PATH = "/api/accessibility";

export interface IssueQuery {
  [key: string]: string | number | boolean | null | undefined;
  path?: string;
  severity?: Severity;
  resolved?: boolean;
  limit?: number;
}

export interface AccessibilityApi {
  listIssues(
    query?: IssueQuery,
    options?: RequestOptions,
  ): Promise<A11yIssue[]>;
  createIssue(
    payload: IssueCreatePayload,
    options?: RequestOptions,
  ): Promise<A11yIssue>;
  resolveIssue(issueId: string, options?: RequestOptions): Promise<A11yIssue>;
  listShortcuts(scope?: string, options?: RequestOptions): Promise<Shortcut[]>;
  registerShortcut(
    payload: ShortcutCreatePayload,
    options?: RequestOptions,
  ): Promise<Shortcut>;
  deleteShortcut(shortcutId: string, options?: RequestOptions): Promise<void>;
  shortcutConflicts(options?: RequestOptions): Promise<ShortcutConflict[]>;
  auditContrast(
    payload: ContrastAuditPayload,
    options?: RequestOptions,
  ): Promise<ContrastAudit>;
  listFocusEntries(options?: RequestOptions): Promise<FocusOrderEntry[]>;
  addFocusEntry(
    payload: FocusOrderCreatePayload,
    options?: RequestOptions,
  ): Promise<FocusOrderEntry>;
  reorderFocusEntries(
    ids: string[],
    options?: RequestOptions,
  ): Promise<FocusOrderEntry[]>;
  getFocusTrap(
    index?: number,
    options?: RequestOptions,
  ): Promise<FocusTrapSnapshot>;
  suggestAriaLabel(
    payload: AriaSuggestionPayload,
    options?: RequestOptions,
  ): Promise<{ suggestion: string }>;
  getStats(options?: RequestOptions): Promise<AccessibilityStats>;
}

export const accessibilityApi: AccessibilityApi = {
  listIssues(query, options) {
    return get<A11yIssue[]>(`${BASE_PATH}/issues${buildQuery(query)}`, options);
  },

  createIssue(payload, options) {
    return post<A11yIssue>(`${BASE_PATH}/issues`, payload, options);
  },

  resolveIssue(issueId, options) {
    return post<A11yIssue>(
      `${BASE_PATH}/issues/${encodeURIComponent(issueId)}/resolve`,
      undefined,
      options,
    );
  },

  listShortcuts(scope, options) {
    return get<Shortcut[]>(
      `${BASE_PATH}/shortcuts${buildQuery({ scope })}`,
      options,
    );
  },

  registerShortcut(payload, options) {
    return post<Shortcut>(`${BASE_PATH}/shortcuts`, payload, options);
  },

  deleteShortcut(shortcutId, options) {
    return del<void>(
      `${BASE_PATH}/shortcuts/${encodeURIComponent(shortcutId)}`,
      options,
    );
  },

  shortcutConflicts(options) {
    return get<ShortcutConflict[]>(`${BASE_PATH}/shortcuts/conflicts`, options);
  },

  auditContrast(payload, options) {
    return post<ContrastAudit>(`${BASE_PATH}/contrast`, payload, options);
  },

  listFocusEntries(options) {
    return get<FocusOrderEntry[]>(`${BASE_PATH}/focus-orders`, options);
  },

  addFocusEntry(payload, options) {
    return post<FocusOrderEntry>(`${BASE_PATH}/focus-orders`, payload, options);
  },

  reorderFocusEntries(ids, options) {
    return post<FocusOrderEntry[]>(
      `${BASE_PATH}/focus-orders/reorder`,
      { ids },
      options,
    );
  },

  getFocusTrap(index, options) {
    return get<FocusTrapSnapshot>(
      `${BASE_PATH}/focus-trap${buildQuery({ index })}`,
      options,
    );
  },

  suggestAriaLabel(payload, options) {
    return post<{ suggestion: string }>(
      `${BASE_PATH}/aria-suggestions`,
      payload,
      options,
    );
  },

  getStats(options) {
    return get<AccessibilityStats>(`${BASE_PATH}/stats`, options);
  },
};
