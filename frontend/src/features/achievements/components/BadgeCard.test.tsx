import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BadgeCard } from "./BadgeCard";
import { makeBadgeView } from "../testFixtures";

describe("BadgeCard", () => {
  it("renders the badge name, tier and score", () => {
    render(
      <BadgeCard
        view={makeBadgeView({
          badge: {
            ...makeBadgeView().badge,
            name: "Speed Runner",
            tier: "gold",
            score: 40,
          },
        })}
        onSelect={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("button", { name: /Speed Runner/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("gold")).toBeInTheDocument();
    expect(screen.getByText("40 pts")).toBeInTheDocument();
  });

  it("reports the current progress through an accessible meter", () => {
    render(
      <BadgeCard
        view={makeBadgeView({ current: 4, target: 8, percent: 50 })}
        onSelect={vi.fn()}
      />,
    );
    const meter = screen.getByRole("meter", { name: /criterion progress/i });
    expect(meter).toHaveAttribute("aria-valuenow", "4");
    expect(meter).toHaveAttribute("aria-valuemax", "8");
  });

  it("invokes the selection callback when activated", () => {
    const onSelect = vi.fn();
    const view = makeBadgeView();
    render(<BadgeCard view={view} onSelect={onSelect} />);
    fireEvent.click(screen.getByRole("button", { name: /First Blood/i }));
    expect(onSelect).toHaveBeenCalledWith(view);
  });

  it("masks secret badges until they are revealed", () => {
    const view = makeBadgeView({
      revealed: false,
      display_name: "???",
      display_description: "A hidden achievement",
    });
    render(<BadgeCard view={view} onSelect={vi.fn()} />);
    expect(screen.getByText("???")).toBeInTheDocument();
    expect(screen.getByText("A hidden achievement")).toBeInTheDocument();
  });

  it("marks a freshly unlocked badge with a celebration label", () => {
    render(
      <BadgeCard
        view={makeBadgeView({ awarded: true, percent: 100 })}
        onSelect={vi.fn()}
        newlyUnlocked
      />,
    );
    const card = screen.getByRole("button", { name: /First Blood/i });
    expect(card).toHaveAttribute(
      "aria-label",
      expect.stringContaining("First Blood"),
    );
    expect(card.querySelector("svg")).toBeInTheDocument();
  });
});
