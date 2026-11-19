import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RankTable } from "./RankTable";
import type { RankingEntry } from "../types";

function entry(overrides: Partial<RankingEntry> = {}): RankingEntry {
  return {
    team_id: "team-1",
    team_name: "RedScribe",
    points: 2450,
    solves: 12,
    rank: 1,
    previous_rank: 3,
    movement: "up",
    movement_label: "↑2",
    last_solve_at: null,
    ...overrides,
  };
}

const ENTRIES = [
  entry(),
  entry({
    team_id: "team-2",
    team_name: "Null Pointers",
    points: 2100,
    solves: 9,
    rank: 2,
    previous_rank: 2,
    movement: "stable",
    movement_label: "—",
  }),
  entry({
    team_id: "team-3",
    team_name: "Cipher Wardens",
    points: 1800,
    solves: 11,
    rank: 3,
    previous_rank: null,
    movement: "new",
    movement_label: "NEW",
  }),
];

describe("RankTable", () => {
  it("renders ranks, solve counts and movement arrows", () => {
    render(<RankTable entries={ENTRIES} />);
    expect(screen.getByText("RedScribe")).toBeInTheDocument();
    expect(screen.getByLabelText("12 solves")).toHaveTextContent("12");
    expect(screen.getByText("↑2")).toBeInTheDocument();
    expect(screen.getByText("NEW")).toBeInTheDocument();
    expect(screen.getByLabelText("Rank unchanged")).toBeInTheDocument();
  });

  it("selects a team when its name is activated", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<RankTable entries={ENTRIES} onSelect={onSelect} />);
    await user.click(screen.getByLabelText("Inspect Null Pointers"));
    expect(onSelect).toHaveBeenCalledWith("team-2");
  });

  it("reorders rows when a sortable header is activated", async () => {
    const user = userEvent.setup();
    render(<RankTable entries={ENTRIES} />);
    const names = () =>
      screen
        .getAllByRole("row")
        .slice(1)
        .map((row) => row.textContent);
    const before = names();
    await user.click(screen.getByRole("button", { name: /Solves/ }));
    expect(names()).not.toEqual(before);
  });

  it("shows an empty message when no teams are ranked", () => {
    render(<RankTable entries={[]} />);
    expect(screen.getByText("No teams to rank yet.")).toBeInTheDocument();
  });
});
