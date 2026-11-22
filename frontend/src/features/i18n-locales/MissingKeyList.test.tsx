/** Rendered tests for the missing key inspector. */

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MissingKeyList } from "./components/MissingKeyList";
import type { MissingKey } from "./types";

const items: MissingKey[] = [
  {
    locale: "fr",
    namespace: "ui",
    key: "items.one",
    qualified_key: "ui:items.one",
    reference_value: "{count} item",
    resolved_locale: "en",
    has_fallback: true,
  },
  {
    locale: "fr",
    namespace: "ui",
    key: "farewell",
    qualified_key: "ui:farewell",
    reference_value: "Goodbye",
    resolved_locale: null,
    has_fallback: false,
  },
];

describe("MissingKeyList", () => {
  it("lists keys with their fallback status", () => {
    render(<MissingKeyList items={items} locale="fr" />);
    expect(
      screen.getByRole("list", { name: "Missing keys for fr" }),
    ).toBeInTheDocument();
    expect(screen.getByText("ui:items.one")).toBeInTheDocument();
    expect(screen.getByText("fallback: en")).toBeInTheDocument();
    expect(screen.getByText("no fallback")).toBeInTheDocument();
  });

  it("renders an empty state when the catalogue is complete", () => {
    render(<MissingKeyList items={[]} locale="fr" />);
    expect(screen.getByText("Nothing missing")).toBeInTheDocument();
    expect(
      screen.getByText("fr covers every reference key."),
    ).toBeInTheDocument();
  });
});
