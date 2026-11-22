/** Rendered interaction tests for the language controls. */

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { DirectionBadge } from "./components/DirectionBadge";
import { LocaleSwitcher } from "./components/LocaleSwitcher";
import type { Locale } from "./types";

const locales: Locale[] = [
  {
    code: "ar",
    name: "Arabic",
    direction: "rtl",
    plural_rules: "arabic",
    base_language: "ar",
    canonical_code: "ar",
    is_rtl: true,
    chain: ["ar", "en"],
  },
  {
    code: "fr-CA",
    name: "Canadian French",
    direction: "ltr",
    plural_rules: "simple",
    base_language: "fr",
    canonical_code: "fr-CA",
    is_rtl: false,
    chain: ["fr-CA", "fr", "en"],
  },
];

describe("DirectionBadge", () => {
  it("announces the direction for assistive technology", () => {
    render(<DirectionBadge direction="rtl" code="ar" />);
    expect(screen.getByLabelText("Right to left")).toHaveTextContent("ar");
  });

  it("supports a compact representation", () => {
    render(<DirectionBadge direction="ltr" compact />);
    expect(screen.getByText("LTR")).toBeInTheDocument();
  });
});

describe("LocaleSwitcher", () => {
  it("renders the registered languages and their fallback chain", () => {
    render(
      <LocaleSwitcher
        locales={locales}
        value="ar"
        onChange={() => undefined}
      />,
    );
    expect(screen.getByLabelText("Language")).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "Arabic (ar)" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Fallback: ar/)).toBeInTheDocument();
  });

  it("reports a changed selection", () => {
    const onChange = vi.fn();
    render(<LocaleSwitcher locales={locales} value="ar" onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Language"), {
      target: { value: "fr-CA" },
    });
    expect(onChange).toHaveBeenCalledWith("fr-CA");
  });

  it("disables itself when there are no languages", () => {
    render(<LocaleSwitcher locales={[]} value="" onChange={() => undefined} />);
    expect(screen.getByLabelText("Language")).toBeDisabled();
  });
});
