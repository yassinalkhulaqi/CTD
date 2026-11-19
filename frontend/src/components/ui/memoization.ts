/**
 * Memoisation helpers reducing the re-render cost of the dashboard.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

/**
 * Return a stable callback whose identity only changes when its
 * dependencies change.
 *
 * @param callback - The callback to memoise.
 * @param dependencies - The dependencies of the callback.
 * @returns The memoised callback.
 */
export function useStableCallback<TArgs extends unknown[], TResult>(
  callback: (...args: TArgs) => TResult,
  dependencies: unknown[],
): (...args: TArgs) => TResult {
  const ref = useRef(callback);
  ref.current = callback;

  // eslint-disable-next-line react-hooks/exhaustive-deps
  return useCallback((...args: TArgs) => ref.current(...args), dependencies);
}

/**
 * Return a value that only changes when the input really changed.
 *
 * @param value - The value to stabilise.
 * @returns The stabilised value.
 */
export function useStableValue<T>(value: T): T {
  const ref = useRef(value);
  if (!Object.is(ref.current, value)) {
    ref.current = value;
  }
  return ref.current;
}

/**
 * Return a debounced copy of a value.
 *
 * @param value - The value to debounce.
 * @param delay - The debounce delay in milliseconds.
 * @returns The debounced value.
 */
export function useDebounced<T>(value: T, delay = 200): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [delay, value]);

  return debounced;
}

/**
 * Return the result of a factory recomputed only when its inputs change.
 *
 * @param factory - The factory producing the value.
 * @param dependencies - The dependencies of the factory.
 * @returns The memoised value.
 */
export function useFactory<T>(factory: () => T, dependencies: unknown[]): T {
  // eslint-disable-next-line react-hooks/exhaustive-deps
  return useMemo(factory, dependencies);
}

/**
 * Keep the previous value of a changing input.
 *
 * @param value - The current value.
 * @returns The previous value.
 */
export function usePrevious<T>(value: T): T | undefined {
  const ref = useRef<T | undefined>(undefined);
  useEffect(() => {
    ref.current = value;
  }, [value]);
  return ref.current;
}

/**
 * Run a callback when the size of the observed element changes.
 *
 * @param callback - The callback receiving the new size.
 * @returns A ref to attach to the observed element.
 */
export function useElementSize(
  callback: (size: { width: number; height: number }) => void,
): React.RefObject<HTMLDivElement | null> {
  const ref = useRef<HTMLDivElement | null>(null);
  const stable = useStableCallback(callback, []);

  useEffect(() => {
    const node = ref.current;
    if (!node || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      stable({
        width: entry.contentRect.width,
        height: entry.contentRect.height,
      });
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [stable]);

  return ref;
}
