/** Plugin metadata tests. */

import { describe, expect, it } from "vitest";
import { plugin } from "./plugin";

describe("search plugin", () => {
  it("declares a unique workspace route", () => {
    expect(plugin.id).toBe("search");
    expect(plugin.label).toBe("Search");
    expect(plugin.path).toBe("/search");
    expect(plugin.group).toBe("Workspace");
    expect(plugin.description).toContain("command palette");
  });

  it("contributes a mounted root component", () => {
    expect(typeof plugin.component).toBe("function");
  });
});
