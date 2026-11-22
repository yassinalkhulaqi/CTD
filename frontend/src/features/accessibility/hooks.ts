import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../../api/client";
import { accessibilityApi } from "./api";
import type {
  A11yIssue,
  AccessibilityStats,
  FocusOrderEntry,
  IssueFilters,
  Shortcut,
  Severity,
} from "./types";
import { EMPTY_STATS } from "./types";

export interface AccessibilitySnapshot {
  issues: A11yIssue[];
  shortcuts: Shortcut[];
  focusEntries: FocusOrderEntry[];
  stats: AccessibilityStats;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

export function useAccessibilityData(): AccessibilitySnapshot {
  const [issues, setIssues] = useState<A11yIssue[]>([]);
  const [shortcuts, setShortcuts] = useState<Shortcut[]>([]);
  const [focusEntries, setFocusEntries] = useState<FocusOrderEntry[]>([]);
  const [stats, setStats] = useState<AccessibilityStats>(EMPTY_STATS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const [issueRows, shortcutRows, focusRows, summary] = await Promise.all([
        accessibilityApi.listIssues(undefined, { signal }),
        accessibilityApi.listShortcuts(undefined, { signal }),
        accessibilityApi.listFocusEntries({ signal }),
        accessibilityApi.getStats({ signal }),
      ]);
      setIssues(issueRows);
      setShortcuts(shortcutRows);
      setFocusEntries(focusRows);
      setStats(summary);
    } catch (cause) {
      if (cause instanceof ApiError && cause.code === "aborted") return;
      setError(
        cause instanceof Error
          ? cause.message
          : "Unable to load accessibility data",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const reload = useCallback(() => {
    void load();
  }, [load]);

  return { issues, shortcuts, focusEntries, stats, loading, error, reload };
}

export interface IssueFilterControls {
  filters: IssueFilters;
  setSeverity: (severity: Severity | "all") => void;
  setQuery: (query: string) => void;
  toggleResolved: () => void;
  reset: () => void;
}

export function useIssueFilters(
  initial?: Partial<IssueFilters>,
): IssueFilterControls {
  const [filters, setFilters] = useState<IssueFilters>({
    severity: initial?.severity ?? "all",
    includeResolved: initial?.includeResolved ?? false,
    query: initial?.query ?? "",
  });

  const setSeverity = useCallback((severity: Severity | "all") => {
    setFilters((current) => ({ ...current, severity }));
  }, []);

  const setQuery = useCallback((query: string) => {
    setFilters((current) => ({ ...current, query }));
  }, []);

  const toggleResolved = useCallback(() => {
    setFilters((current) => ({
      ...current,
      includeResolved: !current.includeResolved,
    }));
  }, []);

  const reset = useCallback(() => {
    setFilters({ severity: "all", includeResolved: false, query: "" });
  }, []);

  return { filters, setSeverity, setQuery, toggleResolved, reset };
}
