import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  del: vi.fn(),
}));

function buildQuery(
  params: Record<string, string | number | boolean | undefined>,
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) search.set(key, String(value));
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

vi.mock("../../api/client", () => ({
  buildQuery,
  get: mocks.get,
  post: mocks.post,
  patch: mocks.patch,
  del: mocks.del,
}));

import { notesApi } from "./api";

describe("notesApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists notes with encoded filters", async () => {
    mocks.get.mockResolvedValue([]);
    const result = await notesApi.listNotes({
      challengeId: "challenge-1",
      tag: "web",
      query: "jwt tokens",
      pinned: true,
    });
    expect(result).toEqual([]);
    expect(mocks.get).toHaveBeenCalledWith(
      "/api/notes?challenge_id=challenge-1&tag=web&q=jwt+tokens&pinned=true",
      undefined,
    );
  });

  it("creates a note with the JSON payload", async () => {
    mocks.post.mockResolvedValue({ id: "note-1" });
    const payload = {
      challenge_id: "challenge-1",
      member_id: "member-1",
      title: "Title",
      body: "Body",
      format: "markdown" as const,
      tags: ["web"],
      pinned: false,
    };
    const result = await notesApi.createNote(payload);
    expect(result).toEqual({ id: "note-1" });
    expect(mocks.post).toHaveBeenCalledWith("/api/notes", payload, undefined);
  });

  it("reads, updates and deletes a note by id", async () => {
    mocks.get.mockResolvedValue({ id: "note/1" });
    mocks.patch.mockResolvedValue({ id: "note/1", title: "New" });
    mocks.del.mockResolvedValue(undefined);

    await notesApi.getNote("note/1");
    expect(mocks.get).toHaveBeenCalledWith("/api/notes/note%2F1", undefined);

    await notesApi.updateNote("note/1", { title: "New", expected_version: 2 });
    expect(mocks.patch).toHaveBeenCalledWith(
      "/api/notes/note%2F1",
      { title: "New", expected_version: 2 },
      undefined,
    );

    await notesApi.deleteNote("note/1");
    expect(mocks.del).toHaveBeenCalledWith("/api/notes/note%2F1", undefined);
  });

  it("sets the pinned state and lists revisions", async () => {
    mocks.post.mockResolvedValue({ id: "note-1", pinned: true });
    mocks.get.mockResolvedValue([]);

    await notesApi.setPin("note-1", true);
    expect(mocks.post).toHaveBeenCalledWith(
      "/api/notes/note-1/pin",
      { pinned: true },
      undefined,
    );

    await notesApi.listRevisions("note-1");
    expect(mocks.get).toHaveBeenCalledWith(
      "/api/notes/note-1/revisions",
      undefined,
    );
  });

  it("handles templates and rendering", async () => {
    mocks.get.mockResolvedValue([]);
    mocks.post.mockResolvedValue({ body: "rendered" });

    await notesApi.listTemplates("crypto");
    expect(mocks.get).toHaveBeenCalledWith(
      "/api/note-templates?category=crypto",
      undefined,
    );

    const payload = {
      name: "Report",
      category: "crypto" as const,
      body: "{{ title }}",
    };
    await notesApi.createTemplate(payload);
    expect(mocks.post).toHaveBeenCalledWith(
      "/api/note-templates",
      payload,
      undefined,
    );

    await notesApi.renderTemplate({
      body: "{{ title }}",
      variables: { title: "RSA" },
    });
    expect(mocks.post).toHaveBeenCalledWith(
      "/api/note-templates/render",
      {
        body: "{{ title }}",
        variables: { title: "RSA" },
      },
      undefined,
    );
  });

  it("loads the workspace summary", async () => {
    mocks.get.mockResolvedValue({ total_notes: 3 });
    const result = await notesApi.summary("challenge-1");
    expect(result).toEqual({ total_notes: 3 });
    expect(mocks.get).toHaveBeenCalledWith(
      "/api/notes/summary?challenge_id=challenge-1",
      undefined,
    );
  });
});
