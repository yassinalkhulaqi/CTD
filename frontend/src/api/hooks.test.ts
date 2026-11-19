import { describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryCache } from "./cache";
import { useMutation } from "./useMutation";
import { useQuery } from "./useQuery";

describe("useQuery", () => {
  it("fetches and exposes the data", async () => {
    const cache = new QueryCache();
    const fetcher = vi.fn().mockResolvedValue({ id: "team-1" });

    const { result } = renderHook(() =>
      useQuery({ key: "teams", fetcher, cache, staleTime: 60_000 }),
    );

    await waitFor(() => expect(result.current.data).toEqual({ id: "team-1" }));
    expect(result.current.isLoading).toBe(false);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("serves a fresh entry from the cache without refetching", async () => {
    const cache = new QueryCache({ staleTime: 60_000 });
    cache.set("teams", ["cached"]);
    const fetcher = vi.fn().mockResolvedValue(["fresh"]);

    const { result } = renderHook(() =>
      useQuery({ key: "teams", fetcher, cache, staleTime: 60_000 }),
    );

    await waitFor(() => expect(result.current.data).toEqual(["cached"]));
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("exposes the failure of a rejected request", async () => {
    const cache = new QueryCache();
    const fetcher = vi.fn().mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() =>
      useQuery({ key: "teams", fetcher, cache }),
    );

    await waitFor(() => expect(result.current.error).toBeTruthy());
    expect(result.current.data).toBeUndefined();
  });

  it("does not run when the query is disabled", async () => {
    const cache = new QueryCache();
    const fetcher = vi.fn().mockResolvedValue("value");

    renderHook(() =>
      useQuery({ key: "teams", fetcher, cache, enabled: false }),
    );

    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("invalidates the cached entry", async () => {
    const cache = new QueryCache();
    const fetcher = vi.fn().mockResolvedValue("value");

    const { result } = renderHook(() =>
      useQuery({ key: "teams", fetcher, cache }),
    );

    await waitFor(() => expect(result.current.data).toBe("value"));
    act(() => result.current.invalidate());
    expect(cache.get("teams")).toBeUndefined();
  });
});

describe("useMutation", () => {
  it("runs the mutation and exposes the result", async () => {
    const mutationFn = vi.fn().mockResolvedValue("created");

    const { result } = renderHook(() => useMutation({ mutationFn }));

    let returned: string | undefined;
    await act(async () => {
      returned = (await result.current.mutate("input")) as string | undefined;
    });

    expect(returned).toBe("created");
    expect(result.current.data).toBe("created");
    expect(result.current.isPending).toBe(false);
  });

  it("exposes the failure of a rejected mutation", async () => {
    const mutationFn = vi.fn().mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() => useMutation({ mutationFn }));

    await act(async () => {
      await result.current.mutate("input");
    });

    expect(result.current.error).toBeTruthy();
  });

  it("invalidates the configured cache keys", async () => {
    const cache = new QueryCache();
    cache.set("teams", ["stale"]);
    const mutationFn = vi.fn().mockResolvedValue("ok");

    const { result } = renderHook(() =>
      useMutation({ mutationFn, invalidates: ["teams"], cache }),
    );

    await act(async () => {
      await result.current.mutate("input");
    });

    expect(cache.get("teams")).toBeUndefined();
  });

  it("runs the optimistic context before the mutation", async () => {
    const order: string[] = [];
    const mutationFn = vi.fn().mockImplementation(async () => {
      order.push("mutation");
      return "ok";
    });

    const { result } = renderHook(() =>
      useMutation({
        mutationFn,
        onMutate: () => {
          order.push("mutate");
          return "context";
        },
      }),
    );

    await act(async () => {
      await result.current.mutate("input");
    });

    expect(order).toEqual(["mutate", "mutation"]);
  });
});
