import { describe, expect, it } from "vitest";
import { discoverPlugins, pluginForPath } from "../plugins";
import { plugin } from "./plugin";

describe("roster plugin", () => {
  it("declares the operations navigation metadata", () => {
    expect(plugin.id).toBe("roster");
    expect(plugin.label).toBe("Roster");
    expect(plugin.path).toBe("/roster");
    expect(plugin.group).toBe("Operations");
    expect(plugin.description.length).toBeGreaterThan(10);
    expect(plugin.component).toBeTypeOf("function");
  });

  it("is discovered and mounted dynamically", () => {
    expect(discoverPlugins().map((item) => item.id)).toContain("roster");
    expect(pluginForPath("/roster")?.id).toBe("roster");
    expect(pluginForPath("/roster/details")?.id).toBe("roster");
  });
});
