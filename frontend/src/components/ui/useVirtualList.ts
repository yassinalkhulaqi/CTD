/**
 * Windowing helpers rendering only the visible slice of a long list.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

/** The options accepted by {@link useVirtualList}. */
export interface UseVirtualListOptions<T> {
  /** The full list of items. */
  items: T[];
  /** The height of a row, in pixels. */
  itemHeight: number;
  /** The height of the viewport, in pixels. */
  viewportHeight: number;
  /** The number of rows rendered above and below the viewport. */
  overscan?: number;
}

/** The state returned by {@link useVirtualList}. */
export interface UseVirtualListResult<T> {
  /** The items currently visible. */
  visible: T[];
  /** The total height of the list, in pixels. */
  totalHeight: number;
  /** The offset of the first visible item, in pixels. */
  offsetY: number;
  /** The index of the first visible item. */
  startIndex: number;
  /** The index of the last visible item. */
  endIndex: number;
  /** Attach the scroll listener to the viewport. */
  scrollRef: React.RefObject<HTMLDivElement | null>;
  /** The scroll offset of the viewport. */
  scrollTop: number;
  /** Handle a scroll event manually. */
  onScroll: (event: React.UIEvent<HTMLElement>) => void;
}

/**
 * Return the slice of a long list that is currently visible.
 *
 * @param options - The hook options.
 * @returns The virtualisation state.
 */
export function useVirtualList<T>(options: UseVirtualListOptions<T>): UseVirtualListResult<T> {
  const { items, itemHeight, viewportHeight, overscan = 4 } = options;
  const [scrollTop, setScrollTop] = useState(0);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const totalHeight = items.length * itemHeight;

  const { startIndex, endIndex } = useMemo(() => {
    const first = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
    const visibleCount = Math.ceil(viewportHeight / itemHeight) + overscan * 2;
    const last = Math.min(items.length, first + visibleCount);
    return { startIndex: first, endIndex: last };
  }, [items.length, itemHeight, overscan, scrollTop, viewportHeight]);

  const visible = useMemo(
    () => items.slice(startIndex, endIndex),
    [endIndex, items, startIndex],
  );

  const onScroll = useCallback((event: React.UIEvent<HTMLElement>) => {
    setScrollTop(event.currentTarget.scrollTop);
  }, []);

  useEffect(() => {
    const node = scrollRef.current;
    if (!node) return;
    setScrollTop(node.scrollTop);
  }, []);

  return {
    visible,
    totalHeight,
    offsetY: startIndex * itemHeight,
    startIndex,
    endIndex,
    scrollRef,
    onScroll,
    scrollTop,
  };
}
