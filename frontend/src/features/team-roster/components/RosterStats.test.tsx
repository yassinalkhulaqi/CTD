import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { makeStats } from "../fixtures";
import { RosterStatsView } from "./RosterStats";

describe("RosterStatsView", () => {
  it("renders the headline statistic tiles", () => {
    render(
      <RosterStatsView
        stats={makeStats()}
        summary={{
          members: 4,
          leads: 1,
          available: 2,
          pending: 1,
          utilisation: 0.25,
        }}
      />,
    );
    expect(screen.getByText("Roster overview")).toBeInTheDocument();
    expect(screen.getByText("Pending invites")).toBeInTheDocument();
    expect(screen.getByText("25%")).toBeInTheDocument();
  });

  it("renders role and availability breakdown bars", () => {
    render(
      <RosterStatsView
        stats={makeStats()}
        summary={{
          members: 4,
          leads: 1,
          available: 2,
          pending: 1,
          utilisation: 0.25,
        }}
      />,
    );
    expect(
      screen.getByRole("progressbar", { name: "Lead members" }),
    ).toHaveAttribute("aria-valuenow", "25");
    expect(
      screen.getByRole("progressbar", { name: "Available members" }),
    ).toBeInTheDocument();
  });

  it("falls back to the local summary while stats are absent", () => {
    render(
      <RosterStatsView
        stats={null}
        summary={{
          members: 2,
          leads: 1,
          available: 1,
          pending: 3,
          utilisation: 0.5,
        }}
      />,
    );
    expect(screen.getByText("50%")).toBeInTheDocument();
    expect(screen.getAllByText("1").length).toBeGreaterThan(0);
  });
});
