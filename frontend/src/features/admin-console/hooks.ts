import { useCallback, useEffect, useRef, useState } from "react";
import { toApiError } from "../../api/client";
import { adminApi } from "./api";
import {
  DEFAULT_CASE_FILTER,
  type AccountControl,
  type AccountStatusPayload,
  type AdminConsoleData,
  type CaseFilterState,
  type CreateCasePayload,
  type HealthMetricsPayload,
  type ModerationCase,
  type SystemHealth,
} from "./types";

export type CaseMutation = "assign" | "resolve" | "dismiss";

export interface UseAdminConsoleResult {
  data: AdminConsoleData | null;
  loading: boolean;
  busy: string | null;
  error: string | null;
  refresh: () => Promise<void>;
  loadCases: (filter: CaseFilterState) => Promise<void>;
  updateCase: (
    caseId: string,
    action: CaseMutation,
    value: string,
  ) => Promise<boolean>;
  openCase: (payload: CreateCasePayload) => Promise<boolean>;
  changeAccountStatus: (payload: AccountStatusPayload) => Promise<boolean>;
  recordHealth: (payload: HealthMetricsPayload) => Promise<boolean>;
  clearError: () => void;
}

function replaceCase(
  items: ModerationCase[],
  updated: ModerationCase,
): ModerationCase[] {
  return items.map((item) => (item.id === updated.id ? updated : item));
}

export function useAdminConsole(): UseAdminConsoleResult {
  const [data, setData] = useState<AdminConsoleData | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const caseFilterRef = useRef<CaseFilterState>(DEFAULT_CASE_FILTER);

  const refresh = useCallback(async (signal?: AbortSignal): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const [cases, accounts, actions, health, stats] = await Promise.all([
        adminApi.listCases(caseFilterRef.current, { signal }),
        adminApi.listAccounts({ signal }),
        adminApi.listActions({}, { signal }),
        adminApi.listHealth({ signal }),
        adminApi.stats({ signal }),
      ]);
      setData({ cases, accounts, actions, health, stats });
    } catch (caught) {
      if (signal?.aborted) return;
      setError(toApiError(caught).message);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void refresh(controller.signal);
    return () => controller.abort();
  }, [refresh]);

  const loadCases = useCallback(
    async (filter: CaseFilterState): Promise<void> => {
      caseFilterRef.current = filter;
      try {
        const cases = await adminApi.listCases(filter);
        setData((previous) => (previous ? { ...previous, cases } : previous));
      } catch (caught) {
        setError(toApiError(caught).message);
      }
    },
    [],
  );

  const runMutation = useCallback(
    async (key: string, task: () => Promise<void>): Promise<boolean> => {
      setBusy(key);
      setError(null);
      try {
        await task();
        return true;
      } catch (caught) {
        setError(toApiError(caught).message);
        return false;
      } finally {
        setBusy(null);
      }
    },
    [],
  );

  const updateCase = useCallback(
    async (
      caseId: string,
      action: CaseMutation,
      value: string,
    ): Promise<boolean> => {
      return runMutation(`case:${caseId}:${action}`, async () => {
        let updated: ModerationCase;
        if (action === "assign") {
          updated = await adminApi.assignCase(caseId, value);
        } else if (action === "resolve") {
          updated = await adminApi.resolveCase(caseId, value);
        } else {
          updated = await adminApi.dismissCase(caseId, value);
        }
        setData((previous) =>
          previous
            ? {
                ...previous,
                cases: {
                  ...previous.cases,
                  items: replaceCase(previous.cases.items, updated),
                },
              }
            : previous,
        );
        await refresh();
      });
    },
    [refresh, runMutation],
  );

  const openCase = useCallback(
    async (payload: CreateCasePayload): Promise<boolean> => {
      return runMutation("case:create", async () => {
        const created = await adminApi.createCase(payload);
        setData((previous) =>
          previous
            ? {
                ...previous,
                cases: {
                  ...previous.cases,
                  total: previous.cases.total + 1,
                  items: [created, ...previous.cases.items].slice(
                    0,
                    previous.cases.limit,
                  ),
                },
              }
            : previous,
        );
        await refresh();
      });
    },
    [refresh, runMutation],
  );

  const changeAccountStatus = useCallback(
    async (payload: AccountStatusPayload): Promise<boolean> => {
      return runMutation(`account:${payload.user_id}`, async () => {
        const updated = await adminApi.setAccountStatus(payload);
        setData((previous) =>
          previous
            ? {
                ...previous,
                accounts: {
                  ...previous.accounts,
                  items: previous.accounts.items.map(
                    (account: AccountControl) =>
                      account.user_id === updated.user_id ? updated : account,
                  ),
                },
              }
            : previous,
        );
        await refresh();
      });
    },
    [refresh, runMutation],
  );

  const recordHealth = useCallback(
    async (payload: HealthMetricsPayload): Promise<boolean> => {
      return runMutation("health:record", async () => {
        const check: SystemHealth = await adminApi.recordHealth(payload);
        setData((previous) =>
          previous
            ? {
                ...previous,
                health: {
                  items: [check, ...previous.health.items].slice(0, 20),
                  latest: check,
                },
              }
            : previous,
        );
        await refresh();
      });
    },
    [refresh, runMutation],
  );

  const clearError = useCallback(() => setError(null), []);

  return {
    data,
    loading,
    busy,
    error,
    refresh,
    loadCases,
    updateCase,
    openCase,
    changeAccountStatus,
    recordHealth,
    clearError,
  };
}
