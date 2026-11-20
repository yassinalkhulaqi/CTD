import type { OnboardingStep, ProgressSummary } from "./types";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";

const mocks = vi.hoisted(() => ({
  useOnboarding: vi.fn(),
  complete: vi.fn(),
  skip: vi.fn(),
  toggle: vi.fn(),
  reset: vi.fn(),
  refetch: vi.fn(),
}));

vi.mock("./hooks", () => ({
  useOnboarding: () => mocks.useOnboarding(),
  useCompleteStep: () => ({
    mutate: mocks.complete,
    isPending: false,
    error: null,
  }),
  useSkipStep: () => ({ mutate: mocks.skip, isPending: false, error: null }),
  useToggleChecklistItem: () => ({
    mutate: mocks.toggle,
    isPending: false,
    error: null,
  }),
  useResetOnboarding: () => ({
    mutate: mocks.reset,
    isPending: false,
    error: null,
  }),
}));

import OnboardingPage from "./OnboardingPage";

function makeStep(
  id: string,
  order: number,
  title: string,
  state: OnboardingStep["state"],
): OnboardingStep {
  return {
    id,
    slug: id,
    title,
    description: `About ${title}`,
    target: `#${id}`,
    order,
    completion_key: `tour.${id}`,
    kind: "guide",
    estimated_seconds: 60,
    required: true,
    hint: "A hint",
    icon: "compass",
    created_at: "2026-01-01T00:00:00Z",
    state,
    is_current: state === "active",
    target_kind: "anchor",
    duration_label: "1 min",
  };
}

const steps = [
  makeStep("welcome", 1, "Welcome aboard", "complete"),
  makeStep("workspace", 2, "Explore the board", "active"),
  makeStep("flag", 3, "Submit a flag", "available"),
];

const progress: ProgressSummary = {
  user_id: "demo-user",
  status: "in-progress",
  total: 3,
  completed: 1,
  skipped: 0,
  remaining: 2,
  percent: 33,
  checklist_percent: 50,
  steps,
  records: [],
  next_step: steps[1],
  checklist: {
    user_id: "demo-user",
    items: [
      {
        id: "one",
        label: "Read the welcome note",
        detail: "",
        target: "",
        done: true,
        status: "Done",
      },
      {
        id: "two",
        label: "Open the challenge board",
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
  },
  resume: {
    can_resume: true,
    next_step_slug: "workspace",
    percent: 33,
    last_activity_at: null,
    message: "Continue where you left off",
  },
  welcome_note: {
    id: "note-1",
    user_id: "demo-user",
    title: "Keep going",
    body: "You are almost there.",
    tone: "tip",
    word_count: 5,
    reading_seconds: 1,
    created_at: "2026-01-01T00:00:00Z",
  },
};

describe("OnboardingPage", () => {
  beforeEach(() => {
    mocks.useOnboarding.mockReturnValue({
      steps,
      progress,
      isLoading: false,
      error: null,
      refetch: mocks.refetch,
    });
    mocks.complete.mockResolvedValue(undefined);
    mocks.skip.mockResolvedValue(undefined);
    mocks.toggle.mockResolvedValue(undefined);
    mocks.reset.mockResolvedValue(undefined);
  });

  it("renders the wizard, banner, steps and checklist", () => {
    render(<OnboardingPage />);
    expect(screen.getByText("Set up your workspace")).toBeInTheDocument();
    expect(screen.getByText("33%")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Welcome aboard" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Read the welcome note")).toBeInTheDocument();
    expect(screen.getByText("You are almost there.")).toBeInTheDocument();
  });

  it("opens the spotlight at the next step from the resume banner", () => {
    render(<OnboardingPage />);
    fireEvent.click(screen.getByRole("button", { name: /Resume tour/ }));
    const dialog = screen.getByRole("dialog");
    expect(
      within(dialog).getByRole("heading", { name: "Explore the board" }),
    ).toBeInTheDocument();
    expect(within(dialog).getByText("Step 2 of 3")).toBeInTheDocument();
  });

  it("supports keyboard navigation inside the tour", () => {
    render(<OnboardingPage />);
    fireEvent.click(screen.getByRole("button", { name: /Resume tour/ }));
    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(
      within(screen.getByRole("dialog")).getByRole("heading", {
        name: "Submit a flag",
      }),
    ).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("completes and skips a step from its card", () => {
    render(<OnboardingPage />);
    const heading = screen.getByRole("heading", { name: "Explore the board" });
    const card = heading.closest("article");
    if (!card) throw new Error("Step card not found");
    fireEvent.click(
      within(card).getByRole("button", { name: /Mark complete/ }),
    );
    fireEvent.click(within(card).getByRole("button", { name: /Skip/ }));
    expect(mocks.complete).toHaveBeenCalledWith({ stepId: "workspace" });
    expect(mocks.skip).toHaveBeenCalledWith({ stepId: "workspace" });
  });

  it("toggles checklist items and resets progress", async () => {
    render(<OnboardingPage />);
    const boxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    fireEvent.click(boxes[1]);
    await waitFor(() =>
      expect(mocks.toggle).toHaveBeenCalledWith({ itemId: "two", done: true }),
    );
    fireEvent.click(screen.getByRole("button", { name: /Reset progress/ }));
    await waitFor(() => expect(mocks.reset).toHaveBeenCalled());
  });

  it("renders an empty state when no catalogue is available", () => {
    mocks.useOnboarding.mockReturnValue({
      steps: [],
      progress: null,
      isLoading: false,
      error: null,
      refetch: mocks.refetch,
    });
    render(<OnboardingPage />);
    expect(screen.getByText("No tour steps available")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Reload steps/ }));
    expect(mocks.refetch).toHaveBeenCalled();
  });

  it("renders an error state with a retry action", () => {
    mocks.useOnboarding.mockReturnValue({
      steps: [],
      progress: null,
      isLoading: false,
      error: new Error("Service unavailable"),
      refetch: mocks.refetch,
    });
    render(<OnboardingPage />);
    expect(screen.getByText("Service unavailable")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Try again/ }));
    expect(mocks.refetch).toHaveBeenCalled();
  });
});
