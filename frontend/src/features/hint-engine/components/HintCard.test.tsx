import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { HintCard } from "./HintCard";
import type { HintBudget, HintView } from "../types";

const budget: HintBudget = {
  team_id: "team-1",
  total: 600,
  spent: 0,
  remaining: 600,
  reset_at: "2026-01-08T00:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
  utilization: 0,
  is_exhausted: false,
};

function hint(overrides: Partial<HintView> = {}): HintView {
  return {
    hint_id: "hint-1",
    challenge_id: "challenge-1",
    tier: 2,
    title: "Inspect the token",
    content: "ABCD******************",
    cost: 50,
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
    ...overrides,
  };
}

describe("HintCard", () => {
  it("renders the tier, price and blurred teaser for a locked hint", () => {
    const view = hint({
      state: "locked",
      eligible: false,
      badge_label: "Locked",
    });
    render(<HintCard hint={view} budget={budget} />);
    expect(screen.getByRole("article", { name: /Tier 2/ })).toBeInTheDocument();
    expect(screen.getByText("ABCD******************")).toBeInTheDocument();
    expect(document.querySelector('[data-state="locked"]')).not.toBeNull();
    expect(
      screen.getByRole("button", { name: /Unlock tier 2/ }),
    ).toBeDisabled();
    expect(screen.getByText("50 credits")).toBeInTheDocument();
  });

  it("reports unlock intent with the originating element", () => {
    const onUnlock = vi.fn();
    render(<HintCard hint={hint()} budget={budget} onUnlock={onUnlock} />);
    const button = screen.getByRole("button", { name: /Unlock tier 2/ });
    expect(button).toBeEnabled();
    fireEvent.click(button);
    expect(onUnlock).toHaveBeenCalledTimes(1);
    expect(onUnlock.mock.calls[0][0].hint_id).toBe("hint-1");
    expect(onUnlock.mock.calls[0][1]).toBe(button);
  });

  it("hides the unlock action after a reveal", () => {
    const view = hint({
      state: "unlocked",
      unlocked: true,
      eligible: false,
      badge_label: "Revealed",
      content: "The full answer",
    });
    render(<HintCard hint={view} budget={budget} />);
    expect(screen.getByText("The full answer")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Unlock tier/ })).toBeNull();
    expect(screen.getAllByText("Revealed").length).toBeGreaterThan(0);
  });
});
