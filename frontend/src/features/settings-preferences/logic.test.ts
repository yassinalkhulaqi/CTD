import { describe, expect, it } from "vitest";
import { groupFields, isDirtyValues, toNumber } from "./logic";

describe("settings-preferences logic", () => {
  it("groups schema fields by prefix", () => {
    const groups = groupFields([
      {
        key: "appearance.theme",
        value_type: "enum",
        default: "system",
        label: "",
        description: "",
        choices: [],
        min_value: null,
        max_value: null,
      },
      {
        key: "notifications.email",
        value_type: "boolean",
        default: true,
        label: "",
        description: "",
        choices: [],
        min_value: null,
        max_value: null,
      },
    ]);
    expect(Object.keys(groups).sort()).toEqual(["appearance", "notifications"]);
    expect(groups.appearance).toHaveLength(1);
  });

  it("detects dirty values and coerces numbers", () => {
    expect(isDirtyValues({ a: 1, b: true }, { a: 1, b: false })).toBe(true);
    expect(isDirtyValues({ a: 1 }, { a: 1 })).toBe(false);
    expect(toNumber("30", 5)).toBe(30);
    expect(toNumber("x", 5)).toBe(5);
  });
});
