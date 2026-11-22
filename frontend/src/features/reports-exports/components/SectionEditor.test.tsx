import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SectionEditor } from "./SectionEditor";
import { SECTIONS } from "../testFixtures";

describe("SectionEditor", () => {
  it("renders every section with its placeholder tokens", () => {
    render(
      <SectionEditor
        sections={SECTIONS}
        onToggle={() => undefined}
        onPatch={() => undefined}
        onMove={() => undefined}
        onRemove={() => undefined}
      />,
    );
    expect(screen.getAllByLabelText("Section title")[0]).toHaveValue(
      "Summary for {{ team }}",
    );
    expect(screen.getByText("team")).toBeInTheDocument();
    expect(screen.getByText("score")).toBeInTheDocument();
    expect(
      screen.getByRole("group", { name: "Reorder Challenges" }),
    ).toBeInTheDocument();
  });

  it("toggles, reorders and removes sections through the callbacks", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    const onMove = vi.fn();
    const onRemove = vi.fn();
    render(
      <SectionEditor
        sections={SECTIONS}
        onToggle={onToggle}
        onPatch={() => undefined}
        onMove={onMove}
        onRemove={onRemove}
      />,
    );
    await user.click(
      screen.getByRole("checkbox", { name: "Include Summary for {{ team }}" }),
    );
    await user.click(
      screen.getByRole("button", { name: "Move Challenges up" }),
    );
    await user.click(screen.getByRole("button", { name: "Remove Members" }));
    expect(onToggle).toHaveBeenCalledWith("summary");
    expect(onMove).toHaveBeenCalledWith("challenges", -1);
    expect(onRemove).toHaveBeenCalledWith("members");
  });

  it("edits a section field", () => {
    const onPatch = vi.fn();
    render(
      <SectionEditor
        sections={SECTIONS.slice(0, 1)}
        onToggle={() => undefined}
        onPatch={onPatch}
        onMove={() => undefined}
        onRemove={() => undefined}
      />,
    );
    fireEvent.change(screen.getByLabelText("Section title"), {
      target: { value: "Overview" },
    });
    expect(onPatch).toHaveBeenCalledWith("summary", { title: "Overview" });
  });

  it("renders an empty hint when a template has no sections", () => {
    render(
      <SectionEditor
        sections={[]}
        onToggle={() => undefined}
        onPatch={() => undefined}
        onMove={() => undefined}
        onRemove={() => undefined}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("no sections");
  });
});
