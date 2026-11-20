import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { StatusPipeline } from "./StatusPipeline";

describe("StatusPipeline", () => {
  it("renders the three pipeline stages", () => {
    render(<StatusPipeline status="queued" />);
    const stages = within(screen.getByRole("list"));
    expect(stages.getByText("Queued")).toBeInTheDocument();
    expect(stages.getByText("Validating")).toBeInTheDocument();
    expect(stages.getByText("Accepted")).toBeInTheDocument();
    expect(
      screen.getByRole("group", { name: "Submission pipeline: Queued" }),
    ).toBeInTheDocument();
  });

  it("marks the current stage for a validating submission", () => {
    render(<StatusPipeline status="validating" attempts={1} />);
    const current = within(screen.getByRole("list"))
      .getByText("Validating")
      .closest("li");
    expect(current).toHaveAttribute("aria-current", "step");
    expect(screen.getByText("1 attempt")).toBeInTheDocument();
  });

  it("describes a rejected final stage", () => {
    render(<StatusPipeline status="rejected" attempts={2} />);
    expect(
      screen.getByRole("group", { name: "Submission pipeline: Rejected" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/may be retried/i)).toBeInTheDocument();
  });

  it("hides the footer in compact mode", () => {
    render(<StatusPipeline status="accepted" compact />);
    expect(
      screen.queryByText(/matched the seeded challenge answer/i),
    ).not.toBeInTheDocument();
  });
});
