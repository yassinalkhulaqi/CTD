/**
 * Data loading and local editing state for the notes workspace screen.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { notesApi } from "./api";
import {
  collectTags,
  draftFromNote,
  emptyDraft,
  filterNotes,
  renderTemplate,
  validateDraft,
} from "./logic";
import type {
  NoteDraft,
  NoteEntry,
  NoteRevision,
  NoteTemplate,
  NotesSummary,
  SaveState,
} from "./types";

/** Delay used by the autosave timer, in milliseconds. */
export const AUTOSAVE_DELAY = 900;

/** The challenge used for notes created directly from the workspace. */
export const DEFAULT_CHALLENGE_ID = "workspace";

/** The author used for notes created directly from the workspace. */
export const DEFAULT_MEMBER_ID = "local";

/**
 * Extract a display message from an unknown failure.
 *
 * @param error - The caught value.
 * @param fallback - Message used when the value is not an error.
 * @returns The message to show.
 */
function messageOf(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

/** The state and actions exposed by {@link useNotesWorkspace}. */
export interface NotesWorkspaceController {
  notes: NoteEntry[];
  visibleNotes: NoteEntry[];
  templates: NoteTemplate[];
  summary: NotesSummary | null;
  revisions: NoteRevision[];
  selectedNote: NoteEntry | null;
  previewRevision: NoteRevision | null;
  draft: NoteDraft;
  saveState: SaveState;
  loading: boolean;
  error: string | null;
  query: string;
  activeTags: string[];
  availableTags: string[];
  setQuery: (value: string) => void;
  toggleTag: (tag: string) => void;
  clearTags: () => void;
  selectNote: (id: string) => void;
  selectRevision: (revision: NoteRevision) => void;
  clearRevisionPreview: () => void;
  newNote: (body?: string) => void;
  updateDraft: (patch: Partial<NoteDraft>) => void;
  applyTemplate: (
    template: NoteTemplate,
    variables: Record<string, string>,
  ) => void;
  save: () => void;
  togglePin: (id: string) => void;
  removeNote: (id: string) => void;
  reload: () => void;
}

/**
 * Manage loading, filtering, editing and persistence of workspace notes.
 *
 * @returns The controller consumed by the page.
 */
export function useNotesWorkspace(): NotesWorkspaceController {
  const [notes, setNotes] = useState<NoteEntry[]>([]);
  const [templates, setTemplates] = useState<NoteTemplate[]>([]);
  const [summary, setSummary] = useState<NotesSummary | null>(null);
  const [revisions, setRevisions] = useState<NoteRevision[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [previewRevision, setPreviewRevision] = useState<NoteRevision | null>(
    null,
  );
  const [draft, setDraft] = useState<NoteDraft>(emptyDraft);
  const [saveState, setSaveState] = useState<SaveState>("saved");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [activeTags, setActiveTags] = useState<string[]>([]);
  const savingRef = useRef(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [noteList, templateList, noteSummary] = await Promise.all([
        notesApi.listNotes(),
        notesApi.listTemplates(),
        notesApi.summary(),
      ]);
      setNotes(noteList);
      setTemplates(templateList);
      setSummary(noteSummary);
      const initial = noteList[0] ?? null;
      setSelectedId(initial?.id ?? null);
      setDraft(initial ? draftFromNote(initial) : emptyDraft());
      setSaveState("saved");
      if (initial) {
        const history = await notesApi.listRevisions(initial.id);
        setRevisions(history);
      } else {
        setRevisions([]);
      }
    } catch (cause) {
      setError(messageOf(cause, "Unable to load the notes workspace"));
      setSaveState("error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const selectNote = useCallback(
    (id: string) => {
      const found = notes.find((note) => note.id === id);
      setSelectedId(id);
      setDraft(found ? draftFromNote(found) : emptyDraft());
      setPreviewRevision(null);
      setSaveState("saved");
      setError(null);
      void notesApi
        .listRevisions(id)
        .then(setRevisions)
        .catch((cause: unknown) => {
          setError(messageOf(cause, "Unable to load revisions"));
        });
    },
    [notes],
  );

  const selectRevision = useCallback((revision: NoteRevision) => {
    setPreviewRevision(revision);
  }, []);

  const clearRevisionPreview = useCallback(() => {
    setPreviewRevision(null);
  }, []);

  const newNote = useCallback((body = "") => {
    setSelectedId(null);
    setDraft({ ...emptyDraft(), body });
    setPreviewRevision(null);
    setRevisions([]);
    setSaveState("unsaved");
    setError(null);
  }, []);

  const applyTemplate = useCallback(
    (template: NoteTemplate, variables: Record<string, string>) => {
      const body = renderTemplate(template.body, variables);
      setDraft((current) => ({
        ...current,
        title: current.title.trim() ? current.title : template.name,
        body,
        format: "markdown",
      }));
      setPreviewRevision(null);
      setSaveState("unsaved");
    },
    [],
  );

  const updateDraft = useCallback((patch: Partial<NoteDraft>) => {
    setDraft((current) => ({ ...current, ...patch }));
    setSaveState("unsaved");
    setError(null);
  }, []);

  const save = useCallback(async () => {
    const problem = validateDraft(draft);
    if (problem) {
      setError(problem);
      setSaveState("error");
      return;
    }
    if (savingRef.current) return;
    savingRef.current = true;
    setSaveState("saving");
    setError(null);
    try {
      const version = notes.find((note) => note.id === selectedId)?.version;
      const saved = selectedId
        ? await notesApi.updateNote(selectedId, {
            title: draft.title,
            body: draft.body,
            format: draft.format,
            tags: draft.tags,
            expected_version: version,
            author_id: DEFAULT_MEMBER_ID,
          })
        : await notesApi.createNote({
            challenge_id: DEFAULT_CHALLENGE_ID,
            member_id: DEFAULT_MEMBER_ID,
            title: draft.title,
            body: draft.body,
            format: draft.format,
            tags: draft.tags,
            pinned: draft.pinned,
          });
      setNotes((current) =>
        current.some((note) => note.id === saved.id)
          ? current.map((note) => (note.id === saved.id ? saved : note))
          : [saved, ...current],
      );
      setSelectedId(saved.id);
      setDraft(draftFromNote(saved));
      setSaveState("saved");
      const history = await notesApi.listRevisions(saved.id);
      setRevisions(history);
      setSummary(await notesApi.summary());
    } catch (cause) {
      setError(messageOf(cause, "Unable to save the note"));
      setSaveState("error");
    } finally {
      savingRef.current = false;
    }
  }, [draft, notes, selectedId]);

  useEffect(() => {
    if (loading || saveState !== "unsaved" || !selectedId) return;
    const timer = window.setTimeout(() => {
      void save();
    }, AUTOSAVE_DELAY);
    return () => window.clearTimeout(timer);
  }, [draft, loading, save, saveState, selectedId]);

  const togglePin = useCallback(
    (id: string) => {
      void notesApi
        .setPin(id, null)
        .then((updated) => {
          setNotes((current) =>
            current.map((note) => (note.id === id ? updated : note)),
          );
          if (selectedId === id) {
            setDraft((current) => ({ ...current, pinned: updated.pinned }));
          }
          return notesApi.summary();
        })
        .then(setSummary)
        .catch((cause: unknown) => {
          setError(messageOf(cause, "Unable to change the pinned state"));
        });
    },
    [selectedId],
  );

  const removeNote = useCallback(
    (id: string) => {
      void notesApi
        .deleteNote(id)
        .then(() => {
          setNotes((current) => current.filter((note) => note.id !== id));
          if (selectedId === id) {
            setSelectedId(null);
            setDraft(emptyDraft());
            setRevisions([]);
            setPreviewRevision(null);
            setSaveState("saved");
          }
          return notesApi.summary();
        })
        .then(setSummary)
        .catch((cause: unknown) => {
          setError(messageOf(cause, "Unable to delete the note"));
        });
    },
    [selectedId],
  );

  const toggleTag = useCallback((tag: string) => {
    const cleaned = tag.trim().toLowerCase();
    if (!cleaned) return;
    setActiveTags((current) =>
      current.includes(cleaned)
        ? current.filter((item) => item !== cleaned)
        : [...current, cleaned],
    );
  }, []);

  const clearTags = useCallback(() => {
    setActiveTags([]);
    setQuery("");
  }, []);

  const visibleNotes = useMemo(
    () => filterNotes(notes, query, activeTags),
    [notes, query, activeTags],
  );
  const availableTags = useMemo(() => collectTags(notes), [notes]);
  const selectedNote = useMemo(
    () => notes.find((note) => note.id === selectedId) ?? null,
    [notes, selectedId],
  );

  return {
    notes,
    visibleNotes,
    templates,
    summary,
    revisions,
    selectedNote,
    previewRevision,
    draft,
    saveState,
    loading,
    error,
    query,
    activeTags,
    availableTags,
    setQuery,
    toggleTag,
    clearTags,
    selectNote,
    selectRevision,
    clearRevisionPreview,
    newNote,
    updateDraft,
    applyTemplate,
    save: () => void save(),
    togglePin,
    removeNote,
    reload: () => void load(),
  };
}
