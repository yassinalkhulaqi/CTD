/** Rendered tests for the completeness report table. */

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { CompletenessTable } from "./components/CompletenessTable";
import type { CompletenessStat } from "./types";

const stats: CompletenessStat[] = [
  {
    locale: "fr",
    namespace: "ui",
    reference: "en",
    total: 4,
    translated: 3,
    missing: 1,
    missing_keys: ["items.one"],
    percent: 75,
    is_complete: false,
  },
  {
    locale: "en",
    namespace: "ui",
    reference: "en",
    total: 4,
    translated: 4,
    missing: 0,
    missing_keys: [],
    percent: 100,
    is_complete: true,
  },
];

describe("CompletenessTable", () => {
  it("renders one row per locale and namespace", () => {
    render(<CompletenessTable stats={stats} />);
    expect(
      screen.getByRole("table", { name: "Translation completeness" }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(3);
    expect(screen.getByText("75.0%")).toBeInTheDocument();
    expect(screen.getByText("1 missing")).toBeInTheDocument();
    expect(screen.getByText("Complete")).toBeInTheDocument();
  });

  it("exposes progress values to assistive technology", () => {
    render(<CompletenessTable stats={stats} />);
    const bars = screen.getAllByRole("progressbar");
    expect(bars[0]).toHaveAttribute("aria-valuenow", "75");
    expect(bars[1]).toHaveAttribute("aria-valuenow", "100");
  });

  it("selects a locale when its row button is pressed", () => {
    const onSelect = vi.fn();
    render(
      <CompletenessTable
        stats={stats}
        onSelect={onSelect}
        selectedLocale="en"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "fr" }));
    expect(onSelect).toHaveBeenCalledWith("fr");
  });

  it("renders an empty state without statistics", () => {
    render(<CompletenessTable stats={[]} />);
    expect(screen.getByText("No translations yet")).toBeInTheDocument();
  });
});
