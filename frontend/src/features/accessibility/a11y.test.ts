import { describe, expect, it } from "vitest";
import {
  canonicalShortcut,
  classifyContrast,
  contrastRatio,
  createFocusTrap,
  displayShortcut,
  evaluateContrast,
  filterIssues,
  findShortcutConflicts,
  moveFocus,
  suggestAriaLabel,
} from "./a11y";
import type { A11yIssue, FocusOrderEntry, Shortcut } from "./types";

function issue(overrides: Partial<A11yIssue> = {}): A11yIssue {
  return {
    id: "issue-1",
    path: "/dashboard",
    rule_id: "color-contrast",
    severity: "warning",
    description: "Text is too faint against the surface.",
    suggestion: "Darken the foreground.",
    detected_at: "2026-05-01T10:00:00Z",
    resolved_at: null,
    is_resolved: false,
    severity_weight: 2,
    ...overrides,
  };
}

function shortcut(overrides: Partial<Shortcut> = {}): Shortcut {
  return {
    id: "shortcut-1",
    keys: "ctrl+k",
    canonical_keys: "ctrl+k",
    display_keys: "Ctrl+K",
    action: "Open command palette",
    scope: "global",
    is_global: true,
    is_chord: false,
    ...overrides,
  };
}

function stop(id: string, order: number): FocusOrderEntry {
  return {
    id,
    label: `Stop ${order}`,
    order,
    aria_label: `Focus stop ${order}`,
  };
}

describe("contrast helpers", () => {
  it("computes the WCAG ratio for black on white", () => {
    expect(contrastRatio("#000000", "#ffffff")).toBe(21);
    expect(classifyContrast(21, false)).toBe("aaa");
  });

  it("applies relaxed thresholds to large text", () => {
    expect(classifyContrast(4.49, false)).toBe("fail");
    expect(classifyContrast(4, true)).toBe("aa");
  });

  it("returns a structured error for an unsupported colour", () => {
    const result = evaluateContrast("chartreuse", "#ffffff", false);
    expect(result.valid).toBe(false);
    expect(result.error).toContain("not a supported colour");
  });
});

describe("shortcut helpers", () => {
  it("canonicalises modifier order and display names", () => {
    expect(canonicalShortcut("shift+ctrl+k")).toBe("ctrl+shift+k");
    expect(displayShortcut("cmd+return")).toBe("Meta+Enter");
  });

  it("flags global and same-scope collisions", () => {
    const global = shortcut();
    const otherGlobal = shortcut({ id: "shortcut-2", action: "Open search" });
    const editor = shortcut({
      id: "shortcut-3",
      scope: "editor",
      action: "Format code",
      is_global: false,
    });
    const otherEditor = shortcut({
      id: "shortcut-4",
      scope: "editor",
      action: "Format selection",
      is_global: false,
    });
    expect(findShortcutConflicts([global, otherGlobal])).toHaveLength(1);
    expect(findShortcutConflicts([editor, otherEditor])).toHaveLength(1);
    expect(findShortcutConflicts([global, otherGlobal])[0].keys).toBe("ctrl+k");
  });
});

describe("focus helpers", () => {
  it("sorts stops by order and wraps in both directions", () => {
    const state = createFocusTrap([stop("second", 2), stop("first", 1)]);
    expect(state.entries.map((entry) => entry.id)).toEqual(["first", "second"]);
    expect(moveFocus(state, "previous").index).toBe(1);
    expect(moveFocus(state, "next", false).index).toBe(1);
  });
});

describe("issue helpers", () => {
  it("filters by severity, resolution and query", () => {
    const issues = [
      issue(),
      issue({ id: "issue-2", severity: "critical" }),
      issue({
        id: "issue-3",
        is_resolved: true,
        resolved_at: "2026-05-02T10:00:00Z",
      }),
    ];
    const visible = filterIssues(issues, {
      severity: "warning",
      includeResolved: false,
      query: "faint",
    });
    expect(visible.map((item) => item.id)).toEqual(["issue-1"]);
  });

  it("upgrades generic control text into a descriptive aria label", () => {
    expect(suggestAriaLabel("Submit", "", "Save")).toBe("Save control");
  });
});
