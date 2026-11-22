/**
 * Typed API adapter for the notes workspace feature.
 *
 * Every function delegates to the shared HTTP client so authentication,
 * retries and error normalisation stay consistent with the rest of the app.
 */

import {
  buildQuery,
  del,
  get,
  patch,
  post,
  type RequestOptions,
} from "../../api/client";
import type {
  NoteCreatePayload,
  NoteEntry,
  NoteFilters,
  NoteRevision,
  NoteTemplate,
  NoteTemplateCreatePayload,
  NotesSummary,
  TemplateRenderPayload,
  TemplateRenderResult,
  NoteUpdatePayload,
} from "./types";

/**
 * Encode a note identifier for use in a URL path.
 *
 * @param id - The raw identifier.
 * @returns The encoded identifier.
 */
function pathId(id: string): string {
  return encodeURIComponent(id);
}

/** The notes workspace endpoints. */
export const notesApi = {
  /**
   * List notes matching the supplied filters.
   *
   * @param filters - Optional filters.
   * @param options - Request options.
   * @returns The matching notes.
   */
  listNotes(
    filters: NoteFilters = {},
    options?: RequestOptions,
  ): Promise<NoteEntry[]> {
    const query = buildQuery({
      challenge_id: filters.challengeId,
      member_id: filters.memberId,
      tag: filters.tag,
      q: filters.query,
      pinned: filters.pinned,
    });
    return get<NoteEntry[]>(`/api/notes${query}`, options);
  },

  /**
   * Return one note.
   *
   * @param id - The note identifier.
   * @param options - Request options.
   * @returns The note.
   */
  getNote(id: string, options?: RequestOptions): Promise<NoteEntry> {
    return get<NoteEntry>(`/api/notes/${pathId(id)}`, options);
  },

  /**
   * Create a note.
   *
   * @param payload - The note fields.
   * @param options - Request options.
   * @returns The created note.
   */
  createNote(
    payload: NoteCreatePayload,
    options?: RequestOptions,
  ): Promise<NoteEntry> {
    return post<NoteEntry>("/api/notes", payload, options);
  },

  /**
   * Update a note.
   *
   * @param id - The note identifier.
   * @param payload - The fields to change.
   * @param options - Request options.
   * @returns The updated note.
   */
  updateNote(
    id: string,
    payload: NoteUpdatePayload,
    options?: RequestOptions,
  ): Promise<NoteEntry> {
    return patch<NoteEntry>(`/api/notes/${pathId(id)}`, payload, options);
  },

  /**
   * Delete a note.
   *
   * @param id - The note identifier.
   * @param options - Request options.
   * @returns A promise resolved when the note was removed.
   */
  deleteNote(id: string, options?: RequestOptions): Promise<void> {
    return del<void>(`/api/notes/${pathId(id)}`, options);
  },

  /**
   * Set or toggle the pinned state of a note.
   *
   * @param id - The note identifier.
   * @param pinned - Explicit state, or `null` to toggle.
   * @param options - Request options.
   * @returns The updated note.
   */
  setPin(
    id: string,
    pinned: boolean | null,
    options?: RequestOptions,
  ): Promise<NoteEntry> {
    return post<NoteEntry>(`/api/notes/${pathId(id)}/pin`, { pinned }, options);
  },

  /**
   * Return the revision timeline of a note.
   *
   * @param id - The note identifier.
   * @param options - Request options.
   * @returns The revisions, oldest first.
   */
  listRevisions(id: string, options?: RequestOptions): Promise<NoteRevision[]> {
    return get<NoteRevision[]>(`/api/notes/${pathId(id)}/revisions`, options);
  },

  /**
   * List note templates.
   *
   * @param category - Optional category filter.
   * @param options - Request options.
   * @returns The templates.
   */
  listTemplates(
    category?: string,
    options?: RequestOptions,
  ): Promise<NoteTemplate[]> {
    const query = buildQuery({ category });
    return get<NoteTemplate[]>(`/api/note-templates${query}`, options);
  },

  /**
   * Create a reusable template.
   *
   * @param payload - The template fields.
   * @param options - Request options.
   * @returns The created template.
   */
  createTemplate(
    payload: NoteTemplateCreatePayload,
    options?: RequestOptions,
  ): Promise<NoteTemplate> {
    return post<NoteTemplate>("/api/note-templates", payload, options);
  },

  /**
   * Render a template with variables.
   *
   * @param payload - The template source or id plus variables.
   * @param options - Request options.
   * @returns The rendered body.
   */
  renderTemplate(
    payload: TemplateRenderPayload,
    options?: RequestOptions,
  ): Promise<TemplateRenderResult> {
    return post<TemplateRenderResult>(
      "/api/note-templates/render",
      payload,
      options,
    );
  },

  /**
   * Return per-challenge and workspace note statistics.
   *
   * @param challengeId - Optional challenge restriction.
   * @param options - Request options.
   * @returns The aggregated summary.
   */
  summary(
    challengeId?: string,
    options?: RequestOptions,
  ): Promise<NotesSummary> {
    const query = buildQuery({ challenge_id: challengeId });
    return get<NotesSummary>(`/api/notes/summary${query}`, options);
  },
};
