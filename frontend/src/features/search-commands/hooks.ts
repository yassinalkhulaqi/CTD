/** Data loading and local state hooks for the search workspace. */

import { useCallback, useEffect, useState } from "react";
import { toApiError } from "../../api/client";
import { searchApi } from "./api";
import { buildRecentQueries } from "./searchUtils";
import type { Command, SearchKind, SearchResponse } from "./types";

const RECENT_KEY = "v3.search.recentQueries";
const SEARCH_DEBOUNCE_MS = 180;

/** State returned by the search feed hook. */
export interface SearchFeed {
  results: SearchResponse | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Load search results whenever the query or filters change.
 *
 * @param query - The raw query text.
 * @param kinds - Selected document kinds.
 * @param tags - Selected tag filters.
 * @param limit - Maximum number of results.
 * @returns The response, loading state and a refresh callback.
 */
export function useSearchFeed(
  query: string,
  kinds: SearchKind[],
  tags: string[],
  limit: number,
): SearchFeed {
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  const kindKey = kinds.join(",");
  const tagKey = tags.join(",");

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    const timer = setTimeout(async () => {
      try {
        const payload = await searchApi.search(
          {
            q: query,
            limit,
            kinds: kindKey ? (kindKey.split(",") as SearchKind[]) : undefined,
            tags: tagKey ? tagKey.split(",") : undefined,
          },
          { signal: controller.signal },
        );
        setResponse(payload);
      } catch (cause) {
        if (controller.signal.aborted) return;
        setError(toApiError(cause).message);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [query, kindKey, tagKey, limit, revision]);

  const refresh = useCallback(() => setRevision((value) => value + 1), []);
  return { results: response, loading, error, refresh };
}

/** State returned by the command catalogue hook. */
export interface CommandFeed {
  commands: Command[];
  groups: string[];
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/**
 * Load the command catalogue once and on demand.
 *
 * @returns The commands and their loading state.
 */
export function useCommandsFeed(): CommandFeed {
  const [commands, setCommands] = useState<Command[]>([]);
  const [groups, setGroups] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    searchApi
      .commands("", undefined, { signal: controller.signal })
      .then((payload) => {
        setCommands(payload.commands);
        setGroups(payload.groups);
        setError(null);
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) setError(toApiError(cause).message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [revision]);

  const reload = useCallback(() => setRevision((value) => value + 1), []);
  return { commands, groups, loading, error, reload };
}

/** State returned by the recent query hook. */
export interface RecentQueries {
  queries: string[];
  remember: (query: string) => void;
  clear: () => void;
}

/**
 * Persist the most recent search queries in local storage.
 *
 * @returns The queries and helpers to modify them.
 */
export function useRecentQueries(): RecentQueries {
  const [queries, setQueries] = useState<string[]>(() => {
    try {
      const raw = window.localStorage.getItem(RECENT_KEY);
      const parsed: unknown = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed)
        ? parsed.filter((item): item is string => typeof item === "string")
        : [];
    } catch {
      return [];
    }
  });

  const remember = useCallback((query: string) => {
    setQueries((previous) => {
      const updated = buildRecentQueries(previous, query);
      try {
        window.localStorage.setItem(RECENT_KEY, JSON.stringify(updated));
      } catch {
        return updated;
      }
      return updated;
    });
  }, []);

  const clear = useCallback(() => {
    setQueries([]);
    try {
      window.localStorage.removeItem(RECENT_KEY);
    } catch {
      setQueries([]);
    }
  }, []);

  return { queries, remember, clear };
}
