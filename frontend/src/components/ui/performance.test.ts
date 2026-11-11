import { describe, expect, it } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useVirtualList } from "./useVirtualList";
import { useDebounced, usePrevious, useStableValue } from "./memoization";

describe("useVirtualList", () => {
  it("renders only the visible slice", () => {
    const items = Array.from({ length: 1000 }, (_, index) => index);
    const { result } = renderHook(() =>
      useVirtualList({ items, itemHeight: 40, viewportHeight: 400, overscan: 2 }),
    );

    expect(result.current.visible.length).toBeLessThan(items.length);
    expect(result.current.startIndex).toBe(0);
    expect(result.current.totalHeight).toBe(40_000);
  });

  it("moves the window when the viewport scrolls", () => {
    const items = Array.from({ length: 1000 }, (_, index) => index);
    const { result } = renderHook(() =>
      useVirtualList({ items, itemHeight: 40, viewportHeight: 400, overscan: 2 }),
    );

    act(() => {
      result.current.onScroll({
        currentTarget: { scrollTop: 4000 },
      } as unknown as React.UIEvent<HTMLElement>);
    });

    expect(result.current.startIndex).toBeGreaterThan(90);
    expect(result.current.offsetY).toBe(result.current.startIndex * 40);
  });

  it("keeps the visible items in sync with the source", () => {
    const items = Array.from({ length: 50 }, (_, index) => index);
    const { result } = renderHook(() =>
      useVirtualList({ items, itemHeight: 30, viewportHeight: 300 }),
    );

    expect(result.current.visible[0]).toBe(0);
    expect(result.current.endIndex).toBeLessThanOrEqual(50);
  });
});

describe("memoization helpers", () => {
  it("keeps the identity of a stable value", () => {
    const stable = { a: 1 };
    const { result, rerender } = renderHook(({ value }) => useStableValue(value), {
      initialProps: { value: stable },
    });
    const first = result.current;
    rerender({ value: stable });
    expect(result.current).toBe(first);
  });

  it("replaces the value when the reference changes", () => {
    const { result, rerender } = renderHook(({ value }) => useStableValue(value), {
      initialProps: { value: { a: 1 } },
    });
    const first = result.current;
    rerender({ value: { a: 2 } });
    expect(result.current).not.toBe(first);
  });

  it("debounces a value", async () => {
    const { result, rerender } = renderHook(({ value }) => useDebounced(value, 10), {
      initialProps: { value: "a" },
    });
    rerender({ value: "b" });
    expect(result.current).toBe("a");
    await new Promise((resolve) => setTimeout(resolve, 30));
    expect(result.current).toBe("b");
  });

  it("exposes the previous value", () => {
    const { result, rerender } = renderHook(({ value }) => usePrevious(value), {
      initialProps: { value: 1 },
    });
    rerender({ value: 2 });
    expect(result.current).toBe(1);
  });
});
