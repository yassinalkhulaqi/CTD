import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Podium } from "./Podium";
import type { RankingEntry } from "../types";

function entry(rank: number, teamName: string): RankingEntry {
  return {
    team_id: `team-${rank}`,
    team_name: teamName,
    points: 1000 - rank * 100,
    solves: 10 - rank,
    rank,
    previous_rank: rank + 1,
    movement: "up",
    movement_label: "↑1",
    last_solve_at: null,
  };
}

describe("Podium", () => {
  const entries = [
    entry(1, "RedScribe"),
    entry(2, "Null Pointers"),
    entry(3, "Cipher Wardens"),
  ];

  it("highlights the champion and shows all three places", () => {
    render(<Podium entries={entries} />);
    expect(screen.getByText("Champion")).toBeInTheDocument();
    expect(screen.getByText("2nd place")).toBeInTheDocument();
    expect(screen.getByText("3rd place")).toBeInTheDocument();
    expect(screen.getByText("RedScribe")).toBeInTheDocument();
  });

  it("renders the first place card in the middle of the row", () => {
    render(<Podium entries={entries} />);
    const list = screen.getByRole("list", { name: "Top three teams" });
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(within(items[1]).getByText("RedScribe")).toBeInTheDocument();
  });

  it("invokes the selection callback", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<Podium entries={entries} onSelect={onSelect} />);
    await user.click(screen.getByLabelText("Inspect Null Pointers"));
    expect(onSelect).toHaveBeenCalledWith("team-2");
  });

  it("renders an empty state without entries", () => {
    render(<Podium entries={[]} />);
    expect(screen.getByText("No ranking yet")).toBeInTheDocument();
  });
});
