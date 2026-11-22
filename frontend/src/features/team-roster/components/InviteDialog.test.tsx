import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { InviteDialog } from "./InviteDialog";

function renderDialog(
  overrides: Partial<Parameters<typeof InviteDialog>[0]> = {},
) {
  const props = {
    open: true,
    onClose: vi.fn(),
    onInvite: vi.fn(),
    teams: ["team-alpha", "team-beta"],
    busy: false,
    error: null,
    ...overrides,
  };
  render(<InviteDialog {...props} />);
  return props;
}

describe("InviteDialog", () => {
  it("renders the email, team and role fields when open", () => {
    renderDialog();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByLabelText("Email address")).toBeInTheDocument();
    expect(screen.getByLabelText("Team")).toBeInTheDocument();
    expect(screen.getByLabelText("Role")).toBeInTheDocument();
  });

  it("renders nothing when closed", () => {
    renderDialog({ open: false });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("rejects an invalid email without inviting", async () => {
    const user = userEvent.setup();
    const props = renderDialog();
    await user.type(screen.getByLabelText("Email address"), "not-an-email");
    await user.click(screen.getByRole("button", { name: /Send invitation/ }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Enter a valid email address.",
    );
    expect(props.onInvite).not.toHaveBeenCalled();
  });

  it("submits the chosen email, team and role", async () => {
    const user = userEvent.setup();
    const props = renderDialog();
    await user.type(screen.getByLabelText("Email address"), "new@example.com");
    await user.selectOptions(screen.getByLabelText("Team"), "team-beta");
    await user.selectOptions(screen.getByLabelText("Role"), "lead");
    await user.click(screen.getByRole("button", { name: /Send invitation/ }));
    expect(props.onInvite).toHaveBeenCalledWith({
      team_id: "team-beta",
      email: "new@example.com",
      role: "lead",
    });
  });

  it("calls the close handler from the cancel button", async () => {
    const user = userEvent.setup();
    const props = renderDialog();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(props.onClose).toHaveBeenCalledTimes(1);
  });

  it("surfaces an API error as an alert", () => {
    renderDialog({ error: "A pending invitation already exists" });
    expect(screen.getByRole("alert")).toHaveTextContent(
      "A pending invitation already exists",
    );
  });
});
