import { describe, expect, it } from "vitest";
import {
  MAX_FLAG_LENGTH,
  MAX_NOTE_LENGTH,
  encodePathSegment,
  normaliseFlag,
  normaliseNote,
  redactFlag,
  stripControlCharacters,
} from "./sanitize";

describe("stripControlCharacters", () => {
  it("removes the control characters", () => {
    expect(stripControlCharacters("a\u0000b")).toBe("ab");
  });

  it("keeps the newlines and the tabs", () => {
    expect(stripControlCharacters("a\nb\tc")).toBe("a\nb\tc");
  });
});

describe("normaliseNote", () => {
  it("trims the note", () => {
    expect(normaliseNote("  hello  ")).toBe("hello");
  });

  it("rejects an empty note", () => {
    expect(() => normaliseNote("   ")).toThrow(/must not be empty/);
  });

  it("rejects an oversized note", () => {
    expect(() => normaliseNote("a".repeat(MAX_NOTE_LENGTH + 1))).toThrow(
      /must not exceed/,
    );
  });

  it("removes the control characters", () => {
    expect(normaliseNote("a\u0007b")).toBe("ab");
  });
});

describe("normaliseFlag", () => {
  it("accepts a valid flag", () => {
    expect(normaliseFlag(" flag{value} ")).toBe("flag{value}");
  });

  it("rejects a flag without braces", () => {
    expect(() => normaliseFlag("flagvalue")).toThrow(/prefix\{content\}/);
  });

  it("rejects an empty flag", () => {
    expect(() => normaliseFlag(" ")).toThrow(/must not be empty/);
  });

  it("rejects an oversized flag", () => {
    expect(() => normaliseFlag("a".repeat(MAX_FLAG_LENGTH + 1))).toThrow(
      /must not exceed/,
    );
  });
});

describe("redactFlag", () => {
  it("keeps the prefix only", () => {
    expect(redactFlag("flag{secret}")).toBe("flag{****}");
  });

  it("masks a short value", () => {
    expect(redactFlag("abc")).toBe("***");
  });
});

describe("encodePathSegment", () => {
  it("encodes the reserved characters", () => {
    expect(encodePathSegment("a/b c")).toBe("a%2Fb%20c");
  });
});
