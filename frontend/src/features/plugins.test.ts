import { describe, expect, it } from "vitest";
import type { FeaturePlugin } from "./plugins";
import {
  discoverPlugins,
  groupPlugins,
  normalizePlugins,
  pluginForPath,
} from "./plugins";

/** Build a plugin declaration for tests. */
function makePlugin(
  id: string,
  overrides: Partial<FeaturePlugin> = {},
): FeaturePlugin {
  return {
    id,
    label: id.toUpperCase(),
    path: `/${id}`,
    description: `${id} module`,
    group: "Workspace",
    component: () => null,
    ...overrides,
  };
}

describe("feature plugin registry", () => {
  it("sorts plugins by identifier", () => {
    const sorted = normalizePlugins([makePlugin("zeta"), makePlugin("alpha")]);
    expect(sorted.map((plugin) => plugin.id)).toEqual(["alpha", "zeta"]);
  });

  it("drops duplicate and empty identifiers", () => {
    const sorted = normalizePlugins([
      makePlugin("alpha"),
      makePlugin("alpha"),
      makePlugin(""),
    ]);
    expect(sorted).toHaveLength(1);
  });

  it("groups plugins by their group name", () => {
    const grouped = groupPlugins([
      makePlugin("alpha", { group: "Analyze" }),
      makePlugin("beta", { group: "Analyze" }),
      makePlugin("gamma", { group: "Modules" }),
    ]);
    expect(grouped.Analyze).toHaveLength(2);
    expect(grouped.Modules).toHaveLength(1);
  });

  it("exposes a stable discovery result", () => {
    const first = discoverPlugins();
    const second = discoverPlugins();
    expect(first.map((plugin) => plugin.id)).toEqual(
      second.map((plugin) => plugin.id),
    );
  });

  it("matches exact and nested paths", () => {
    const found = pluginForPath("/notes/detail");
    if (!found) {
      expect(found).toBeUndefined();
      return;
    }
    expect(found.path).toBe("/notes");
  });
});
