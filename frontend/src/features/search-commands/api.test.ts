/** API adapter tests using mocked low-level request helpers. */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { del, get, post } from "../../api/client";
import { searchApi } from "./api";
import { rankResults } from "./searchUtils";
import type { Command, SearchResponse } from "./types";

vi.mock("../../api/client", async () => {
  const actual =
    await vi.importActual<Record<string, unknown>>("../../api/client");
  return {
    ...actual,
    get: vi.fn(),
    post: vi.fn(),
    del: vi.fn(),
  };
});

const response: SearchResponse = {
  query: {
    text: "sql",
    kinds: ["challenge"],
    tags: [],
    limit: 20,
    tokens: ["sql"],
    has_filters: true,
  },
  results: [
    {
      document_id: "b",
      kind: "challenge",
      title: "SQL Basics",
      snippet: "sql",
      score: 2,
      highlights: [],
      path: "/challenges/b",
      relevance: "related",
    },
    {
      document_id: "a",
      kind: "challenge",
      title: "Advanced SQL",
      snippet: "sql",
      score: 9,
      highlights: [],
      path: "/challenges/a",
      relevance: "exact",
    },
  ],
  total_indexed: 12,
  returned: 2,
};

describe("search API adapter", () => {
  beforeEach(() => {
    vi.mocked(get).mockReset();
    vi.mocked(post).mockReset();
    vi.mocked(del).mockReset();
  });

  it("serialises query filters into the request path", async () => {
    vi.mocked(get).mockResolvedValue(response);
    const payload = await searchApi.search({
      q: "sql",
      limit: 10,
      kinds: ["challenge", "team"],
      tags: ["web"],
    });
    const path = vi.mocked(get).mock.calls[0][0];
    expect(path).toContain("q=sql");
    expect(path).toContain("limit=10");
    expect(decodeURIComponent(path)).toContain("kind=challenge,team");
    expect(decodeURIComponent(path)).toContain("tag=web");
    expect(
      rankResults(payload.results).map((item) => item.document_id),
    ).toEqual(["a", "b"]);
  });

  it("posts an index request", async () => {
    vi.mocked(post).mockResolvedValue({
      indexed: 3,
      by_kind: {},
      skipped: 0,
      document_count: 3,
    });
    await searchApi.index({ include_repositories: true });
    expect(vi.mocked(post)).toHaveBeenCalledWith(
      "/api/search/index",
      { include_repositories: true },
      undefined,
    );
  });

  it("encodes command identifiers when executing", async () => {
    const execution = {
      command_id: "nav/search",
      name: "Search",
      action: "navigate",
      target: "/search",
      message: "Open Search",
      arguments: "",
      is_navigation: true,
    };
    vi.mocked(post).mockResolvedValue(execution);
    const result = await searchApi.execute("nav/search", "web");
    expect(vi.mocked(post)).toHaveBeenCalledWith(
      "/api/search/commands/nav%2Fsearch/execute",
      { arguments: "web" },
      undefined,
    );
    expect(result.target).toBe("/search");
  });

  it("loads commands and stats and deletes documents", async () => {
    const commands: Command[] = [];
    vi.mocked(get)
      .mockResolvedValueOnce({ commands, groups: [], total: 0 })
      .mockResolvedValueOnce({
        document_count: 1,
        command_count: 0,
        documents_by_kind: {},
        top_tags: [],
        average_body_length: 0,
        has_documents: true,
        distinct_kinds: 0,
      });
    vi.mocked(del).mockResolvedValue(undefined);
    expect((await searchApi.commands("oc", "Workspace")).total).toBe(0);
    expect((await searchApi.stats()).document_count).toBe(1);
    await searchApi.remove("doc/1");
    expect(vi.mocked(del)).toHaveBeenCalledWith(
      "/api/search/documents/doc%2F1",
      undefined,
    );
  });
});
