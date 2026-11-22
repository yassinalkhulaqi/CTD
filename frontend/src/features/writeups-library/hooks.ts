/** Data loading hooks for the writeups library. */

import { useCallback, useEffect, useState } from "react";
import { getStats, listWriteups } from "./api";
import type { LibraryFilters, WriteupList, WriteupStats } from "./types";

/** Common shape returned by the loading hooks. */
export interface LoadState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * Normalise an unknown thrown value into an error.
 *
 * @param error - The thrown value.
 * @returns An error instance.
 */
function toError(error: unknown): Error {
  return error instanceof Error ? error : new Error(String(error));
}

/**
 * Load a filtered page of the library.
 *
 * @param filters - The active filters.
 * @param page - The zero-based page index.
 * @returns Loading state and a refetch callback.
 */
export function useWriteupLibrary(
  filters: LibraryFilters,
  page: number,
): LoadState<WriteupList> {
  const [data, setData] = useState<WriteupList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [sequence, setSequence] = useState(0);

  const refetch = useCallback(() => setSequence((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setLoading(true);
    setError(null);
    listWriteups(filters, page * 24, 24, controller.signal)
      .then((result) => {
        if (!active) return;
        setData(result);
        setLoading(false);
      })
      .catch((reason: unknown) => {
        if (!active || controller.signal.aborted) return;
        setError(toError(reason));
        setLoading(false);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [filters, page, sequence]);

  return { data, loading, error, refetch };
}

/**
 * Load library wide statistics.
 *
 * @returns Loading state and a refetch callback.
 */
export function useWriteupStats(): LoadState<WriteupStats> {
  const [data, setData] = useState<WriteupStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [sequence, setSequence] = useState(0);

  const refetch = useCallback(() => setSequence((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setLoading(true);
    getStats()
      .then((result) => {
        if (!active) return;
        setData(result);
        setLoading(false);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setError(toError(reason));
        setLoading(false);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [sequence]);

  return { data, loading, error, refetch };
}
