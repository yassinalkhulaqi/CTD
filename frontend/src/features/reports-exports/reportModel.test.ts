import { describe, expect, it } from "vitest";
import {
  buildCreatePayload,
  buildLocalPreview,
  createSection,
  draftFromTemplate,
  moveSection,
  normaliseSections,
  placeholderTokens,
  resolvePlaceholders,
  validateDraft,
} from "./reportModel";
import { SECTIONS, TEMPLATE } from "./testFixtures";

describe("reportModel", () => {
  it("resolves placeholders, fallbacks and nested keys", () => {
    const data = {
      team: "redscribe",
      score: 0,
      nested: { label: "round two" },
      tags: ["web", "crypto"],
    };
    expect(resolvePlaceholders("Team {{ team }}", data).text).toBe(
      "Team redscribe",
    );
    expect(resolvePlaceholders("Score {{ score || none }}", data).text).toBe(
      "Score 0",
    );
    expect(resolvePlaceholders("{{ missing || fallback }}", data).text).toBe(
      "fallback",
    );
    expect(resolvePlaceholders("{{ nested.label }}", data).text).toBe(
      "round two",
    );
    expect(resolvePlaceholders("{{ tags }}", data).text).toBe("web, crypto");
  });

  it("reports unresolved placeholder keys in order", () => {
    const result = resolvePlaceholders(
      "{{ first }} {{ second }} {{ first }}",
      {},
    );
    expect(result.missing).toEqual(["first", "second"]);
    expect(placeholderTokens("{{ a }} {{ b || x }}")).toEqual(["a", "b"]);
  });

  it("moves sections and rewrites their order", () => {
    const moved = moveSection(SECTIONS, "members", -1);
    expect(moved.map((section) => section.id)).toEqual([
      "summary",
      "members",
      "challenges",
    ]);
    expect(moved.map((section) => section.order)).toEqual([0, 1, 2]);
    expect(moveSection(SECTIONS, "summary", -1)).toEqual(
      normaliseSections(SECTIONS),
    );
  });

  it("creates sections with kind-specific defaults", () => {
    const table = createSection("table", 3);
    expect(table.kind).toBe("table");
    expect(table.source).toBe("challenges");
    expect(table.columns).toEqual(["title", "points"]);
    expect(table.order).toBe(3);
  });

  it("validates a draft and builds the create payload", () => {
    const draft = draftFromTemplate(TEMPLATE);
    expect(validateDraft(draft)).toEqual({});
    expect(
      validateDraft({ ...draft, title: "", scopeId: "", sections: [] }),
    ).toEqual({
      title: "Give the report a title.",
      scopeId: "Choose a scope for this report.",
      sections: "Enable at least one section.",
    });
    expect(buildCreatePayload(draft, { score: 1 })).toEqual({
      template_id: "tpl-1",
      title: "Weekly report",
      scope_id: "team",
      data: { score: 1 },
    });
  });

  it("builds a local preview from the draft and snapshot", () => {
    const draft = draftFromTemplate(TEMPLATE);
    const preview = buildLocalPreview(
      draft,
      {
        team: "redscribe",
        score: 900,
        challenges: [{ title: "Warmup", points: 100 }],
        members: ["Ada", "Lin"],
      },
      "html",
    );
    expect(preview.format).toBe("html");
    expect(preview.section_count).toBe(3);
    expect(preview.sections[0].title).toBe("Summary for redscribe");
    expect(preview.sections[0].text).toBe("Score: 900");
    expect(preview.sections[1].rows).toEqual([["Warmup", "100"]]);
    expect(preview.sections[2].items).toEqual(["Ada", "Lin"]);
    expect(preview.summary).toEqual({ score: 900, challenges: 1, members: 2 });
    expect(preview.total_rows).toBe(3);
  });
});
