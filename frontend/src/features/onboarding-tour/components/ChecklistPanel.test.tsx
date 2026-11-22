import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import {
  ChecklistPanel,
  EmptyState,
  ProgressBanner,
  StepCard,
  WizardStepper,
} from ".";
import type { Checklist, OnboardingStep, StepState } from "../types";

function makeStep(
  id: string,
  order: number,
  state: StepState = "available",
): OnboardingStep {
  return {
    id,
    slug: id,
    title: `Step ${order}`,
    description: `Description ${order}`,
    target: `#${id}`,
    order,
    completion_key: `key.${id}`,
    kind: "guide",
    estimated_seconds: 90,
    required: true,
    hint: "A helpful hint",
    icon: "compass",
    created_at: "2026-01-01T00:00:00Z",
    state,
    is_current: state === "active",
    target_kind: "anchor",
    duration_label: "1 min 30s",
  };
}

const checklist: Checklist = {
  user_id: "alice",
  items: [
    {
      id: "one",
      label: "First task",
      detail: "A detail",
      target: "#one",
      done: false,
      status: "To do",
    },
    {
      id: "two",
      label: "Second task",
      detail: "",
      target: "",
      done: true,
      status: "Done",
    },
  ],
  completed: 1,
  total: 2,
  percent: 50,
  updated_at: "2026-01-01T00:00:00Z",
};

describe("WizardStepper", () => {
  it("renders ordered steps and selects one", () => {
    const onSelect = vi.fn();
    render(
      <WizardStepper
        steps={[makeStep("b", 2), makeStep("a", 1, "active")]}
        activeIndex={0}
        onSelect={onSelect}
      />,
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons[0]).toHaveAttribute("aria-current", "step");
    expect(buttons[0]).toHaveTextContent("Step 1");
    fireEvent.click(buttons[1]);
    expect(onSelect).toHaveBeenCalledWith(1);
  });

  it("disables locked steps", () => {
    render(
      <WizardStepper
        steps={[makeStep("locked", 1, "locked")]}
        activeIndex={-1}
        onSelect={() => undefined}
      />,
    );
    expect(screen.getByRole("button")).toBeDisabled();
    expect(screen.getAllByText(/Locked/).length).toBeGreaterThan(0);
  });
});

describe("StepCard", () => {
  const handlers = {
    onComplete: vi.fn(),
    onSkip: vi.fn(),
    onSpotlight: vi.fn(),
  };

  it("renders metadata and forwards actions", () => {
    const step = makeStep("a", 1, "active");
    render(<StepCard step={step} state="active" isCurrent {...handlers} />);
    expect(screen.getByRole("heading", { name: "Step 1" })).toBeInTheDocument();
    expect(screen.getByText("#a")).toBeInTheDocument();
    expect(screen.getByText("A helpful hint")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Show me/ }));
    fireEvent.click(screen.getByRole("button", { name: /Skip/ }));
    fireEvent.click(screen.getByRole("button", { name: /Mark complete/ }));
    expect(handlers.onSpotlight).toHaveBeenCalledWith(step);
    expect(handlers.onSkip).toHaveBeenCalledWith(step);
    expect(handlers.onComplete).toHaveBeenCalledWith(step);
  });

  it("disables actions for resolved steps", () => {
    render(
      <StepCard
        step={makeStep("a", 1, "complete")}
        state="complete"
        isCurrent={false}
        {...handlers}
      />,
    );
    expect(screen.getByRole("button", { name: /Done/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Skip/ })).toBeDisabled();
    expect(screen.queryByText("optional")).not.toBeInTheDocument();
  });
});

describe("ChecklistPanel", () => {
  it("renders items and toggles them", () => {
    const onToggle = vi.fn();
    render(<ChecklistPanel checklist={checklist} onToggle={onToggle} />);
    expect(screen.getByText("1 of 2 tasks complete")).toBeInTheDocument();
    const boxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    expect(boxes[0].checked).toBe(false);
    expect(boxes[1].checked).toBe(true);
    fireEvent.click(boxes[0]);
    expect(onToggle).toHaveBeenCalledWith("one", true);
  });

  it("shows loading and empty states", () => {
    const { rerender } = render(
      <ChecklistPanel checklist={null} onToggle={() => undefined} loading />,
    );
    expect(
      document.querySelectorAll('[aria-hidden="true"]').length,
    ).toBeGreaterThan(0);
    rerender(
      <ChecklistPanel
        checklist={{
          ...checklist,
          items: [],
          total: 0,
          completed: 0,
          percent: 0,
        }}
        onToggle={() => undefined}
      />,
    );
    expect(screen.getByText("Nothing to tick yet")).toBeInTheDocument();
  });
});

describe("ProgressBanner", () => {
  const handlers = {
    onStart: vi.fn(),
    onResume: vi.fn(),
    onRestart: vi.fn(),
  };

  it("offers resume when progress exists", () => {
    render(
      <ProgressBanner
        percent={45}
        completed={3}
        total={7}
        status="in-progress"
        resume={{
          can_resume: true,
          next_step_slug: "workspace",
          percent: 45,
          last_activity_at: null,
          message: "Continue",
        }}
        checklist={checklist}
        {...handlers}
      />,
    );
    expect(screen.getByText("45%")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Resume tour/ }));
    expect(handlers.onResume).toHaveBeenCalled();
  });

  it("offers a fresh start when there is no progress", () => {
    render(
      <ProgressBanner
        percent={0}
        completed={0}
        total={7}
        status="not-started"
        resume={null}
        checklist={null}
        {...handlers}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Start tour/ }));
    expect(handlers.onStart).toHaveBeenCalled();
    expect(
      screen.getByRole("button", { name: /Reset progress/ }),
    ).toBeDisabled();
  });
});

describe("EmptyState", () => {
  it("renders an illustration, copy and an action", () => {
    const onAction = vi.fn();
    render(
      <EmptyState
        variant="sparkles"
        title="All clear"
        description="Nothing left to do"
        actionLabel="Refresh"
        onAction={onAction}
      />,
    );
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(document.querySelector("svg")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Refresh/ }));
    expect(onAction).toHaveBeenCalled();
  });
});
