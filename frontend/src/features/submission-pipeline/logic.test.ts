import { describe, expect, it } from "vitest";
import {
  DEFAULT_MAX_ATTEMPTS,
  FALLBACK_RULES,
  canRetry,
  challengeLabel,
  formatRelative,
  maskFlag,
  memberLabel,
  normalizeFlag,
  stageFor,
  successPercent,
  validateFlag,
} from "./logic";
import type { ChallengeOption, MemberOption } from "./types";

describe("flag normalisation", () => {
  it("trims, lower-cases and strips surrounding quotes", () => {
    expect(normalizeFlag("  FLAG{Hello_World}  ")).toBe("flag{hello_world}");
    expect(normalizeFlag('"flag{abc}"')).toBe("flag{abc}");
    expect(normalizeFlag("`FLAG{ABC}`")).toBe("flag{abc}");
  });

  it("collapses internal whitespace into underscores", () => {
    expect(normalizeFlag("flag{ hello world }")).toBe("flag{_hello_world_}");
  });
});

describe("flag validation", () => {
  it("accepts a well formed flag with fallback rules", () => {
    expect(validateFlag("FLAG{Abc_123}").valid).toBe(true);
  });

  it("rejects empty, malformed and oversized flags", () => {
    expect(validateFlag("   ").code).toBe("format_empty");
    expect(validateFlag("not-a-flag").code).toBe("format_invalid");
    expect(validateFlag(`flag{${"a".repeat(260)}}`).code).toBe(
      "format_too_long",
    );
  });

  it("uses the description of the failing rule as the hint", () => {
    const rules = [
      {
        id: "custom",
        name: "Prefix",
        pattern: "^ctf\\{.*\\}$",
        description: "Start with ctf{.",
        enabled: true,
        priority: 1,
        kind: "format" as const,
      },
    ];
    const result = validateFlag("flag{abc}", rules);
    expect(result.valid).toBe(false);
    expect(result.message).toBe("Start with ctf{.");
  });

  it("ignores disabled and malformed rules", () => {
    const rules = FALLBACK_RULES.map((rule) => ({ ...rule, enabled: false }));
    rules.push({
      id: "broken",
      name: "Broken",
      pattern: "[unclosed",
      description: "Never applies",
      enabled: true,
      priority: 1,
      kind: "format",
    });
    expect(validateFlag("anything", rules).valid).toBe(true);
  });
});

describe("pipeline helpers", () => {
  it("maps statuses to visual stages", () => {
    expect(stageFor("queued")).toEqual({ index: 0, failed: false });
    expect(stageFor("validating")).toEqual({ index: 1, failed: false });
    expect(stageFor("retrying")).toEqual({ index: 1, failed: false });
    expect(stageFor("accepted").failed).toBe(false);
    expect(stageFor("rejected")).toEqual({ index: 2, failed: true });
  });

  it("gates retries by status and attempt budget", () => {
    expect(canRetry("rejected", 1, DEFAULT_MAX_ATTEMPTS)).toBe(true);
    expect(canRetry("rejected", 3, DEFAULT_MAX_ATTEMPTS)).toBe(false);
    expect(canRetry("accepted", 1, DEFAULT_MAX_ATTEMPTS)).toBe(false);
    expect(canRetry("queued", 1, DEFAULT_MAX_ATTEMPTS)).toBe(false);
  });

  it("masks flags without leaking the answer", () => {
    const masked = maskFlag("FLAG{Supersecretvalue}");
    expect(masked.startsWith("flag{")).toBe(true);
    expect(masked).not.toContain("supersecret");
  });

  it("formats relative timestamps and percentages", () => {
    expect(
      formatRelative(
        "2026-01-01T00:00:00Z",
        Date.parse("2026-01-01T00:00:30Z"),
      ),
    ).toBe("30s ago");
    expect(formatRelative("not-a-date")).toBe("—");
    expect(successPercent(1, 4)).toBe(25);
    expect(successPercent(0, 0)).toBe(0);
  });

  it("resolves display labels with fallbacks", () => {
    const challenges: ChallengeOption[] = [
      { id: "c1", title: "Nonce Reuse", team_id: "t1" },
    ];
    const members: MemberOption[] = [
      { id: "m1", handle: "nyx", display_name: "Nyx", team_id: "t1" },
    ];
    expect(challengeLabel("c1", challenges)).toBe("Nonce Reuse");
    expect(challengeLabel("unknown", challenges)).toBe("unknown");
    expect(memberLabel("m1", members)).toBe("Nyx");
    expect(memberLabel("m2", members)).toBe("m2");
  });
});
