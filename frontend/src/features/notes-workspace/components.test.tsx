import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NoteEditor } from "./components/NoteEditor";
import { NotePreview } from "./components/NotePreview";
import { RevisionTimeline } from "./components/RevisionTimeline";
import { TagFilter } from "./components/TagFilter";
import { TemplatePicker } from "./components/TemplatePicker";
import type { NoteDraft, NoteRevision, NoteTemplate } from "./types";

const draft: NoteDraft = {
  title: "Original",
  body: "Some content",
  format: "markdown",
  tags: ["web", "jwt"],
  pinned: false,
};

function StatefulEditor({
  onChange,
  onSave,
  onPin,
  onDelete,
}: {
  onChange: (patch: Partial<NoteDraft>) => void;
  onSave: () => void;
  onPin: () => void;
  onDelete: () => void;
}) {
  const [value, setValue] = useState(draft);
  return (
    <NoteEditor
      draft={value}
      onChange={(patch) => {
        onChange(patch);
        setValue((current) => ({ ...current, ...patch }));
      }}
      onSave={onSave}
      onPin={onPin}
      onDelete={onDelete}
    />
  );
}

function revision(version: number, body: string): NoteRevision {
  return {
    id: `rev-${version}`,
    note_id: "note-1",
    version,
    body,
    author_id: "member-1",
    created_at: "2026-01-01T00:00:00Z",
    added: version,
    removed: 0,
    net: version,
    changed: true,
    magnitude: version,
    is_latest: version === 2,
    change_summary: `+${version}`,
  };
}

describe("NoteEditor", () => {
  it("reports title edits and invokes the actions", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const onSave = vi.fn();
    const onPin = vi.fn();
    const onDelete = vi.fn();
    render(
      <StatefulEditor
        onChange={onChange}
        onSave={onSave}
        onPin={onPin}
        onDelete={onDelete}
      />,
    );

    const title = screen.getByLabelText("Title");
    await user.clear(title);
    await user.type(title, "New title");
    expect(onChange).toHaveBeenLastCalledWith({ title: "New title" });

    await user.click(screen.getByRole("button", { name: /save note/i }));
    await user.click(screen.getByRole("button", { name: "Pin note" }));
    await user.click(screen.getByRole("button", { name: "Delete note" }));
    expect(onSave).toHaveBeenCalledOnce();
    expect(onPin).toHaveBeenCalledOnce();
    expect(onDelete).toHaveBeenCalledOnce();
  });

  it("adds and removes tag chips", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <NoteEditor
        draft={draft}
        onChange={onChange}
        onSave={vi.fn()}
        onPin={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    const input = screen.getByPlaceholderText("Add a tag…");
    await user.type(input, "crypto{Enter}");
    expect(onChange).toHaveBeenCalledWith({ tags: ["web", "jwt", "crypto"] });

    await user.click(screen.getByRole("button", { name: "Remove tag web" }));
    expect(onChange).toHaveBeenCalledWith({ tags: ["jwt"] });
  });

  it("shows a validation message", () => {
    render(
      <NoteEditor
        draft={draft}
        onChange={vi.fn()}
        onSave={vi.fn()}
        onPin={vi.fn()}
        onDelete={vi.fn()}
        error="A body is required"
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("A body is required");
  });
});

describe("TagFilter", () => {
  it("toggles chips and clears the filters", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    const onClear = vi.fn();
    render(
      <TagFilter
        tags={["web", "jwt"]}
        activeTags={["web"]}
        onToggle={onToggle}
        onClear={onClear}
      />,
    );

    const active = screen.getByRole("button", { name: "#web" });
    expect(active).toHaveAttribute("aria-pressed", "true");
    await user.click(active);
    expect(onToggle).toHaveBeenCalledWith("web");

    await user.click(screen.getByRole("button", { name: /clear/i }));
    expect(onClear).toHaveBeenCalledOnce();
  });
});

describe("TemplatePicker", () => {
  it("collects variables and applies the rendered template", async () => {
    const user = userEvent.setup();
    const onApply = vi.fn();
    const template: NoteTemplate = {
      id: "tpl-1",
      name: "Report",
      category: "crypto",
      body: "## {{ title }}\nBy {{ author }}",
      variables: ["title", "author"],
      variable_count: 2,
      line_count: 2,
    };
    render(<TemplatePicker templates={[template]} onApply={onApply} />);

    await user.selectOptions(screen.getByLabelText("Template"), "tpl-1");
    await user.type(screen.getByLabelText("title"), "RSA");
    await user.type(screen.getByLabelText("author"), "nyx");
    await user.click(screen.getByRole("button", { name: "Use template" }));

    expect(onApply).toHaveBeenCalledWith(template, {
      title: "RSA",
      author: "nyx",
    });
  });
});

describe("RevisionTimeline", () => {
  it("selects a revision", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const revisions = [revision(1, "first"), revision(2, "second")];
    render(<RevisionTimeline revisions={revisions} onSelect={onSelect} />);

    await user.click(screen.getByRole("button", { name: /version 2/i }));
    expect(onSelect).toHaveBeenCalledWith(revisions[1]);
  });
});

describe("NotePreview", () => {
  it("escapes injected markup while rendering formatting", () => {
    const { container } = render(
      <NotePreview
        note={null}
        title="Preview"
        body={"# Heading\n\n<script>alert('x')</script>\n\n**bold**"}
      />,
    );
    expect(container.querySelector("script")).toBeNull();
    expect(screen.getByText("<script>alert('x')</script>")).toBeInTheDocument();
    expect(container.querySelector("strong")).toHaveTextContent("bold");
    expect(container.querySelector("h1")).toHaveTextContent("Heading");
  });
});
