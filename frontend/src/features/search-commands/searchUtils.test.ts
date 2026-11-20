/** Pure helper tests for query parsing and command ranking. */

import { describe, expect, it } from "vitest";
import {
  buildRecentQueries,
  commandInitials,
  commandScore,
  filterCommands,
  foldText,
  formatShortcut,
  groupCommands,
  parseQueryText,
  rankResults,
  scoreLabel,
  tokenizeQuery,
} from "./searchUtils";
import type { Command, SearchResult } from "./types";

function command(id: string, name: string, keywords: string[] = []): Command {
  return {
    id,
    name,
    description: `Open ${name.toLowerCase()} at /${id}`,
    group: "Workspace",
    shortcut: "G C",
    keywords,
    initials: commandInitials(name),
    shortcut_label: "G C",
  };
}

function result(id: string, score: number): SearchResult {
  return {
    document_id: id,
    kind: "custom",
    title: id,
    snippet: "snippet",
    score,
    highlights: [],
    path: `/${id}`,
    relevance: "related",
  };
}

describe("query helpers", () => {
  it("folds accents and drops stopwords", () => {
    expect(foldText("Crème Brûlée!")).toBe("creme brulee");
    expect(tokenizeQuery("The web shell")).toEqual(["web", "shell"]);
    expect(tokenizeQuery("the")).toEqual(["the"]);
  });

  it("extracts inline kind and tag filters", () => {
    const parsed = parseQueryText("sql kind:challenge tag:web kind:team");
    expect(parsed.text).toBe("sql");
    expect(parsed.kinds).toEqual(["challenge", "team"]);
    expect(parsed.tags).toEqual(["web"]);
    expect(parseQueryText("kind:unknown sql").kinds).toEqual([]);
  });

  it("ranks results by score and then identifier", () => {
    const ordered = rankResults(
      [result("b", 4), result("a", 4), result("c", 9)],
      2,
    );
    expect(ordered.map((item) => item.document_id)).toEqual(["c", "a"]);
  });

  it("maintains a bounded unique recent-query list", () => {
    expect(buildRecentQueries(["old", "web"], "web", 2)).toEqual([
      "web",
      "old",
    ]);
    expect(buildRecentQueries(["a", "b", "c"], "d", 2)).toEqual(["d", "a"]);
    expect(buildRecentQueries(["a"], "  ")).toEqual(["a"]);
  });
});

describe("command helpers", () => {
  const commands = [
    command("b.second", "Focus search", ["find"]),
    command("a.first", "Open challenges", ["board"]),
  ];

  it("matches commands by substring, initials and keyword", () => {
    expect(commandScore(commands[1], "challenges")).toBeGreaterThanOrEqual(8);
    expect(commandScore(commands[1], "oc")).toBeGreaterThanOrEqual(6);
    expect(commandScore(commands[1], "board")).toBe(5);
    expect(commandScore(commands[1], "missing")).toBe(0);
  });

  it("filters and groups commands deterministically", () => {
    expect(filterCommands(commands, "").map((item) => item.id)).toEqual([
      "a.first",
      "b.second",
    ]);
    expect(filterCommands(commands, "focus").map((item) => item.id)).toEqual([
      "b.second",
    ]);
    expect(Object.keys(groupCommands(filterCommands(commands, "")))).toEqual([
      "Workspace",
    ]);
  });

  it("formats labels and shortcuts", () => {
    expect(commandInitials("Open challenges")).toBe("oc");
    expect(formatShortcut("Mod+K")).toBe("⌘/Ctrl+K");
    expect(scoreLabel(13)).toBe("Exact");
    expect(scoreLabel(0)).toBe("Indexed");
  });
});
