import { describe, expect, it } from "vitest";
import { plugin } from "./plugin";

describe("achievements plugin", () => {
  it("declares a unique route and group", () => {
    expect(plugin.id).toBe("achievements");
    expect(plugin.path).toBe("/achievements");
    expect(plugin.group).toBe("Progress");
  });

  it("exposes metadata for the module launcher", () => {
    expect(plugin.label).toBe("Achievements");
    expect(plugin.description).toMatch(/badge/i);
  });

  it("provides a renderable root component", () => {
    expect(typeof plugin.component).toBe("function");
  });
});
