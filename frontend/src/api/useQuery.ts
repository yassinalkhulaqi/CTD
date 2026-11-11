/**
 * `useQuery` — a declarative data fetching hook with caching, polling and
 * stale-while-revalidate semantics.
 */

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { queryCache, type CacheSnapshot, type QueryCache } from "./cache";
import { toApiError } from "./client";

/** Options accepted by {@link useQuery}. */
export interface UseQueryOptions<T> {
  /** The cache key; pass `null` to disable the query entirely. */
  key: string | null;
  /** The function performing the request. */
  fetcher: (signal: AbortSignal) => Promise<T>;
  /** The time after which the data is considered stale, in milliseconds. */
  staleTime?: number;
  /** The polling interval in milliseconds; `0` disables polling. */
  refetchInterval?: number;
  /** Whether the query should run automatically. */
  enabled?: boolean;
  /** The cache instance used to store the result. */
  cache?: QueryCache;
  /** Called after every successful fetch. */
  onSuccess?: (data: T) => void;
  /** Called after every failure. */
  onError?: (error: unknown) => void;
}

/** The value returned by {@link useQuery}. */
export interface UseQueryResult<T> {
  /** The last known value of the query. */
  data: T | undefined;
  /** The last failure of the query. */
  error: unknown;
  /** Whether the first load is in progress. */
  isLoading: boolean;
  /** Whether a request is currently in flight. */
  isFetching: boolean;
  /** Whether the cached value is considered fresh. */
  isFresh: boolean;
  /** Trigger a manual refetch. */
  refetch: () => Promise<T | undefined>;
  /** Remove the cached value and force the next read to refetch. */
  invalidate: () => void;
}

const EMPTY_SNAPSHOT: CacheSnapshot<never> = {
  data: undefined,
  error: undefined,
  updatedAt: 0,
  erroredAt: 0,
};

/**
 * Subscribe to a cached value.
 *
 * @param cache - The cache instance.
 * @param key - The cache key.
 * @returns The subscribed snapshot.
 */
function useCacheSnapshot<T>(cache: QueryCache, key: string): CacheSnapshot<T> {
  const subscribe = useCallback(
    (listener: () => void) => cache.subscribe(key, listener),
    [cache, key],
  );

  const getSnapshot = useCallback((): CacheSnapshot<T> => {
    const entry = cache.get<T>(key);
    return entry?.snapshot ?? EMPTY_SNAPSHOT;
  }, [cache, key]);

  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

/**
 * Fetch and cache a remote resource.
 *
 * @param options - The hook options.
 * @returns The query state.
 */
export function useQuery<T>(options: UseQueryOptions<T>): UseQueryResult<T> {
  const cache = options.cache ?? queryCache;
  const {
    key,
    fetcher,
    staleTime = 15_000,
    refetchInterval = 0,
    enabled = true,
    onSuccess,
    onError,
  } = options;

  const snapshot = useCacheSnapshot<T>(cache, key ?? "__disabled__");
  const [isFetching, setIsFetching] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);
  const callbacks = useRef({ onSuccess, onError });
  callbacks.current = { onSuccess, onError };

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      controllerRef.current?.abort();
    };
  }, []);

  const execute = useCallback(async (): Promise<T | undefined> => {
    if (!key || !enabled) return undefined;

    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setIsFetching(true);
    try {
      const data = await fetcher(controller.signal);
      if (controller.signal.aborted) return undefined;
      cache.set(key, data);
      cache.notify(key);
      callbacks.current.onSuccess?.(data);
      return data;
    } catch (error) {
      if (controller.signal.aborted) return undefined;
      const normalised = toApiError(error);
      cache.setError(key, normalised);
      cache.notify(key);
      callbacks.current.onError?.(normalised);
      return undefined;
    } finally {
      if (mountedRef.current && controllerRef.current === controller) {
        setIsFetching(false);
      }
    }
  }, [cache, enabled, fetcher, key]);

  useEffect(() => {
    if (!key || !enabled) return;

    const entry = cache.get(key);
    const isFresh = entry !== undefined && Date.now() - entry.updatedAt < staleTime;

    if (isFresh) return;

    void execute();
  }, [cache, enabled, execute, key, staleTime]);

  useEffect(() => {
    if (!key || !enabled || refetchInterval <= 0) return;
    const timer = window.setInterval(() => {
      void execute();
    }, refetchInterval);
    return () => window.clearInterval(timer);
  }, [enabled, execute, key, refetchInterval]);

  const refetch = useCallback(async () => {
    if (!key) return undefined;
    return execute();
  }, [execute, key]);

  const invalidate = useCallback(() => {
    if (!key) return;
    cache.invalidate(key);
    cache.notify(key);
  }, [cache, key]);

  const isLoading = snapshot.data === undefined && isFetching;

  return {
    data: snapshot.data,
    error: snapshot.error,
    isLoading,
    isFetching,
    isFresh: snapshot.updatedAt > 0 && Date.now() - snapshot.updatedAt < staleTime,
    refetch,
    invalidate,
  };
}

/**
 * Build a fetcher that calls the given endpoint function.
 *
 * @param loader - The endpoint function.
 * @returns A fetcher compatible with {@link useQuery}.
 */
export function fetcherFrom<T>(
  loader: (signal: AbortSignal) => Promise<T>,
): (signal: AbortSignal) => Promise<T> {
  return loader;
}
