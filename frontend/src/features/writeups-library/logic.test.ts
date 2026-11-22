/** Pure logic tests for the writeups library. */

import { describe, expect, it } from "vitest";
import { DEFAULT_FILTERS, type Writeup } from "./types";
import {
  bayesianScore,
  buildToc,
  categoryLabel,
  countWords,
  excerpt,
  filterAndSort,
  formatCount,
  normaliseTags,
  readingTime,
  relativeDate,
  slugify,
  splitMarkdownSections,
  statusTone,
  tagFrequency,
} from "./logic";

function writeup(overrides: Partial<Writeup> = {}): Writeup {
  return {
    id: "wu_1",
    challenge_id: "challenge-1",
    author_id: "member-1",
    title: "Recovering the keystream",
    slug: "recovering-the-keystream",
    summary: "A careful walkthrough of nonce reuse.",
    body: "## Setup\nSome words here.\n\n## Attack\nMore words.",
    category: "crypto",
    difficulty: "hard",
    tags: ["crypto", "aes"],
    status: "published",
    excerpt: "A careful walkthrough.",
    word_count: 8,
    reading_minutes: 1,
    average_rating: 4.2,
    bayesian_score: 3.93,
    rating_sum: 21,
    rating_count: 5,
    views: 1200,
    created_at: "2026-01-01T00:00:00Z",
    published_at: "2026-01-02T00:00:00Z",
    toc: [],
    ...overrides,
  };
}

describe("rating mathematics", () => {
  it("applies a prior that shrinks small samples", () => {
    expect(bayesianScore(0, 0)).toBe(3.5);
    expect(bayesianScore(5, 1)).toBeCloseTo(3.8, 2);
    expect(bayesianScore(50, 10)).toBeGreaterThan(bayesianScore(5, 1));
    expect(bayesianScore(1000, 200)).toBeLessThanOrEqual(5);
  });

  it("supports a custom prior and clamps results", () => {
    expect(bayesianScore(0, 0, 4, 2)).toBe(4);
    expect(bayesianScore(-50, 1)).toBe(1);
    expect(bayesianScore(9999, 1)).toBe(5);
  });
});

describe("markdown helpers", () => {
  it("builds a table of contents with unique anchors", () => {
    const toc = buildToc("# Ignored\n## First step\n## First step\n### Detail");
    expect(toc.map((entry) => entry.anchor)).toEqual([
      "first-step",
      "first-step-1",
      "detail",
    ]);
    expect(toc[2].level).toBe(3);
  });

  it("splits sections while preserving content", () => {
    const sections = splitMarkdownSections(
      "Intro\n\n## Alpha\nText A\n\n## Beta\nText B",
    );
    expect(sections.map((section) => section.title)).toEqual([
      "Introduction",
      "Alpha",
      "Beta",
    ]);
    expect(sections[2].content).toContain("Text B");
  });

  it("counts words and estimates reading time", () => {
    expect(countWords("one two's three")).toBe(3);
    expect(readingTime("")).toBe(0);
    expect(readingTime("word ".repeat(200), 100)).toBe(2);
  });

  it("produces markdown-free excerpts", () => {
    expect(excerpt("## Title\nSome **bold** and `code`.")).toContain(
      "Some bold and code.",
    );
    expect(excerpt("word ".repeat(80), 30).endsWith("…")).toBe(true);
  });

  it("normalises titles and tags", () => {
    expect(slugify("Hello, World!")).toBe("hello-world");
    expect(slugify("***")).toBe("writeup");
    expect(normaliseTags([" #Crypto ", "crypto", "", "AES-GCM"])).toEqual([
      "crypto",
      "aes-gcm",
    ]);
  });
});

describe("view helpers", () => {
  it("formats counts, categories, statuses and dates", () => {
    expect(formatCount(999)).toBe("999");
    expect(formatCount(1200)).toBe("1.2k");
    expect(categoryLabel("pwn")).toBe("Binary");
    expect(statusTone("review")).toBe("warning");
    expect(
      relativeDate("2026-01-01T00:00:00Z", Date.parse("2026-01-04T00:00:00Z")),
    ).toBe("3d ago");
  });

  it("filters and sorts an in-memory list", () => {
    const items = [
      writeup(),
      writeup({
        id: "wu_2",
        title: "Web shell",
        category: "web",
        status: "draft",
        tags: ["web"],
        views: 9000,
        bayesian_score: 4.8,
        created_at: "2026-02-01T00:00:00Z",
      }),
    ];
    expect(
      filterAndSort(items, { ...DEFAULT_FILTERS, status: "all" }),
    ).toHaveLength(2);
    expect(filterAndSort(items, DEFAULT_FILTERS)).toHaveLength(1);
    expect(
      filterAndSort(items, {
        ...DEFAULT_FILTERS,
        status: "all",
        category: "web",
      })[0].id,
    ).toBe("wu_2");
    expect(
      filterAndSort(items, {
        ...DEFAULT_FILTERS,
        status: "all",
        sort: "views",
      })[0].id,
    ).toBe("wu_2");
    expect(
      filterAndSort(items, {
        ...DEFAULT_FILTERS,
        status: "all",
        search: "shell",
      })[0].id,
    ).toBe("wu_2");
  });

  it("collects tag frequencies", () => {
    expect(tagFrequency([writeup(), writeup({ id: "wu_2" })])).toEqual([
      { tag: "aes", count: 2 },
      { tag: "crypto", count: 2 },
    ]);
  });
});
