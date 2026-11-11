import { describe, expect, it } from "vitest";
import { QueryCache, queryKey, stableStringify } from "./cache";

describe("QueryCache", () => {
  it("stores and returns values", () => {
    const cache = new QueryCache();
    cache.set("teams", [{ id: "a" }]);
    expect(cache.get("teams")?.data).toEqual([{ id: "a" }]);
  });

  it("reports freshness based on the stale time", () => {
    const cache = new QueryCache({ staleTime: 60_000 });
    cache.set("teams", []);
    expect(cache.isFresh("teams")).toBe(true);
    expect(cache.isFresh("missing")).toBe(false);
  });

  it("keeps the previous value when an error is recorded", () => {
    const cache = new QueryCache();
    cache.set("teams", [1]);
    cache.setError("teams", new Error("boom"));
    expect(cache.get("teams")?.data).toEqual([1]);
    expect(cache.get("teams")?.error).toBeInstanceOf(Error);
  });

  it("invalidates a single key", () => {
    const cache = new QueryCache();
    cache.set("teams", []);
    cache.invalidate("teams");
    expect(cache.get("teams")).toBeUndefined();
  });

  it("invalidates every key sharing a prefix", () => {
    const cache = new QueryCache();
    cache.set("teams:a", []);
    cache.set("teams:b", []);
    cache.set("members:a", []);
    expect(cache.invalidatePrefix("teams:")).toBe(2);
    expect(cache.get("members:a")).toBeDefined();
  });

  it("notifies subscribers", () => {
    const cache = new QueryCache();
    let notified = 0;
    cache.subscribe("teams", () => {
      notified += 1;
    });
    cache.notify("teams");
    expect(notified).toBe(1);
  });

  it("prunes the least recently updated entries", () => {
    const cache = new QueryCache({ maxEntries: 2 });
    cache.set("a", 1);
    cache.set("b", 2);
    cache.set("c", 3);
    expect(cache.size).toBeLessThanOrEqual(2);
  });
});

describe("queryKey", () => {
  it("builds a stable key from the parameters", () => {
    expect(queryKey("teams", { b: 2, a: 1 })).toBe(queryKey("teams", { a: 1, b: 2 }));
  });

  it("returns the plain name without parameters", () => {
    expect(queryKey("teams")).toBe("teams");
  });
});

describe("stableStringify", () => {
  it("sorts object keys", () => {
    expect(stableStringify({ b: 1, a: 2 })).toBe('{"a":2,"b":1}');
  });

  it("preserves array order", () => {
    expect(stableStringify([1, 2])).toBe("[1,2]");
  });

  it("handles primitives", () => {
    expect(stableStringify(null)).toBe("null");
    expect(stableStringify(5)).toBe("5");
  });
});
