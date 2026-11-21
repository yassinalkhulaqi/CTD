import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ContrastChecker } from "./components/ContrastChecker";
import { FocusOrderMap } from "./components/FocusOrderMap";
import { IssueList } from "./components/IssueList";
import { MotionControls } from "./components/MotionControls";
import { ShortcutEditor } from "./components/ShortcutEditor";
import type {
  A11yIssue,
  ContrastAudit,
  FocusOrderEntry,
  Shortcut,
} from "./types";

function audit(): ContrastAudit {
  return {
    pairs: [],
    issues: [],
    failures: 0,
    pass_rate: 1,
    average_ratio: 21,
  };
}

function issue(overrides: Partial<A11yIssue> = {}): A11yIssue {
  return {
    id: "issue-1",
    path: "/dashboard",
    rule_id: "color-contrast",
    severity: "warning",
    description: "Text is too faint.",
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

describe("ContrastChecker", () => {
  it("evaluates a pair and submits the audit payload", async () => {
    const user = userEvent.setup();
    const onAudit = vi.fn().mockResolvedValue(audit());
    render(<ContrastChecker onAudit={onAudit} />);

    await user.clear(screen.getByLabelText("Foreground"));
    await user.type(screen.getByLabelText("Foreground"), "#000000");
    await user.clear(screen.getByLabelText("Background"));
    await user.type(screen.getByLabelText("Background"), "#ffffff");

    expect(screen.getByText("21.00:1")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Audit pair" }));
    await waitFor(() =>
      expect(onAudit).toHaveBeenCalledWith(
        expect.objectContaining({
          foreground: "#000000",
          background: "#ffffff",
        }),
      ),
    );
  });
});

describe("ShortcutEditor", () => {
  it("blocks a shortcut that conflicts with an existing binding", async () => {
    const user = userEvent.setup();
    const onRegister = vi.fn();
    render(<ShortcutEditor shortcuts={[shortcut()]} onRegister={onRegister} />);

    await user.clear(screen.getByLabelText("Keys"));
    await user.type(screen.getByLabelText("Keys"), "ctrl+k");
    await user.click(screen.getByRole("button", { name: "Register shortcut" }));

    const alerts = await screen.findAllByRole("alert");
    expect(
      alerts.some((alert) => alert.textContent?.includes("Conflict")),
    ).toBe(true);
    expect(onRegister).not.toHaveBeenCalled();
  });
});

describe("IssueList", () => {
  it("filters by severity and resolves the visible issue", async () => {
    const user = userEvent.setup();
    const onResolve = vi.fn().mockResolvedValue(issue());
    render(
      <IssueList
        issues={[
          issue({
            severity: "critical",
            description: "Missing label on submit button.",
          }),
          issue({
            id: "issue-2",
            severity: "warning",
            description: "Text is too faint.",
          }),
        ]}
        onResolve={onResolve}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Critical" }));
    expect(
      screen.getByText("Missing label on submit button."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Text is too faint.")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Resolve" }));
    await waitFor(() => expect(onResolve).toHaveBeenCalledWith("issue-1"));
  });
});

describe("FocusOrderMap", () => {
  it("wraps focus from the first stop to the last", async () => {
    const user = userEvent.setup();
    render(<FocusOrderMap entries={[stop("first", 1), stop("second", 2)]} />);

    expect(screen.getByText(/Current stop 1 of 2/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Previous" }));
    expect(screen.getByText(/Current stop 2 of 2/)).toBeInTheDocument();
  });
});

describe("MotionControls", () => {
  it("reports page-scoped preference changes", async () => {
    const user = userEvent.setup();
    const onReducedMotionChange = vi.fn();
    const onHighContrastChange = vi.fn();
    render(
      <MotionControls
        reducedMotion={false}
        highContrast={false}
        onReducedMotionChange={onReducedMotionChange}
        onHighContrastChange={onHighContrastChange}
      />,
    );

    await user.click(screen.getByRole("switch", { name: "Reduce motion" }));
    await user.click(screen.getByRole("switch", { name: "High contrast" }));
    expect(onReducedMotionChange).toHaveBeenCalledWith(true);
    expect(onHighContrastChange).toHaveBeenCalledWith(true);
  });
});
