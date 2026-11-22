/** API adapter tests for the writeups library. */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { del, get, patch, post } from "../../api/client";
import {
  addReview,
  createWriteup,
  deleteWriteup,
  getStats,
  getWriteup,
  listWriteups,
  publishWriteup,
  rateWriteup,
  toggleBookmark,
  updateWriteup,
} from "./api";
import { DEFAULT_FILTERS } from "./types";

vi.mock("../../api/client", () => ({
  buildQuery: (
    params?: Record<string, string | number | boolean | null | undefined>,
  ) => {
    if (!params) return "";
    const search = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null || value === "") continue;
      search.set(key, String(value));
    }
    const encoded = search.toString();
    return encoded ? `?${encoded}` : "";
  },
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  del: vi.fn(),
}));

describe("writeups API adapter", () => {
  beforeEach(() => {
    vi.mocked(get).mockReset();
    vi.mocked(post).mockReset();
    vi.mocked(patch).mockReset();
    vi.mocked(del).mockReset();
  });

  it("builds a filtered list request", async () => {
    vi.mocked(get).mockResolvedValue({
      items: [],
      total: 0,
      offset: 0,
      limit: 24,
    });
    const result = await listWriteups(
      { ...DEFAULT_FILTERS, category: "web", search: "shell" },
      1,
      12,
    );
    expect(get).toHaveBeenCalledWith(
      "/api/writeups?status=published&category=web&search=shell&sort=date&offset=1&limit=12",
      { signal: undefined },
    );
    expect(result.total).toBe(0);
  });

  it("omits all filters from the default list request", async () => {
    vi.mocked(get).mockResolvedValue({
      items: [],
      total: 0,
      offset: 0,
      limit: 24,
    });
    await listWriteups(DEFAULT_FILTERS);
    expect(get).toHaveBeenCalledWith(
      "/api/writeups?status=published&sort=date&offset=0&limit=24",
      {
        signal: undefined,
      },
    );
  });

  it("encodes identifiers and view tracking", async () => {
    vi.mocked(get).mockResolvedValue({});
    await getWriteup("wu/42", false);
    expect(get).toHaveBeenCalledWith("/api/writeups/wu%2F42?track_view=false");
  });

  it("posts creation and workflow commands to the right paths", async () => {
    vi.mocked(post).mockResolvedValue({ id: "wu_1" });
    await createWriteup({
      challenge_id: "c1",
      author_id: "m1",
      title: "Title",
      summary: "A summary long enough",
      body: "Body",
      category: "crypto",
      difficulty: "hard",
      tags: ["crypto"],
    });
    expect(post).toHaveBeenCalledWith(
      "/api/writeups",
      expect.objectContaining({ title: "Title" }),
    );

    await publishWriteup("wu_1");
    expect(post).toHaveBeenCalledWith("/api/writeups/wu_1/publish");

    await rateWriteup("wu_1", "m2", 5);
    expect(post).toHaveBeenCalledWith("/api/writeups/wu_1/rate", {
      member_id: "m2",
      score: 5,
    });

    await toggleBookmark("wu_1", "m2");
    expect(post).toHaveBeenCalledWith("/api/writeups/wu_1/bookmark", {
      member_id: "m2",
    });

    await addReview("wu_1", {
      reviewer_id: "m3",
      verdict: "approve",
      comment: "Good",
    });
    expect(post).toHaveBeenCalledWith("/api/writeups/wu_1/reviews", {
      reviewer_id: "m3",
      verdict: "approve",
      comment: "Good",
    });
  });

  it("uses patch and delete for edits and removal", async () => {
    vi.mocked(patch).mockResolvedValue({ id: "wu_1" });
    vi.mocked(del).mockResolvedValue(undefined);
    await updateWriteup("wu_1", { title: "Renamed" });
    expect(patch).toHaveBeenCalledWith("/api/writeups/wu_1", {
      title: "Renamed",
    });
    await deleteWriteup("wu_1");
    expect(del).toHaveBeenCalledWith("/api/writeups/wu_1");
  });

  it("requests statistics", async () => {
    vi.mocked(get).mockResolvedValue({ total: 3 });
    await getStats();
    expect(get).toHaveBeenCalledWith("/api/writeups/stats");
  });
});
