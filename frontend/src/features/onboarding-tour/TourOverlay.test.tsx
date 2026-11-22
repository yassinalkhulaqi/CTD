import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { TourOverlay } from "./components/TourOverlay";
import type { OnboardingStep } from "./types";

const step: OnboardingStep = {
  id: "step-workspace",
  slug: "workspace",
  title: "Explore the board",
  description: "A guided description",
  target: '[data-tour="challenge-board"]',
  order: 3,
  completion_key: "tour.workspace",
  kind: "guide",
  estimated_seconds: 120,
  required: true,
  hint: "Look at a challenge card",
  icon: "layout",
  created_at: "2026-01-01T00:00:00Z",
  state: "active",
  is_current: true,
  target_kind: "selector",
  duration_label: "2 min",
};

function renderOverlay(
  overrides: Partial<ComponentProps<typeof TourOverlay>> = {},
) {
  const handlers = {
    onNext: vi.fn(),
    onBack: vi.fn(),
    onClose: vi.fn(),
  };
  const view = render(
    <TourOverlay
      step={step}
      index={2}
      total={7}
      isFirst={false}
      isLast={false}
      {...handlers}
      {...overrides}
    />,
  );
  return { ...handlers, ...view };
}

describe("TourOverlay", () => {
  it("renders an accessible dialog with step details", () => {
    renderOverlay();
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(
      screen.getByRole("heading", { name: "Explore the board" }),
    ).toBeInTheDocument();
    expect(screen.getByText("A guided description")).toBeInTheDocument();
    expect(screen.getAllByText(step.target).length).toBeGreaterThan(0);
    expect(screen.getByText("Step 3 of 7")).toBeInTheDocument();
  });

  it("focuses the close control for keyboard users", () => {
    renderOverlay();
    expect(
      screen.getByRole("button", { name: "Close guided tour" }),
    ).toHaveFocus();
  });

  it("maps keyboard shortcuts to tour actions", () => {
    const handlers = renderOverlay();
    fireEvent.keyDown(window, { key: "ArrowRight" });
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    fireEvent.keyDown(window, { key: "Escape" });
    fireEvent.keyDown(window, { key: "q" });
    expect(handlers.onNext).toHaveBeenCalledTimes(1);
    expect(handlers.onBack).toHaveBeenCalledTimes(1);
    expect(handlers.onClose).toHaveBeenCalledTimes(1);
  });

  it("disables back on the first step and relabels finish on the last", () => {
    renderOverlay({ isFirst: true, isLast: true, index: 6 });
    expect(screen.getByRole("button", { name: /Back/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Finish/ })).toBeInTheDocument();
  });

  it("advances through buttons and closes on backdrop click", () => {
    const handlers = renderOverlay();
    fireEvent.click(screen.getByRole("button", { name: /Next step/ }));
    expect(handlers.onNext).toHaveBeenCalledTimes(1);
    const backdrop = screen.getByRole("dialog").parentElement;
    if (backdrop) fireEvent.mouseDown(backdrop);
    expect(handlers.onClose).toHaveBeenCalledTimes(1);
  });
});
