/** Tests for the filter bar. */

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { SearchFilters } from "./SearchFilters";

describe("SearchFilters", () => {
  it("toggles kind chips and exposes their pressed state", () => {
    const onToggle = vi.fn();
    render(
      <SearchFilters
        kinds={["team"]}
        onToggle={onToggle}
        onClear={vi.fn()}
        limit={20}
        onLimitChange={vi.fn()}
      />,
    );
    const teams = screen.getByRole("button", { name: /Teams/ });
    expect(teams).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(teams);
    expect(onToggle).toHaveBeenCalledWith("team");
    fireEvent.click(screen.getByRole("button", { name: /Challenges/ }));
    expect(onToggle).toHaveBeenCalledWith("challenge");
  });

  it("clears filters and changes the result limit", () => {
    const onClear = vi.fn();
    const onLimitChange = vi.fn();
    render(
      <SearchFilters
        kinds={["team"]}
        onToggle={vi.fn()}
        onClear={onClear}
        limit={20}
        onLimitChange={onLimitChange}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(onClear).toHaveBeenCalledTimes(1);
    fireEvent.change(screen.getByLabelText("Results per search"), {
      target: { value: "50" },
    });
    expect(onLimitChange).toHaveBeenCalledWith(50);
  });

  it("shows counters when stats are provided", () => {
    render(
      <SearchFilters
        kinds={[]}
        onToggle={vi.fn()}
        onClear={vi.fn()}
        limit={10}
        onLimitChange={vi.fn()}
        stats={{
          document_count: 3,
          command_count: 8,
          documents_by_kind: { challenge: 3 },
          top_tags: [],
          average_body_length: 0,
          has_documents: true,
          distinct_kinds: 1,
        }}
      />,
    );
    expect(
      screen.getByRole("button", { name: /Challenges.*3/ }),
    ).toBeInTheDocument();
  });
});
