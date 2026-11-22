import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TierFilter } from "./TierFilter";

describe("TierFilter", () => {
  it("renders tier options with counts", () => {
    render(
      <TierFilter
        tier="all"
        kind="all"
        query=""
        counts={{ all: 12, bronze: 6, silver: 4, gold: 2 }}
        onTierChange={vi.fn()}
        onKindChange={vi.fn()}
        onQueryChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /All tiers/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: /gold/i })).toHaveTextContent(
      "2",
    );
  });

  it("reports tier selections", () => {
    const onTierChange = vi.fn();
    render(
      <TierFilter
        tier="all"
        kind="all"
        query=""
        onTierChange={onTierChange}
        onKindChange={vi.fn()}
        onQueryChange={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /silver/i }));
    expect(onTierChange).toHaveBeenCalledWith("silver");
  });

  it("reports criterion selections", () => {
    const onKindChange = vi.fn();
    render(
      <TierFilter
        tier="all"
        kind="all"
        query=""
        onTierChange={vi.fn()}
        onKindChange={onKindChange}
        onQueryChange={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "streak" },
    });
    expect(onKindChange).toHaveBeenCalledWith("streak");
  });

  it("reports search text", () => {
    const onQueryChange = vi.fn();
    render(
      <TierFilter
        tier="all"
        kind="all"
        query=""
        onTierChange={vi.fn()}
        onKindChange={vi.fn()}
        onQueryChange={onQueryChange}
      />,
    );
    fireEvent.change(screen.getByPlaceholderText("Search badges"), {
      target: { value: "streak" },
    });
    expect(onQueryChange).toHaveBeenCalledWith("streak");
  });
});
