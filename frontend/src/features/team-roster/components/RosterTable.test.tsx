import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { MemberFilters } from "../types";
import { makeMember, makeMemberSet } from "../fixtures";
import { RosterTable } from "./RosterTable";

const filters: MemberFilters = {
  teamId: "all",
  role: "all",
  availability: "all",
  query: "",
};

type TableProps = Parameters<typeof RosterTable>[0];

function baseProps(overrides: Partial<TableProps> = {}): TableProps {
  return {
    members: makeMemberSet(),
    assignedHours: { "member-1": 4 },
    filters,
    onFiltersChange: vi.fn(),
    sortKey: "name",
    onSortChange: vi.fn(),
    onRoleChange: vi.fn(),
    onRemove: vi.fn(),
    loading: false,
    busy: false,
    ...overrides,
  };
}

function renderTable(overrides: Partial<TableProps> = {}) {
  const props = baseProps(overrides);
  render(<RosterTable {...props} />);
  return props;
}

describe("RosterTable", () => {
  it("renders the columns and every member row", () => {
    renderTable();
    expect(
      screen.getByRole("table", { name: "Team roster" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Nyx Chandler")).toBeInTheDocument();
    expect(screen.getByText("Atlas Vale")).toBeInTheDocument();
    expect(screen.getByText("4 members in view")).toBeInTheDocument();
  });

  it("shows role chips, availability and an accessible capacity bar", () => {
    renderTable({ members: [makeMember()] });
    expect(screen.getByLabelText("Role: Member")).toBeInTheDocument();
    expect(
      within(screen.getByRole("table", { name: "Team roster" })).getByText(
        "Available",
      ),
    ).toBeInTheDocument();
    const bar = screen.getByRole("progressbar", { name: "Capacity for nyx" });
    expect(bar).toHaveAttribute("aria-valuenow", "50");
    expect(bar).toHaveAttribute("aria-valuetext", "4h of 8h reserved");
  });

  it("changes a role through the inline menu", async () => {
    const user = userEvent.setup();
    const props = renderTable({ members: [makeMember()] });
    await user.selectOptions(
      screen.getByLabelText("Change role for nyx"),
      "lead",
    );
    expect(props.onRoleChange).toHaveBeenCalledTimes(1);
    expect(props.onRoleChange).toHaveBeenCalledWith(props.members[0], "lead");
  });

  it("removes a member through the row action", async () => {
    const user = userEvent.setup();
    const props = renderTable({ members: [makeMember()] });
    await user.click(screen.getByRole("button", { name: "Remove nyx" }));
    expect(props.onRemove).toHaveBeenCalledWith(props.members[0]);
  });

  it("reports filter and sort interactions", async () => {
    const user = userEvent.setup();
    const props = renderTable();
    await user.selectOptions(screen.getByLabelText("Filter by role"), "lead");
    expect(props.onFiltersChange).toHaveBeenCalledWith({
      ...filters,
      role: "lead",
    });
    fireEvent.change(screen.getByLabelText("Search roster"), {
      target: { value: "crypto" },
    });
    expect(props.onFiltersChange).toHaveBeenCalledWith({
      ...filters,
      query: "crypto",
    });
    await user.click(screen.getByRole("button", { name: /Role/ }));
    expect(props.onSortChange).toHaveBeenCalledWith("role");
  });

  it("shows skeleton rows while loading and an empty state when empty", () => {
    const { rerender } = render(
      <RosterTable {...baseProps({ members: [], loading: true })} />,
    );
    expect(
      screen.getByRole("table", { name: "Loading roster" }),
    ).toBeInTheDocument();
    rerender(<RosterTable {...baseProps({ members: [] })} />);
    expect(screen.getByText("No roster members")).toBeInTheDocument();
  });
});
