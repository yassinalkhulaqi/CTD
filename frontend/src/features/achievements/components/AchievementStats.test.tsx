import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AchievementStatsPanel } from "./AchievementStats";
import { makeStats } from "../testFixtures";

describe("AchievementStatsPanel", () => {
  it("renders aggregate achievement statistics", () => {
    render(<AchievementStatsPanel stats={makeStats()} />);
    expect(screen.getByText("Badges unlocked")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("1,280")).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByText("68%")).toBeInTheDocument();
  });

  it("renders placeholders while loading", () => {
    const { container } = render(
      <AchievementStatsPanel stats={undefined} loading />,
    );
    expect(container.firstElementChild).toHaveAttribute("aria-busy", "true");
    expect(screen.getAllByText("Loading")).toHaveLength(4);
    expect(container.querySelectorAll('[aria-hidden="true"]')).not.toHaveLength(
      0,
    );
  });
});
