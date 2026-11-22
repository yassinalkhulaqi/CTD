import { describe, expect, it } from "vitest";
import { discoverPlugins, pluginForPath } from "../plugins";
import { plugin } from "./plugin";

describe("accessibility plugin", () => {
  it("declares the settings plugin metadata", () => {
    expect(plugin.id).toBe("accessibility");
    expect(plugin.label).toBe("Accessibility");
    expect(plugin.path).toBe("/accessibility");
    expect(plugin.group).toBe("Settings");
    expect(plugin.component).toBeTypeOf("function");
  });

  it("is discovered and routed by the dynamic registry", () => {
    expect(discoverPlugins().map((item) => item.id)).toContain("accessibility");
    expect(pluginForPath("/accessibility")?.id).toBe("accessibility");
  });
});
