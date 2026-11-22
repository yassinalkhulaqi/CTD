import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LeaderboardPanel } from "./LeaderboardPanel";
import { makeLeaderboardEntry } from "../testFixtures";

describe("LeaderboardPanel", () => {
  it("renders ranked members and their points", () => {
    render(
      <LeaderboardPanel
        entries={[
          makeLeaderboardEntry(),
          makeLeaderboardEntry({
            member_id: "member-2",
            handle: "orbit",
            display_name: "Orbit",
            label: "Orbit (@orbit)",
            rank: 2,
            points: 240,
            awards: 6,
          }),
        ]}
      />,
    );
    expect(screen.getByText("Nova (@nova)")).toBeInTheDocument();
    expect(screen.getByText("Orbit (@orbit)")).toBeInTheDocument();
    expect(screen.getByText("320")).toBeInTheDocument();
    expect(screen.getByText("240")).toBeInTheDocument();
    expect(screen.getByLabelText("Rank 1")).toBeInTheDocument();
  });

  it("highlights the selected member", () => {
    const { container } = render(
      <LeaderboardPanel
        entries={[makeLeaderboardEntry()]}
        highlightedMemberId="member-1"
      />,
    );
    expect(container.querySelectorAll("li")[0].className).toContain(
      "highlighted",
    );
  });

  it("shows an empty state when nobody has awards", () => {
    render(<LeaderboardPanel entries={[]} />);
    expect(screen.getByText("No awards yet")).toBeInTheDocument();
  });

  it("shows skeleton rows while loading", () => {
    const { container } = render(
      <LeaderboardPanel entries={undefined} loading />,
    );
    expect(container.querySelectorAll('[aria-hidden="true"]')).not.toHaveLength(
      0,
    );
    expect(screen.queryByText("No awards yet")).not.toBeInTheDocument();
  });
});
