/**
 * Hooks of the challenge tracking feature.
 */

import { useCallback } from "react";
import { useMutation, useQuery } from "../../api";
import { queryKey } from "../../api/cache";
import { challengeDetailsApi } from "./api";
import type { FlagResult, Note, TimelineEntry } from "./types";

/**
 * Return the notes attached to a challenge.
 *
 * @param challengeId - The identifier of the challenge, `null` disables the query.
 * @returns The query state.
 */
export function useChallengeNotes(challengeId: string | null) {
  const key = queryKey("challenges:notes", { challengeId });
  const fetcher = useCallback(
    (signal: AbortSignal) => challengeDetailsApi.listNotes(challengeId ?? "", { signal }),
    [challengeId],
  );
  return useQuery<Note[]>({ key: challengeId ? key : null, fetcher, staleTime: 15_000 });
}

/**
 * Return the solve timeline of a challenge.
 *
 * @param challengeId - The identifier of the challenge, `null` disables the query.
 * @returns The query state.
 */
export function useChallengeTimeline(challengeId: string | null) {
  const key = queryKey("challenges:timeline", { challengeId });
  const fetcher = useCallback(
    (signal: AbortSignal) => challengeDetailsApi.timeline(challengeId ?? "", { signal }),
    [challengeId],
  );
  return useQuery<TimelineEntry[]>({
    key: challengeId ? key : null,
    fetcher,
    staleTime: 10_000,
  });
}

/** The payload accepted by the flag submission mutation. */
export interface SubmitFlagInput {
  challengeId: string;
  memberId: string;
  flag: string;
}

/**
 * Return the mutation used to submit a flag.
 *
 * @returns The mutation state.
 */
export function useSubmitFlag() {
  return useMutation<SubmitFlagInput, FlagResult>({
    mutationFn: (input) =>
      challengeDetailsApi.submitFlag(input.challengeId, input.memberId, input.flag),
    invalidates: [
      queryKey("challenges"),
      queryKey("solves"),
      queryKey("stats:overview"),
    ],
    invalidatesPrefixes: [queryKey("dashboard"), queryKey("challenges:")],
  });
}

/** The payload accepted by the note creation mutation. */
export interface AddNoteInput {
  memberId: string;
  body: string;
}

/**
 * Return the mutation used to attach a note to a challenge.
 *
 * @param challengeId - The identifier of the challenge.
 * @returns The mutation state.
 */
export function useAddNote(challengeId: string | null) {
  return useMutation<AddNoteInput, Note>({
    mutationFn: (input) =>
      challengeDetailsApi.createNote(challengeId ?? "", input.memberId, input.body),
    invalidates: [queryKey("challenges:notes", { challengeId })],
  });
}

/**
 * Return the mutation used to delete a note.
 *
 * @returns The mutation state.
 */
export function useDeleteNote() {
  return useMutation<{ noteId: string; memberId: string }, void>({
    mutationFn: (input) => challengeDetailsApi.deleteNote(input.noteId, input.memberId),
    invalidatesPrefixes: [queryKey("challenges:notes")],
  });
}
