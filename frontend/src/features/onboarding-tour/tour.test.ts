import { describe, expect, it } from "vitest";
import {
  checklistSummary,
  completionPercent,
  indexOfStep,
  isResolved,
  nextStep,
  orderedSteps,
  resumeMessage,
  stateLabel,
  stateTone,
  stepPosition,
  tourKeyboardAction,
  buildTourFrame,
} from "./tour";
import type { Checklist, OnboardingStep, StepState } from "./types";

function makeStep(
  id: string,
  order: number,
  state: StepState | null = null,
  slug = id,
): OnboardingStep {
  return {
    id,
    slug,
    title: `Step ${order}`,
    description: "Description",
    target: `#${id}`,
    order,
    completion_key: `key.${id}`,
    kind: "guide",
    estimated_seconds: 60,
    required: true,
    hint: "Hint",
    icon: "compass",
    created_at: "2026-01-01T00:00:00Z",
    state,
    is_current: false,
    target_kind: "anchor",
    duration_label: "1 min",
  };
}

describe("completionPercent", () => {
  it("clamps and rounds down", () => {
    expect(completionPercent(0, 0)).toBe(0);
    expect(completionPercent(1, 3)).toBe(33);
    expect(completionPercent(3, 3)).toBe(100);
    expect(completionPercent(7, 3)).toBe(100);
    expect(completionPercent(-1, 3)).toBe(0);
  });
});

describe("step ordering", () => {
  it("sorts by order without mutating the input", () => {
    const input = [makeStep("c", 3), makeStep("a", 1), makeStep("b", 2)];
    expect(orderedSteps(input).map((step) => step.id)).toEqual(["a", "b", "c"]);
    expect(input[0].id).toBe("c");
  });

  it("derives the next unresolved step", () => {
    const steps = [
      makeStep("a", 1, "complete"),
      makeStep("b", 2, "skipped"),
      makeStep("c", 3, "available"),
    ];
    expect(nextStep(steps)?.id).toBe("c");
    expect(isResolved(steps[0])).toBe(true);
    expect(isResolved(steps[2])).toBe(false);
    expect(nextStep([makeStep("x", 1, "complete")])).toBeNull();
  });

  it("finds step indices and builds tour frames", () => {
    const steps = [makeStep("a", 1), makeStep("b", 2), makeStep("c", 3)];
    expect(indexOfStep(steps, "b")).toBe(1);
    expect(buildTourFrame(steps, null)).toBeNull();
    expect(buildTourFrame(steps, "missing")).toBeNull();
    const frame = buildTourFrame(steps, "b");
    expect(frame?.index).toBe(1);
    expect(frame?.total).toBe(3);
    expect(frame?.isFirst).toBe(false);
    expect(frame?.isLast).toBe(false);
    expect(buildTourFrame(steps, "c")?.isLast).toBe(true);
  });
});

describe("state presentation", () => {
  it("maps states to labels and tones", () => {
    expect(stateLabel(null)).toBe("Pending");
    expect(stateLabel("complete")).toBe("Completed");
    expect(stateLabel("skipped")).toBe("Skipped");
    expect(stateTone("active")).toBe("accent");
    expect(stateTone("locked")).toBe("neutral");
    expect(stateTone("complete")).toBe("success");
    expect(stateTone(null)).toBe("neutral");
  });

  it("formats positions and keyboard actions", () => {
    expect(stepPosition(0, 7)).toBe("Step 1 of 7");
    expect(stepPosition(-1, 0)).toBe("Step 1 of 0");
    expect(tourKeyboardAction("ArrowRight")).toBe("next");
    expect(tourKeyboardAction("Enter")).toBe("next");
    expect(tourKeyboardAction("ArrowLeft")).toBe("previous");
    expect(tourKeyboardAction("Escape")).toBe("close");
    expect(tourKeyboardAction("a")).toBeNull();
  });
});

describe("checklist and resume helpers", () => {
  const checklist: Checklist = {
    user_id: "demo-user",
    items: [
      {
        id: "a",
        label: "One",
        detail: "",
        target: "",
        done: true,
        status: "Done",
      },
      {
        id: "b",
        label: "Two",
        detail: "",
        target: "",
        done: false,
        status: "To do",
      },
    ],
    completed: 1,
    total: 2,
    percent: 50,
    updated_at: "2026-01-01T00:00:00Z",
  };

  it("summarises checklist items", () => {
    expect(checklistSummary(checklist.items)).toEqual({
      completed: 1,
      total: 2,
      percent: 50,
    });
    expect(checklistSummary([]).percent).toBe(0);
  });

  it("builds contextual resume messages", () => {
    expect(resumeMessage(checklist, 50)).toContain("1 checklist item left");
    expect(resumeMessage(null, 0)).toContain("progress will appear");
    expect(resumeMessage(checklist, 100)).toContain("Everything is ready");
  });
});
