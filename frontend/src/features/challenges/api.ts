/**
 * Typed endpoints of the challenge detail feature.
 */

import { del, get, patch, post } from "../../api/client";
import type { Note, TimelineEntry, FlagResult } from "./types";

/** The challenge detail endpoints. */
export const challengeDetailsApi = {
  /**
   * Return the notes attached to a challenge.
   *
   * @param challengeId - The identifier of the challenge.
   * @param options - Request options.
   * @returns The notes, oldest first.
   */
  listNotes(challengeId: string, options?: { signal?: AbortSignal }): Promise<Note[]> {
    return get<Note[]>(`/api/challenges/${encodeURIComponent(challengeId)}/notes`, options);
  },

  /**
   * Attach a note to a challenge.
   *
   * @param challengeId - The identifier of the challenge.
   * @param memberId - The identifier of the author.
   * @param body - The content of the note.
   * @param options - Request options.
   * @returns The created note.
   */
  createNote(
    challengeId: string,
    memberId: string,
    body: string,
    options?: { signal?: AbortSignal },
  ): Promise<Note> {
    return post<Note>(
      `/api/challenges/${encodeURIComponent(challengeId)}/notes`,
      { member_id: memberId, body },
      options,
    );
  },

  /**
   * Edit a note.
   *
   * @param noteId - The identifier of the note.
   * @param memberId - The identifier of the author.
   * @param body - The new content of the note.
   * @param options - Request options.
   * @returns The updated note.
   */
  updateNote(
    noteId: string,
    memberId: string,
    body: string,
    options?: { signal?: AbortSignal },
  ): Promise<Note> {
    return patch<Note>(
      `/api/challenges/notes/${encodeURIComponent(noteId)}`,
      { member_id: memberId, body },
      options,
    );
  },

  /**
   * Delete a note.
   *
   * @param noteId - The identifier of the note.
   * @param memberId - The identifier of the author.
   * @param options - Request options.
   * @returns A promise resolved when the note was removed.
   */
  deleteNote(
    noteId: string,
    memberId: string,
    options?: { signal?: AbortSignal },
  ): Promise<void> {
    return del<void>(
      `/api/challenges/notes/${encodeURIComponent(noteId)}?member_id=${encodeURIComponent(memberId)}`,
      options,
    );
  },

  /**
   * Return the solve timeline of a challenge.
   *
   * @param challengeId - The identifier of the challenge.
   * @param options - Request options.
   * @returns The timeline entries, newest first.
   */
  timeline(challengeId: string, options?: { signal?: AbortSignal }): Promise<TimelineEntry[]> {
    return get<TimelineEntry[]>(
      `/api/challenges/${encodeURIComponent(challengeId)}/timeline`,
      options,
    );
  },

  /**
   * Submit a flag for a challenge.
   *
   * @param challengeId - The identifier of the challenge.
   * @param memberId - The identifier of the solver.
   * @param flag - The submitted flag.
   * @param options - Request options.
   * @returns The outcome of the submission.
   */
  submitFlag(
    challengeId: string,
    memberId: string,
    flag: string,
    options?: { signal?: AbortSignal },
  ): Promise<FlagResult> {
    return post<FlagResult>(
      `/api/challenges/${encodeURIComponent(challengeId)}/flags`,
      { challenge_id: challengeId, member_id: memberId, flag },
      options,
    );
  },
};
