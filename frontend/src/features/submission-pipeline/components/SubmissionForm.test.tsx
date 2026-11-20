import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { SubmissionForm } from "./SubmissionForm";
import type { ChallengeOption, MemberOption } from "../types";

const challenges: ChallengeOption[] = [
  { id: "challenge-1", title: "Nonce Reuse", team_id: "team-1" },
  { id: "challenge-2", title: "Heap House", team_id: "team-2" },
];

const members: MemberOption[] = [
  { id: "member-1", handle: "nyx", display_name: "Nyx", team_id: "team-1" },
  {
    id: "member-2",
    handle: "cortex",
    display_name: "Cortex",
    team_id: "team-2",
  },
];

function renderForm(onSubmit = vi.fn(), error: string | null = null) {
  render(
    <SubmissionForm
      challenges={challenges}
      members={members}
      rules={[]}
      error={error}
      onSubmit={onSubmit}
    />,
  );
  return onSubmit;
}

describe("SubmissionForm", () => {
  it("preselects the first challenge and a member of the same team", () => {
    renderForm();
    expect(screen.getByLabelText("Challenge")).toHaveValue("challenge-1");
    expect(screen.getByLabelText("Member")).toHaveValue("member-1");
  });

  it("switches members when the challenge team changes", () => {
    renderForm();
    fireEvent.change(screen.getByLabelText("Challenge"), {
      target: { value: "challenge-2" },
    });
    expect(screen.getByLabelText("Member")).toHaveValue("member-2");
  });

  it("shows an accessible hint and does not submit a malformed flag", () => {
    const onSubmit = renderForm();
    fireEvent.change(screen.getByLabelText("Flag"), {
      target: { value: "garbage" },
    });
    fireEvent.click(screen.getByRole("button", { name: /submit flag/i }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("flag{...}");
  });

  it("submits a normalised flag", () => {
    const onSubmit = renderForm();
    fireEvent.change(screen.getByLabelText("Flag"), {
      target: { value: "  FLAG{NONCE_REUSE}  " },
    });
    fireEvent.click(screen.getByRole("button", { name: /submit flag/i }));
    expect(onSubmit).toHaveBeenCalledWith({
      challenge_id: "challenge-1",
      member_id: "member-1",
      flag: "flag{nonce_reuse}",
    });
    expect(screen.getByLabelText("Flag")).toHaveValue("");
  });

  it("renders an API error as an alert", () => {
    renderForm(vi.fn(), "This flag was already submitted for the challenge");
    expect(screen.getByRole("alert")).toHaveTextContent("already submitted");
  });
});
