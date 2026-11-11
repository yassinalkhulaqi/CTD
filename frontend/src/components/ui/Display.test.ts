import { describe, expect, it } from "vitest";
import { colorOf, initialsOf } from "./Display";

describe("initialsOf", () => {
  it("uses the first and last name", () => {
    expect(initialsOf("Nyx Chandler")).toBe("NC");
  });

  it("uses the first two characters of a single name", () => {
    expect(initialsOf("nyx")).toBe("NY");
  });

  it("falls back to a question mark", () => {
    expect(initialsOf("   ")).toBe("?");
  });
});

describe("colorOf", () => {
  it("is deterministic", () => {
    expect(colorOf("RedScribe")).toBe(colorOf("RedScribe"));
  });

  it("returns a hex colour", () => {
    expect(colorOf("RedScribe")).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it("spreads different names across the palette", () => {
    const colours = new Set(["a", "b", "c", "d", "e", "f"].map(colorOf));
    expect(colours.size).toBeGreaterThan(1);
  });
});
