/** Rendered interaction tests for the library card. */

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WriteupCard } from "./components/WriteupCard";
import type { Writeup } from "./types";

function writeup(overrides: Partial<Writeup> = {}): Writeup {
  return {
    id: "wu_1",
    challenge_id: "challenge-1",
    author_id: "member-1",
    title: "Nonce reuse in the wild",
    slug: "nonce-reuse-in-the-wild",
    summary: "How a repeated nonce breaks confidentiality.",
    body: "## Attack\nDetails.",
    category: "crypto",
    difficulty: "hard",
    tags: ["crypto", "aes"],
    status: "published",
    excerpt: "How a repeated nonce breaks confidentiality.",
    word_count: 420,
    reading_minutes: 3,
    average_rating: 4.5,
    bayesian_score: 4.12,
    rating_sum: 9,
    rating_count: 2,
    views: 1240,
    created_at: "2026-01-01T00:00:00Z",
    published_at: "2026-01-02T00:00:00Z",
    toc: [],
    ...overrides,
  };
}

describe("WriteupCard", () => {
  it("shows the magazine card content", () => {
    render(<WriteupCard writeup={writeup()} onOpen={vi.fn()} />);
    expect(
      screen.getByRole("button", { name: /Nonce reuse in the wild/ }),
    ).toBeInTheDocument();
    expect(screen.getByText("#crypto")).toBeInTheDocument();
    expect(screen.getByText("4.12")).toBeInTheDocument();
    expect(screen.getByText("3m")).toBeInTheDocument();
  });

  it("opens the reader when the title is activated by keyboard", () => {
    const onOpen = vi.fn();
    render(<WriteupCard writeup={writeup()} onOpen={onOpen} />);
    const title = screen.getByRole("button", {
      name: /Nonce reuse in the wild/,
    });
    title.focus();
    fireEvent.keyDown(title, { key: "Enter" });
    fireEvent.click(title);
    expect(onOpen).toHaveBeenCalledWith(
      expect.objectContaining({ id: "wu_1" }),
    );
  });

  it("toggles the bookmark through its accessible button", () => {
    const onBookmark = vi.fn();
    const { rerender } = render(
      <WriteupCard
        writeup={writeup()}
        bookmarked={false}
        onOpen={vi.fn()}
        onBookmark={onBookmark}
      />,
    );
    const bookmark = screen.getByRole("button", {
      name: "Bookmark this writeup",
    });
    expect(bookmark).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(bookmark);
    expect(onBookmark).toHaveBeenCalledTimes(1);

    rerender(
      <WriteupCard
        writeup={writeup()}
        bookmarked
        onOpen={vi.fn()}
        onBookmark={onBookmark}
      />,
    );
    expect(
      screen.getByRole("button", { name: "Remove bookmark" }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("renders draft status distinctly", () => {
    render(
      <WriteupCard writeup={writeup({ status: "draft" })} onOpen={vi.fn()} />,
    );
    expect(screen.getByText("draft")).toBeInTheDocument();
  });
});
