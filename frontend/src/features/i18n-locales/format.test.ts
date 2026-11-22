/** Tests for the pure locale utilities. */

import { describe, expect, it } from "vitest";
import {
  baseLanguage,
  completenessPercent,
  completenessTone,
  defaultFormatRule,
  directionFor,
  extractPlaceholders,
  fallbackChain,
  formatDate,
  formatNumber,
  interpolate,
  isRtlLocale,
  isValidLocaleCode,
  normalizeKey,
  parseLocaleCode,
  pluralCategory,
  pluralKey,
  toLocaleOptions,
  validateDatePattern,
  validateNumberPattern,
} from "./format";

describe("locale codes", () => {
  it("parses script and region subtags", () => {
    const parsed = parseLocaleCode("zh-Hant-TW");
    expect(parsed.base_language).toBe("zh");
    expect(parsed.script).toBe("hant");
    expect(parsed.region).toBe("tw");
    expect(parsed.canonical).toBe("zh-Hant-TW");
  });

  it("rejects malformed codes", () => {
    expect(isValidLocaleCode("e")).toBe(false);
    expect(isValidLocaleCode("en!")).toBe(false);
    expect(() => parseLocaleCode("English")).toThrow(/Invalid locale code/);
  });

  it("detects right to left languages", () => {
    expect(baseLanguage("FR-ca")).toBe("fr");
    expect(isRtlLocale("ar-EG")).toBe(true);
    expect(isRtlLocale("he")).toBe(true);
    expect(directionFor("fr")).toBe("ltr");
    expect(directionFor("ur")).toBe("rtl");
  });

  it("builds de-duplicated fallback chains", () => {
    expect(fallbackChain("fr-CA")).toEqual(["fr-CA", "fr", "en"]);
    expect(fallbackChain("en-US")).toEqual(["en-US", "en"]);
  });
});

describe("plural selection", () => {
  it("handles simple and none rules", () => {
    expect(pluralCategory("simple", 1)).toBe("one");
    expect(pluralCategory("simple", 4)).toBe("other");
    expect(pluralCategory("none", 1)).toBe("other");
  });

  it("handles arabic and slavic families", () => {
    expect(pluralCategory("arabic", 0)).toBe("zero");
    expect(pluralCategory("arabic", 2)).toBe("two");
    expect(pluralCategory("arabic", 7)).toBe("few");
    expect(pluralCategory("arabic", 21)).toBe("many");
    expect(pluralCategory("arabic", 101)).toBe("one");
    expect(pluralCategory("slavic", 3)).toBe("few");
    expect(pluralCategory("slavic", 11)).toBe("many");
    expect(pluralKey("items", "one")).toBe("items.one");
  });
});

describe("interpolation", () => {
  it("extracts unique placeholders", () => {
    expect(extractPlaceholders("Hi {name}, {count} {name}")).toEqual([
      "name",
      "count",
    ]);
  });

  it("substitutes values and reports missing names", () => {
    const result = interpolate("Hello {name}, you have {count}", {
      name: "Ada",
    });
    expect(result.value).toBe("Hello Ada, you have {count}");
    expect(result.applied).toEqual(["name"]);
    expect(result.missing).toEqual(["count"]);
    expect(result.complete).toBe(false);
  });

  it("unescapes doubled braces", () => {
    expect(interpolate("Use {{name}} here", {}).value).toBe("Use {name} here");
  });
});

describe("formatting", () => {
  it("validates and formats numbers with half-up rounding", () => {
    expect(validateNumberPattern("#,##0.00")).toBe("#,##0.00");
    expect(() => validateNumberPattern("abc")).toThrow(
      /Invalid number pattern/,
    );
    expect(formatNumber(1234567.891, "#,##0.00")).toBe("1,234,567.89");
    expect(formatNumber(1234.5, "0")).toBe("1235");
    expect(formatNumber(-1234.5, "#,##0.0")).toBe("-1,234.5");
    expect(formatNumber(12.345, "0.00")).toBe("12.35");
  });

  it("formats dates with localised month tokens", () => {
    expect(() => validateDatePattern("QQ/YYYY")).toThrow(
      /Unsupported date token/,
    );
    expect(formatDate("2026-11-20", "YYYY-MM-DD")).toBe("2026-11-20");
    expect(formatDate("2026-11-20", "DD/MM/YYYY", "fr")).toBe("20/11/2026");
    expect(formatDate("2026-11-20", "MMMM YYYY", "en")).toBe("November 2026");
    expect(formatDate("2026-11-20", "MMM DD", "fr")).toBe("nov 20");
    expect(() => formatDate("not-a-date", "YYYY")).toThrow(/Invalid date/);
  });

  it("exposes sensible defaults per language", () => {
    expect(defaultFormatRule("en")).toEqual(["#,##0.00", "MM/DD/YYYY"]);
    expect(defaultFormatRule("de")).toEqual(["#,##0.00", "DD.MM.YYYY"]);
    expect(defaultFormatRule("xx")).toEqual(["#,##0.00", "YYYY-MM-DD"]);
  });
});

describe("reporting helpers", () => {
  it("computes completeness percentages and tones", () => {
    expect(completenessPercent(3, 4)).toBe(75);
    expect(completenessPercent(0, 0)).toBe(0);
    expect(completenessTone(95)).toBe("success");
    expect(completenessTone(60)).toBe("warning");
    expect(completenessTone(20)).toBe("danger");
  });

  it("builds selector options and normalises keys", () => {
    const options = toLocaleOptions([
      { code: "fr", name: "French" },
      { code: "ar", name: "Arabic" },
    ]);
    expect(options.map((option) => option.code)).toEqual(["ar", "fr"]);
    expect(options[0].isRtl).toBe(true);
    expect(normalizeKey("  hello world  ")).toBe("hello-world");
  });
});
