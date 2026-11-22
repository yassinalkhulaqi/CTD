import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { makeMember } from "../fixtures";
import { MemberCard } from "./MemberCard";

describe("MemberCard", () => {
  it("shows the member identity, role, timezone and capacity", () => {
    render(
      <MemberCard
        member={makeMember({ role: "lead" })}
        assignedHours={4}
        onRoleChange={vi.fn()}
        onRemove={vi.fn()}
      />,
    );
    expect(screen.getByText("Nyx Chandler")).toBeInTheDocument();
    expect(screen.getByText("@nyx")).toBeInTheDocument();
    expect(screen.getByLabelText("Role: Lead")).toBeInTheDocument();
    expect(screen.getByText("Europe/London")).toBeInTheDocument();
    expect(
      screen.getByRole("progressbar", { name: "Capacity for nyx" }),
    ).toHaveAttribute("aria-valuenow", "50");
  });

  it("changes a role from the menu", async () => {
    const user = userEvent.setup();
    const onRoleChange = vi.fn();
    const member = makeMember();
    render(
      <MemberCard
        member={member}
        assignedHours={0}
        onRoleChange={onRoleChange}
        onRemove={vi.fn()}
      />,
    );
    await user.click(
      screen.getByRole("button", { name: "Role options for nyx" }),
    );
    await user.click(screen.getByRole("menuitem", { name: "Lead" }));
    expect(onRoleChange).toHaveBeenCalledWith(member, "lead");
  });

  it("removes a member from the menu", async () => {
    const user = userEvent.setup();
    const onRemove = vi.fn();
    const member = makeMember();
    render(
      <MemberCard
        member={member}
        assignedHours={0}
        onRoleChange={vi.fn()}
        onRemove={onRemove}
      />,
    );
    await user.click(
      screen.getByRole("button", { name: "Role options for nyx" }),
    );
    await user.click(screen.getByRole("menuitem", { name: "Remove member" }));
    expect(onRemove).toHaveBeenCalledWith(member);
  });

  it("does not emit a role change when the current role is chosen", async () => {
    const user = userEvent.setup();
    const onRoleChange = vi.fn();
    render(
      <MemberCard
        member={makeMember()}
        assignedHours={0}
        onRoleChange={onRoleChange}
        onRemove={vi.fn()}
      />,
    );
    await user.click(
      screen.getByRole("button", { name: "Role options for nyx" }),
    );
    await user.click(screen.getByRole("menuitem", { name: "Member" }));
    expect(onRoleChange).not.toHaveBeenCalled();
  });
});
