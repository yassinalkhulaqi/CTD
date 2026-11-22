import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ExportMenu } from "./ExportMenu";
import { EXPORT_JOB } from "../testFixtures";

describe("ExportMenu", () => {
  it("lists all four formats and reports the selected one", async () => {
    const user = userEvent.setup();
    render(<ExportMenu onExport={() => undefined} activeFormat="markdown" />);
    await user.click(screen.getByRole("button", { name: /Export report/ }));
    expect(screen.getAllByRole("menuitem")).toHaveLength(4);
    expect(screen.getByRole("menuitem", { name: /CSV/ })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(
      screen.getByText("Structured payload with pretty printing"),
    ).toBeInTheDocument();
  });

  it("calls the export callback with the chosen format", async () => {
    const user = userEvent.setup();
    const onExport = vi.fn();
    render(<ExportMenu onExport={onExport} />);
    await user.click(screen.getByRole("button", { name: /Export report/ }));
    await user.click(screen.getByRole("menuitem", { name: /JSON/ }));
    expect(onExport).toHaveBeenCalledWith("json");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("disables the trigger when no final report is selected", () => {
    render(<ExportMenu onExport={() => undefined} disabled />);
    expect(
      screen.getByRole("button", { name: /Export report/ }),
    ).toBeDisabled();
  });

  it("shows details of the last export", async () => {
    const user = userEvent.setup();
    render(<ExportMenu onExport={() => undefined} lastExport={EXPORT_JOB} />);
    await user.click(screen.getByRole("button", { name: /Export report/ }));
    expect(screen.getByText("Last export")).toBeInTheDocument();
    expect(screen.getByText("15 B · 1 lines")).toBeInTheDocument();
  });
});
