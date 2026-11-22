import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { UnlockDialog } from "./UnlockDialog";
import type { HintBudget, HintView } from "../types";

const budget: HintBudget = {
  team_id: "team-1",
  total: 600,
  spent: 100,
  remaining: 500,
  reset_at: "2026-01-08T00:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
  utilization: 100 / 600,
  is_exhausted: false,
};

const hint: HintView = {
  hint_id: "hint-1",
  challenge_id: "challenge-1",
  tier: 3,
  title: "Final nudge",
  content: "Final ****",
  cost: 100,
  reveal_after_seconds: 0,
  is_active: true,
  state: "eligible",
  reason: "Ready",
  remaining_seconds: 0,
  required_tier: null,
  unlocked: false,
  eligible: true,
  badge_label: "Available",
  unlocked_at: null,
  unlocked_by: null,
};

function Harness({
  onConfirm,
  onClose,
}: {
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <>
      <button type="button">Open hint</button>
      <UnlockDialog
        open
        hint={hint}
        budget={budget}
        onConfirm={onConfirm}
        onClose={onClose}
      />
    </>
  );
}

describe("UnlockDialog", () => {
  it("shows the price and the budget remaining after the unlock", () => {
    render(<Harness onConfirm={() => undefined} onClose={() => undefined} />);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByText("Tier 3 hint")).toBeInTheDocument();
    expect(screen.getByText("100 credits")).toBeInTheDocument();
    expect(screen.getByText("400 credits")).toBeInTheDocument();
  });

  it("confirms an unlock when the primary action is activated", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<Harness onConfirm={onConfirm} onClose={() => undefined} />);
    await user.click(screen.getByRole("button", { name: /Unlock hint/i }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("closes on Escape and returns focus to the trigger", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const { rerender } = render(
      <>
        <button type="button">Open hint</button>
        <UnlockDialog
          open={false}
          hint={hint}
          budget={budget}
          onConfirm={() => undefined}
          onClose={onClose}
        />
      </>,
    );
    const trigger = screen.getByRole("button", { name: "Open hint" });
    trigger.focus();
    rerender(
      <>
        <button type="button">Open hint</button>
        <UnlockDialog
          open
          hint={hint}
          budget={budget}
          onConfirm={() => undefined}
          onClose={onClose}
        />
      </>,
    );
    expect(screen.getByRole("button", { name: "Cancel" })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
    rerender(
      <>
        <button type="button">Open hint</button>
        <UnlockDialog
          open={false}
          hint={hint}
          budget={budget}
          onConfirm={() => undefined}
          onClose={onClose}
        />
      </>,
    );
    expect(trigger).toHaveFocus();
  });
});
