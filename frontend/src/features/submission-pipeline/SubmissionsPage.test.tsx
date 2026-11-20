import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

const { controller } = vi.hoisted(() => ({
  controller: {
    submissions: [
      {
        id: "sub-1",
        challenge_id: "challenge-1",
        member_id: "member-1",
        flag_cipher: "flag{********_use}",
        status: "rejected" as const,
        attempts: 1,
        created_at: "2026-01-01T00:00:00Z",
        completed_at: "2026-01-01T00:00:02Z",
        error: "flag_mismatch",
        accepted: false,
        stage_index: 2,
        is_pending: false,
      },
    ],
    stats: {
      total: 1,
      by_status: { rejected: 1 },
      by_member: [],
      acceptance_rate: 0,
      average_attempts: 1,
      pending: 0,
      retries: 0,
      attempts: 1,
    },
    rules: [],
    challenges: [
      { id: "challenge-1", title: "Nonce Reuse", team_id: "team-1" },
    ],
    members: [
      { id: "member-1", handle: "nyx", display_name: "Nyx", team_id: "team-1" },
    ],
    filters: { status: "all" as const, challenge_id: "", member_id: "" },
    loading: false,
    busy: false,
    error: null as string | null,
    lastSummary: null,
    setFilters: vi.fn(),
    refresh: vi.fn(async () => undefined),
    submitFlag: vi.fn(async () => controller.submissions[0]),
    retry: vi.fn(async () => undefined),
    process: vi.fn(async () => ({}) as never),
    clearError: vi.fn(),
  },
}));

vi.mock("./hooks", () => ({ useSubmissions: () => controller }));

import { SubmissionsPage } from "./SubmissionsPage";

describe("SubmissionsPage", () => {
  it("composes the console, statistics and live log", () => {
    render(<SubmissionsPage />);
    expect(
      screen.getByRole("heading", { name: "Submissions" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Submission console")).toBeInTheDocument();
    expect(screen.getByText("Live submission log")).toBeInTheDocument();
    expect(screen.getAllByText("Nonce Reuse").length).toBeGreaterThan(0);
    expect(screen.getByText("flag_mismatch")).toBeInTheDocument();
  });

  it("requests a retry for a rejected submission", () => {
    render(<SubmissionsPage />);
    const retry = screen.getAllByRole("button", {
      name: "Retry submission",
    })[0];
    expect(retry).toBeEnabled();
    fireEvent.click(retry);
    expect(controller.retry).toHaveBeenCalledWith("sub-1");
  });

  it("submits a flag through the controller", () => {
    render(<SubmissionsPage />);
    fireEvent.change(screen.getByLabelText("Flag"), {
      target: { value: "flag{abc_123}" },
    });
    fireEvent.click(screen.getByRole("button", { name: /submit flag/i }));
    expect(controller.submitFlag).toHaveBeenCalledWith({
      challenge_id: "challenge-1",
      member_id: "member-1",
      flag: "flag{abc_123}",
    });
  });
});
