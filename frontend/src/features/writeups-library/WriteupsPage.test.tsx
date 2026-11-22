/** Rendered page interaction test for the writeups library. */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import {
  addReview,
  bookmarksFor,
  getStats,
  getWriteup,
  listReviews,
  listWriteups,
  rateWriteup,
  toggleBookmark,
} from "./api";
import type { Writeup, WriteupStats } from "./types";
import { WriteupsPage } from "./WriteupsPage";

vi.mock("./api", () => ({
  listWriteups: vi.fn(),
  getStats: vi.fn(),
  bookmarksFor: vi.fn(),
  getWriteup: vi.fn(),
  listReviews: vi.fn(),
  createWriteup: vi.fn(),
  deleteWriteup: vi.fn(),
  publishWriteup: vi.fn(),
  submitWriteup: vi.fn(),
  withdrawWriteup: vi.fn(),
  rateWriteup: vi.fn(),
  toggleBookmark: vi.fn(),
  addReview: vi.fn(),
  updateWriteup: vi.fn(),
}));

const writeup: Writeup = {
  id: "wu_1",
  challenge_id: "challenge-1",
  author_id: "member-1",
  title: "Nonce reuse in the wild",
  slug: "nonce-reuse-in-the-wild",
  summary: "How a repeated nonce breaks confidentiality.",
  body: "## Attack\nReusing a nonce destroys the keystream.",
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
  toc: [{ level: 2, title: "Attack", anchor: "attack" }],
};

const stats: WriteupStats = {
  total: 1,
  published: 1,
  drafts: 0,
  in_review: 0,
  total_views: 1240,
  total_ratings: 2,
  bookmarks: 0,
  publication_rate: 1,
  average_views: 1240,
  by_category: [],
  by_status: [],
  top_rated: [],
};

describe("WriteupsPage", () => {
  beforeEach(() => {
    vi.mocked(listWriteups).mockResolvedValue({
      items: [writeup],
      total: 1,
      offset: 0,
      limit: 24,
    });
    vi.mocked(getStats).mockResolvedValue(stats);
    vi.mocked(bookmarksFor).mockResolvedValue([]);
    vi.mocked(getWriteup).mockResolvedValue(writeup);
    vi.mocked(listReviews).mockResolvedValue([]);
    vi.mocked(toggleBookmark).mockResolvedValue({
      writeup_id: "wu_1",
      member_id: "member-1",
      bookmarked: true,
      count: 1,
    });
    vi.mocked(rateWriteup).mockResolvedValue(writeup);
    vi.mocked(addReview).mockResolvedValue({
      id: "rv_1",
      writeup_id: "wu_1",
      reviewer_id: "member-1",
      verdict: "approve",
      comment: "Clear explanation.",
      approved: true,
      created_at: "2026-01-03T00:00:00Z",
    });
  });

  it("renders the library hero and loaded writeup", async () => {
    render(<WriteupsPage />);
    expect(screen.getByText("The writeups library")).toBeInTheDocument();
    expect(
      await screen.findByText("Nonce reuse in the wild"),
    ).toBeInTheDocument();
    expect(listWriteups).toHaveBeenCalled();
  });

  it("reloads the library when the search filter changes", async () => {
    render(<WriteupsPage />);
    const search = screen.getByLabelText("Search library");
    fireEvent.change(search, { target: { value: "nonce" } });
    await waitFor(() => {
      const lastCall = vi.mocked(listWriteups).mock.calls.at(-1);
      expect(lastCall?.[0].search).toBe("nonce");
    });
  });

  it("opens the reading view from a card", async () => {
    render(<WriteupsPage />);
    fireEvent.click(
      await screen.findByRole("button", { name: /Nonce reuse in the wild/ }),
    );
    expect(await screen.findByText("Reading view")).toBeInTheDocument();
    expect(getWriteup).toHaveBeenCalledWith("wu_1");
    expect(
      screen.getByRole("navigation", { name: "Table of contents" }),
    ).toBeInTheDocument();
  });

  it("reveals the composer with a live preview", () => {
    render(<WriteupsPage />);
    fireEvent.click(screen.getByRole("button", { name: "Write a writeup" }));
    expect(
      screen.getByRole("region", { name: "Write a new writeup" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Live preview")).toBeInTheDocument();
  });
});
