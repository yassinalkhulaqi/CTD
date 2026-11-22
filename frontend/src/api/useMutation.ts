/**
 * `useMutation` — a data mutation hook with optimistic updates, automatic
 * rollback and cache invalidation.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { queryCache, type QueryCache } from "./cache";
import { toApiError } from "./client";

/** Options accepted by {@link useMutation}. */
export interface UseMutationOptions<TInput, TResult, TContext = unknown> {
  /** The mutation function. */
  mutationFn: (input: TInput) => Promise<TResult>;
  /**
   * Called before the mutation runs. The returned context is handed back to
   * the rollback handler when the mutation fails.
   */
  onMutate?: (input: TInput) => TContext | Promise<TContext>;
  /** Called after the mutation succeeds. */
  onSuccess?: (
    result: TResult,
    input: TInput,
    context: TContext | undefined,
  ) => void;
  /** Called after the mutation fails. */
  onError?: (
    error: unknown,
    input: TInput,
    context: TContext | undefined,
  ) => void;
  /** Called after the mutation settles, regardless of the outcome. */
  onSettled?: (
    result: TResult | undefined,
    error: unknown,
    input: TInput,
  ) => void;
  /** Cache keys invalidated once the mutation settles. */
  invalidates?: string[];
  /** Cache key prefixes invalidated once the mutation settles. */
  invalidatesPrefixes?: string[];
  /** The cache instance used for the invalidation. */
  cache?: QueryCache;
}

/** The value returned by {@link useMutation}. */
export interface UseMutationResult<TInput, TResult> {
  /** Run the mutation. */
  mutate: (input: TInput) => Promise<TResult | undefined>;
  /** Whether a mutation is currently running. */
  isPending: boolean;
  /** The last failure of the mutation. */
  error: unknown;
  /** The result of the last successful mutation. */
  data: TResult | undefined;
  /** Clear the error and the result. */
  reset: () => void;
}

/**
 * Run a mutation with optimistic updates and rollback.
 *
 * @param options - The hook options.
 * @returns The mutation state.
 */
export function useMutation<TInput, TResult, TContext = unknown>(
  options: UseMutationOptions<TInput, TResult, TContext>,
): UseMutationResult<TInput, TResult> {
  const cache = options.cache ?? queryCache;
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [data, setData] = useState<TResult | undefined>(undefined);
  const mountedRef = useRef(true);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const invalidate = useCallback(() => {
    const current = optionsRef.current;
    for (const key of current.invalidates ?? []) {
      cache.invalidate(key);
      cache.notify(key);
    }
    for (const prefix of current.invalidatesPrefixes ?? []) {
      const removed = cache.invalidatePrefix(prefix);
      if (removed > 0) {
        for (const key of cache.keys()) {
          if (key.startsWith(prefix)) cache.notify(key);
        }
      }
    }
  }, [cache]);

  const mutate = useCallback(
    async (input: TInput): Promise<TResult | undefined> => {
      const current = optionsRef.current;
      setIsPending(true);
      setError(null);

      let context: TContext | undefined;
      let result: TResult | undefined;
      let failure: unknown;

      try {
        context = await current.onMutate?.(input);
        result = await current.mutationFn(input);
        if (mountedRef.current) {
          setData(result);
          setError(null);
        }
        current.onSuccess?.(result, input, context);
      } catch (caught) {
        failure = toApiError(caught);
        if (mountedRef.current) setError(failure);
        current.onError?.(failure, input, context);
      } finally {
        if (mountedRef.current) setIsPending(false);
        current.onSettled?.(result, failure, input);
        invalidate();
      }

      return result;
    },
    [invalidate],
  );

  const reset = useCallback(() => {
    setError(null);
    setData(undefined);
  }, []);

  return { mutate, isPending, error, data, reset };
}
