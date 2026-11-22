/** Rendered interaction tests for the formatting playground. */

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { FormatPlayground } from "./components/FormatPlayground";

describe("FormatPlayground", () => {
  it("previews numbers with the locale pattern", () => {
    render(<FormatPlayground locale="en" />);
    expect(screen.getByTestId("format-output")).toHaveTextContent(
      "1,234,567.89",
    );
    expect(screen.getByRole("button", { name: "Number" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("switches to dates and applies edited patterns", () => {
    render(<FormatPlayground locale="en" />);
    fireEvent.click(screen.getByRole("button", { name: "Date" }));
    expect(screen.getByLabelText("ISO date")).toBeInTheDocument();
    expect(screen.getByTestId("format-output")).toHaveTextContent("11/20/2026");

    fireEvent.change(screen.getByLabelText("Date pattern"), {
      target: { value: "DD/MM/YYYY" },
    });
    expect(screen.getByTestId("format-output")).toHaveTextContent("20/11/2026");
  });

  it("applies quick pattern presets", () => {
    render(<FormatPlayground locale="en" />);
    fireEvent.click(screen.getByRole("button", { name: "#,##0" }));
    expect(screen.getByTestId("format-output")).toHaveTextContent("1,234,568");
  });

  it("surfaces invalid patterns and blocks saving", () => {
    const onSaveRule = vi.fn();
    render(<FormatPlayground locale="en" onSaveRule={onSaveRule} />);
    fireEvent.change(screen.getByLabelText("Number pattern"), {
      target: { value: "not-a-pattern" },
    });
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Save patterns/ }),
    ).toBeDisabled();
  });

  it("saves edited patterns for the active locale", () => {
    const onSaveRule = vi.fn();
    render(<FormatPlayground locale="en" onSaveRule={onSaveRule} />);
    fireEvent.change(screen.getByLabelText("Number pattern"), {
      target: { value: "#,##0" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Save patterns/ }));
    expect(onSaveRule).toHaveBeenCalledWith("#,##0", "MM/DD/YYYY");
  });
});
