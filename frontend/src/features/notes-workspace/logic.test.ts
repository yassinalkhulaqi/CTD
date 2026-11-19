import { describe, expect, it } from "vitest";
import {
  collectTags,
  countWords,
  draftFromNote,
  emptyDraft,
  escapeHtml,
  extractTemplateVariables,
  filterNotes,
  formatChangeSummary,
  makeExcerpt,
  normaliseTag,
  normaliseTags,
  readingMinutes,
  renderMarkdownish,
  renderTemplate,
  saveStateLabel,
  slugify,
  validateDraft,
} from "./logic";
import type { NoteEntry } from "./types";

function note(overrides: Partial<NoteEntry> = {}): NoteEntry {
  return {
    id: "note-1",
    challenge_id: "challenge-1",
    member_id: "member-1",
    title: "JWT keys",
    body: "# Heading\n\nThe **jwt** secret is weak.",
    format: "markdown",
    tags: ["web", "jwt"],
    pinned: false,
    version: 1,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-02T00:00:00Z",
    word_count: 6,
    reading_time_minutes: 0,
    excerpt: "Heading The jwt secret is weak.",
    headings: [
      { level: 1, text: "Heading", line: 1, anchor: "heading", indent: 0 },
    ],
    tag_count: 2,
    is_pinned: false,
    ...overrides,
  };
}

describe("text metrics", () => {
  it("counts words and estimates reading time", () => {
    expect(countWords("one two, three's four!")).toBe(4);
    expect(countWords("  ")).toBe(0);
    expect(readingMinutes("word ".repeat(400))).toBe(2);
    expect(readingMinutes("word", 0)).toBe(0);
  });

  it("builds a compact excerpt", () => {
    expect(makeExcerpt("  #  Title \n Some **bold** text ")).toBe(
      "Title Some bold text",
    );
    expect(makeExcerpt("x".repeat(300), 20)).toBe("x".repeat(19) + "…");
  });
});

describe("tags", () => {
  it("normalises single tags", () => {
    expect(normaliseTag("  Web Exploit!! ")).toBe("web-exploit");
    expect(normaliseTag("---")).toBe("");
    expect(slugify("  Hello, World! ")).toBe("hello-world");
    expect(slugify("!!!")).toBe("section");
  });

  it("deduplicates and caps tag lists", () => {
    expect(
      normaliseTags(["Web", "web", " crypto ", "", "a".repeat(50)]),
    ).toEqual(["web", "crypto", "a".repeat(32)]);
    expect(
      normaliseTags(Array.from({ length: 30 }, (_, i) => `tag-${i}`)),
    ).toHaveLength(12);
  });
});

describe("templates", () => {
  it("discovers variables in appearance order", () => {
    expect(
      extractTemplateVariables("{{ title }} / {{owner}} / {{ title }}"),
    ).toEqual(["title", "owner"]);
  });

  it("substitutes known variables and keeps unknown ones", () => {
    expect(renderTemplate("Hi {{ name }}!", { name: "nyx" })).toBe("Hi nyx!");
    expect(renderTemplate("Hi {{ name }}!", {})).toBe("Hi {{ name }}!");
  });
});

describe("safe preview", () => {
  it("escapes HTML before applying formatting", () => {
    const html = renderMarkdownish("# Hello\n\n<script>alert('x')</script>");
    expect(html).toContain("<h1");
    expect(html).not.toContain("<script>");
    expect(html).toContain("&lt;script&gt;");
  });

  it("rejects unsafe link targets and accepts safe ones", () => {
    expect(renderMarkdownish("[click](javascript:alert(1))")).not.toContain(
      "href=",
    );
    expect(renderMarkdownish("[docs](https://example.com)")).toContain(
      'href="https://example.com"',
    );
  });

  it("renders bold, code and fenced blocks", () => {
    const html = renderMarkdownish(
      "Some **bold** and `code`.\n\n```ts\nconst x = 1;\n```",
    );
    expect(html).toContain("<strong>bold</strong>");
    expect(html).toContain("<code>code</code>");
    expect(html).toContain("<pre>");
    expect(html).toContain("const x = 1;");
  });

  it("escapes raw markup passed through the renderer", () => {
    expect(escapeHtml(`<img src=x onerror="boom">`)).toContain("&lt;img");
  });
});

describe("filtering and drafts", () => {
  it("filters notes by text and tags", () => {
    const notes = [
      note(),
      note({
        id: "note-2",
        title: "Heap",
        body: "An overflow in the allocator.",
        tags: ["pwn"],
      }),
    ];
    expect(filterNotes(notes, "jwt", [])).toHaveLength(1);
    expect(filterNotes(notes, "", ["PWN"]).map((item) => item.id)).toEqual([
      "note-2",
    ]);
    expect(collectTags(notes)).toEqual(["jwt", "pwn", "web"]);
  });

  it("builds and validates drafts", () => {
    expect(emptyDraft()).toEqual({
      title: "",
      body: "",
      format: "markdown",
      tags: [],
      pinned: false,
    });
    expect(draftFromNote(note()).title).toBe("JWT keys");
    expect(validateDraft(emptyDraft())).toBe("A title is required");
    expect(validateDraft({ ...emptyDraft(), title: "A" })).toBe(
      "A body is required",
    );
    expect(
      validateDraft({ ...emptyDraft(), title: "A", body: "B" }),
    ).toBeNull();
  });
});

describe("display helpers", () => {
  it("maps save states to labels", () => {
    expect(saveStateLabel("saved")).toBe("Saved");
    expect(saveStateLabel("unsaved")).toBe("Unsaved");
    expect(saveStateLabel("saving")).toBe("Saving");
    expect(saveStateLabel("error")).toBe("Save failed");
  });

  it("formats change summaries", () => {
    expect(formatChangeSummary(0, 0)).toBe("No content change");
    expect(formatChangeSummary(2, 0)).toBe("+2");
    expect(formatChangeSummary(2, 1)).toBe("+2 -1");
  });
});
