import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const { mockCatalog, mockWorkspace } = vi.hoisted(() => ({
  mockCatalog: vi.fn(),
  mockWorkspace: vi.fn(),
}));

vi.mock("./hooks", () => ({
  useHintCatalog: () => mockCatalog(),
  useHintWorkspace: () => mockWorkspace(),
}));

import { HintsPage } from "./HintsPage";
import type { HintView } from "./types";

const hint: HintView = {
  hint_id: "hint-1",
  challenge_id: "challenge-1",
  tier: 1,
  title: "Start with the header",
  content: "Start with the ****",
  cost: 25,
  reveal_after_seconds: 0,
  is_active: true,
  state: "eligible",
  reason: "Ready to unlock",
  remaining_seconds: 0,
  required_tier: null,
  unlocked: false,
  eligible: true,
  badge_label: "Available",
  unlocked_at: null,
  unlocked_by: null,
};

const budget = {
  team_id: "team-1",
  total: 600,
  spent: 0,
  remaining: 600,
  reset_at: "2026-01-08T00:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
  utilization: 0,
  is_exhausted: false,
};

const view = {
  challenge_id: "challenge-1",
  team_id: "team-1",
  hints: [hint],
  budget,
  curve: [
    { tier: 1, cost: 25, cumulative: 25, label: "T1: 25" },
    { tier: 2, cost: 50, cumulative: 75, label: "T2: 50" },
    { tier: 3, cost: 100, cumulative: 175, label: "T3: 100" },
  ],
  unlocked_count: 0,
};

describe("HintsPage", () => {
  beforeEach(() => {
    mockCatalog.mockReturnValue({
      teams: [{ id: "team-1", name: "RedScribe" }],
      challenges: [
        { id: "challenge-1", team_id: "team-1", title: "Nonce Reuse" },
      ],
      members: [{ id: "member-1", team_id: "team-1", display_name: "Nyx" }],
      loading: false,
      error: null,
      reload: vi.fn(),
    });
    mockWorkspace.mockReturnValue({
      view,
      ledger: {
        team_id: "team-1",
        entries: [],
        summary: { by_tier: [], unlock_count: 0 },
      },
      loading: false,
      working: false,
      error: null,
      refresh: vi.fn(),
      unlock: vi.fn().mockResolvedValue(undefined),
      resetBudget: vi.fn().mockResolvedValue(undefined),
    });
  });

  it("renders the selectors, budget, cost curve and ladder", () => {
    render(<HintsPage />);
    expect(
      screen.getByRole("heading", { name: "Tiered hints" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Team")).toHaveValue("team-1");
    expect(screen.getByLabelText("Challenge")).toHaveValue("challenge-1");
    expect(
      screen.getByRole("heading", { name: "Nonce Reuse" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Team budget")).toBeInTheDocument();
    expect(screen.getByText("Cost curve")).toBeInTheDocument();
    expect(screen.getByText("Start with the header")).toBeInTheDocument();
  });

  it("opens the confirmation dialog from a hint card and cancels it", async () => {
    const user = userEvent.setup();
    render(<HintsPage />);
    await user.click(screen.getByRole("button", { name: /Unlock tier 1/ }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(
      screen.getByText(/Unlock “Start with the header”/),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("shows an empty state when no hints are authored", () => {
    mockWorkspace.mockReturnValue({
      ...mockWorkspace(),
      view: { ...view, hints: [] },
    });
    render(<HintsPage />);
    expect(screen.getByText("No hints authored")).toBeInTheDocument();
  });
});
