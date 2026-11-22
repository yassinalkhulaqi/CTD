import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ReportPreview } from "./ReportPreview";
import { PREVIEW } from "../testFixtures";

describe("ReportPreview", () => {
  it("renders the document title, summary and rendered table", () => {
    render(
      <ReportPreview
        preview={PREVIEW}
        format="markdown"
        onFormatChange={() => undefined}
      />,
    );
    expect(
      screen.getByRole("heading", { level: 1, name: "Weekly report" }),
    ).toBeInTheDocument();
    expect(screen.getByText("challenges")).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "points" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Warmup" })).toBeInTheDocument();
  });

  it("switches the preview format", async () => {
    const user = userEvent.setup();
    const onFormatChange = vi.fn();
    render(
      <ReportPreview
        preview={PREVIEW}
        format="markdown"
        onFormatChange={onFormatChange}
      />,
    );
    await user.click(screen.getByRole("button", { name: "HTML" }));
    expect(onFormatChange).toHaveBeenCalledWith("html");
  });

  it("renders unresolved placeholder warnings", () => {
    const preview = {
      ...PREVIEW,
      warnings: ["team"],
      has_warnings: true,
      sections: [
        { ...PREVIEW.sections[0], warnings: ["team"] },
        ...PREVIEW.sections.slice(1),
      ],
    };
    render(
      <ReportPreview
        preview={preview}
        format="json"
        onFormatChange={() => undefined}
      />,
    );
    expect(
      screen.getByText(/placeholder could not be resolved/),
    ).toBeInTheDocument();
    expect(screen.getByText("Missing: team")).toBeInTheDocument();
  });

  it("renders an empty state without a preview", () => {
    render(
      <ReportPreview
        preview={null}
        format="csv"
        onFormatChange={() => undefined}
      />,
    );
    expect(screen.getByText("Nothing to preview yet")).toBeInTheDocument();
  });
});
