import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SaveBar } from "./components/SaveBar";
import { ThemePreview } from "./components/ThemePreview";
import { ImportExport } from "./components/ImportExport";

describe("settings-preferences components", () => {
  it("renders save bar when dirty and triggers save", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const onReset = vi.fn().mockResolvedValue(undefined);
    render(
      <SaveBar
        dirty
        saveState={{ status: "idle", message: "" }}
        onSave={onSave}
        onReset={onReset}
      />,
    );
    expect(screen.getByText("Unsaved changes")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(onSave).toHaveBeenCalled();
  });

  it("renders theme preview contrast status", () => {
    render(
      <ThemePreview
        tokens={{
          surface: "#fff",
          surfaceMuted: "#eee",
          textPrimary: "#111",
          textMuted: "#444",
          accent: "#00f",
          accentText: "#fff",
        }}
        contrastPass={true}
      />,
    );
    expect(screen.getByText("AA pass")).toBeInTheDocument();
  });

  it("exports via import/export component", async () => {
    const onExport = vi.fn().mockResolvedValue("{}");
    const onImport = vi.fn().mockResolvedValue(undefined);
    const createObjectURL = vi.fn(() => "blob:x");
    const revokeObjectURL = vi.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    const click = vi.fn();
    const origCreate = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      const el = origCreate(tag);
      if (tag === "a") (el as HTMLAnchorElement).click = click;
      return el;
    });
    render(<ImportExport onExport={onExport} onImport={onImport} />);
    await userEvent.click(screen.getByRole("button", { name: "Export JSON" }));
    expect(onExport).toHaveBeenCalled();
    vi.restoreAllMocks();
  });
});
