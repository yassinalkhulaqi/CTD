/** Tests for query highlighting. */

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Highlight, highlightSegments } from "./Highlight";

describe("Highlight", () => {
  it("marks every case-insensitive token match", () => {
    render(<Highlight text="Web Shell Challenge" query="web shell" />);
    expect(screen.getByText("Web").tagName).toBe("MARK");
    expect(screen.getByText("Shell").tagName).toBe("MARK");
    expect(screen.getByText("Challenge")).toBeInTheDocument();
  });

  it("renders plain text when no tokens match", () => {
    render(<Highlight text="Nothing here" query="missing" />);
    expect(document.querySelectorAll("mark")).toHaveLength(0);
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });

  it("exposes segment offsets for tests and callers", () => {
    expect(highlightSegments("Alpha beta", "alpha")).toEqual([
      { text: "Alpha", match: true },
      { text: " beta", match: false },
    ]);
  });

  it("highlights partial tokens inside longer words", () => {
    const segments = highlightSegments("Challenges board", "challen");
    expect(segments[0]).toEqual({ text: "Challen", match: true });
  });
});
