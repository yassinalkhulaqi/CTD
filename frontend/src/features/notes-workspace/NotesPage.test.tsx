import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { NotesWorkspaceController } from "./hooks";
import type {
  NoteEntry,
  NoteRevision,
  NoteTemplate,
  NotesSummary,
} from "./types";

const state = vi.hoisted(() => ({ controller: {} as unknown }));

vi.mock("./hooks", () => ({
  useNotesWorkspace: () => state.controller,
}));

import { NotesPage } from "./NotesPage";

const note: NoteEntry = {
  id: "note-1",
  challenge_id: "challenge-1",
  member_id: "member-1",
  title: "JWT keys",
  body: "# Notes\n\nThe secret is weak.",
  format: "markdown",
  tags: ["web", "jwt"],
  pinned: true,
  version: 2,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
  word_count: 6,
  reading_time_minutes: 0,
  excerpt: "Notes The secret is weak.",
  headings: [{ level: 1, text: "Notes", line: 1, anchor: "notes", indent: 0 }],
  tag_count: 2,
  is_pinned: true,
};

const revision: NoteRevision = {
  id: "rev-1",
  note_id: "note-1",
  version: 1,
  body: "first body",
  author_id: "member-1",
  created_at: "2026-01-01T00:00:00Z",
  added: 2,
  removed: 0,
  net: 2,
  changed: true,
  magnitude: 2,
  is_latest: true,
  change_summary: "+2",
};

const summary: NotesSummary = {
  challenges: [],
  total_notes: 1,
  total_revisions: 1,
  total_words: 6,
  pinned_notes: 1,
  unique_tags: ["jwt", "web"],
  generated_at: "2026-01-02T00:00:00Z",
  challenge_count: 1,
  average_words: 6,
};

function controller(
  overrides: Partial<NotesWorkspaceController> = {},
): NotesWorkspaceController {
  return {
    notes: [note],
    visibleNotes: [note],
    templates: [] as NoteTemplate[],
    summary,
    revisions: [revision],
    selectedNote: note,
    previewRevision: null,
    draft: {
      title: note.title,
      body: note.body,
      format: note.format,
      tags: note.tags,
      pinned: note.pinned,
    },
    saveState: "saved",
    loading: false,
    error: null,
    query: "",
    activeTags: [],
    availableTags: ["jwt", "web"],
    setQuery: vi.fn(),
    toggleTag: vi.fn(),
    clearTags: vi.fn(),
    selectNote: vi.fn(),
    selectRevision: vi.fn(),
    clearRevisionPreview: vi.fn(),
    newNote: vi.fn(),
    updateDraft: vi.fn(),
    applyTemplate: vi.fn(),
    save: vi.fn(),
    togglePin: vi.fn(),
    removeNote: vi.fn(),
    reload: vi.fn(),
    ...overrides,
  };
}

describe("NotesPage", () => {
  beforeEach(() => {
    state.controller = controller();
  });

  it("renders a loading placeholder", () => {
    state.controller = controller({ loading: true });
    render(<NotesPage />);
    expect(screen.getByLabelText("Loading notes")).toBeInTheDocument();
  });

  it("renders an error with a retry action", async () => {
    const user = userEvent.setup();
    const reload = vi.fn();
    state.controller = controller({
      error: "Network down",
      reload,
      notes: [],
      visibleNotes: [],
      selectedNote: null,
    });
    render(<NotesPage />);
    expect(screen.getByRole("alert")).toHaveTextContent("Network down");
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(reload).toHaveBeenCalledOnce();
  });

  it("renders an empty state for a new workspace", async () => {
    const user = userEvent.setup();
    const newNote = vi.fn();
    state.controller = controller({
      notes: [],
      visibleNotes: [],
      selectedNote: null,
      summary: null,
      newNote,
    });
    render(<NotesPage />);
    expect(screen.getByText("No notes yet")).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: /create your first note/i }),
    );
    expect(newNote).toHaveBeenCalledOnce();
  });

  it("renders the split workspace and reacts to interactions", async () => {
    const user = userEvent.setup();
    render(<NotesPage />);
    expect(
      screen.getByRole("heading", { name: "Notes workspace" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /JWT keys/ }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Title")).toHaveValue("JWT keys");
    expect(screen.getByLabelText("Note preview")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /version 1/i }),
    ).toBeInTheDocument();

    const ctrl = state.controller as NotesWorkspaceController;
    await user.click(screen.getByRole("button", { name: /JWT keys/ }));
    expect(ctrl.selectNote).toHaveBeenCalledWith("note-1");

    await user.type(
      screen.getByPlaceholderText("Search titles, text and tags…"),
      "jwt",
    );
    expect(ctrl.setQuery).toHaveBeenCalled();
  });
});
