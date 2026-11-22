/** Rendered interaction tests for the rating control. */

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RatingStars } from "./components/RatingStars";

describe("RatingStars", () => {
  it("exposes an accessible radiogroup with five options", () => {
    render(<RatingStars value={3} onRate={vi.fn()} />);
    expect(
      screen.getByRole("radiogroup", { name: "Rate this writeup" }),
    ).toBeInTheDocument();
    const stars = screen.getAllByRole("radio");
    expect(stars).toHaveLength(5);
    expect(stars[2]).toHaveAttribute("aria-checked", "true");
    expect(stars[0]).toHaveAttribute("tabindex", "-1");
    expect(stars[2]).toHaveAttribute("tabindex", "0");
  });

  it("supports arrow navigation and commits with Enter", () => {
    const onRate = vi.fn();
    render(<RatingStars value={1} onRate={onRate} />);
    const stars = screen.getAllByRole("radio");
    stars[0].focus();
    fireEvent.keyDown(stars[0], { key: "ArrowRight" });
    expect(stars[1]).toHaveFocus();
    fireEvent.keyDown(stars[1], { key: "End" });
    expect(stars[4]).toHaveFocus();
    fireEvent.keyDown(stars[4], { key: "Home" });
    expect(stars[0]).toHaveFocus();
    fireEvent.keyDown(stars[0], { key: "ArrowLeft" });
    expect(stars[0]).toHaveFocus();
    fireEvent.keyDown(stars[0], { key: "Enter" });
    expect(onRate).toHaveBeenCalledWith(1);
  });

  it("commits a score on click and space", () => {
    const onRate = vi.fn();
    render(<RatingStars onRate={onRate} />);
    const stars = screen.getAllByRole("radio");
    fireEvent.click(stars[3]);
    expect(onRate).toHaveBeenLastCalledWith(4);
    fireEvent.keyDown(stars[3], { key: " " });
    expect(onRate).toHaveBeenLastCalledWith(4);
  });

  it("renders a read-only summary with an accessible label", () => {
    render(<RatingStars average={4.2} count={9} />);
    expect(
      screen.getByRole("img", { name: "4.2 out of 5 from 9 ratings" }),
    ).toBeInTheDocument();
    expect(screen.queryAllByRole("radio")).toHaveLength(0);
  });

  it("disables the group when requested", () => {
    const onRate = vi.fn();
    render(<RatingStars onRate={onRate} disabled />);
    const group = screen.getByRole("radiogroup");
    expect(group).toHaveAttribute("aria-disabled", "true");
    fireEvent.click(screen.getAllByRole("radio")[1]);
    expect(onRate).not.toHaveBeenCalled();
  });
});
